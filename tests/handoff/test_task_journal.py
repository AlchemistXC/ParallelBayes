import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from task_journal import TaskJournal, JournalConflict


def entry(name,batch=0):
    task=dict(id=name,protocol_sha256='protocol-test',batch=batch,artifact_kind='posterior')
    return dict(task=task,output='/artificial/'+name,binding=dict(task=task,output='/artificial/'+name,source='unchanged'),
                attempts=[],calls=[])


def test_durable_independent_tasks_active_index_and_relocated_export(tmp_path):
    root=tmp_path/'journal';ident=dict(host='artificial-test',schema='test')
    first=entry('first');second=entry('second',1)
    key=TaskJournal.key(first['task']);key2=TaskJournal.key(second['task'])
    with TaskJournal(root,ident) as j:
        j.save(key,first,'registered')
        first['attempts'].append(dict(id='attempt-0001',outcome='active'))
        first['calls'].append(dict(seconds=None,outcome='active'))
        j.save(key,first,'launch_intent')
        j.save(key2,second,'registered')
    with TaskJournal(root,ident) as j:
        assert j.read(key)==first and j.read(key2)==second
        assert j.active()=={key:first}
        assert list(j.keys('protocol-test',1))==[key2]
        first['attempts'][0]['outcome']='infrastructure_interruption'
        first['calls'][0].update(seconds=None,outcome='infrastructure_interruption')
        j.save(key,first,'reconciled',dict(kernel_observation='fixture-only'))
        assert j.active()=={}
        j.export(key,tmp_path/'export.json')
        with pytest.raises(FileExistsError):j.export(key,tmp_path/'export.json')
    export=json.loads((tmp_path/'export.json').read_text())
    assert export['entry']['calls'][0]['seconds'] is None
    assert [e['kind'] for e in export['events']]==['registered','launch_intent','reconciled']
    assert export['process_termination_proven'] is False


def test_rebind_history_truncation_output_alias_and_corruption_fail_closed(tmp_path):
    ident=dict(host='test');root=tmp_path/'journal';record=entry('a');key=TaskJournal.key(record['task'])
    record['attempts']=[dict(id='one',outcome='numerical_failure')]
    record['calls']=[dict(seconds=1.2,outcome='numerical_failure')]
    with TaskJournal(root,ident) as j:
        j.save(key,record,'fixture-terminal')
        for field in ('binding','attempts','calls'):
            bad=copy.deepcopy(record)
            if field=='binding':bad[field]['source']='changed'
            else:bad[field]=[]
            with pytest.raises(JournalConflict):j.save(key,bad,'invalid')
        duplicate=entry('b');duplicate['output']=duplicate['binding']['output']=record['output']
        with pytest.raises(JournalConflict):j.save(TaskJournal.key(duplicate['task']),duplicate,'invalid')
        assert list(j.keys('protocol-test'))==[key]
    with pytest.raises(JournalConflict):
        with TaskJournal(root,dict(host='different')):pass
    with sqlite3.connect(root/'tasks.sqlite3') as db:
        db.execute('UPDATE events SET checksum=? WHERE task_key=?',('0'*64,key))
    with TaskJournal(root,ident) as j:
        with pytest.raises(JournalConflict):j.read(key)


def test_unrelated_terminal_payload_is_not_read_before_pending_lookup(tmp_path):
    root=tmp_path/'journal';ident=dict(host='test');a=entry('a');b=entry('b')
    a['attempts']=[dict(id='one',outcome='valid')]
    b['attempts']=[dict(id='one',outcome='active')]
    ka,kb=TaskJournal.key(a['task']),TaskJournal.key(b['task'])
    with TaskJournal(root,ident) as j:j.save(ka,a,'fixture');j.save(kb,b,'fixture')
    # Intentional corruption demonstrates bounded access, not permission to
    # accept the corrupt task: accessing/exporting that task must still fail.
    with sqlite3.connect(root/'tasks.sqlite3') as db:db.execute('UPDATE tasks SET record=? WHERE key=?',('INVALID',ka))
    with TaskJournal(root,ident) as j:
        assert j.active()=={kb:b}
        assert j.read(kb)==b
        with pytest.raises((JournalConflict,json.JSONDecodeError)):j.export(ka,tmp_path/'invalid.json')


def test_incomplete_directory_and_duplicate_initialization_are_not_repaired(tmp_path):
    root=tmp_path/'partial';root.mkdir()
    with pytest.raises(JournalConflict):
        with TaskJournal(root,{}):pass
    assert list(root.iterdir())==[]


def test_writer_process_exit_rolls_back_half_written_task_and_event(tmp_path):
    root=tmp_path/'journal';ident=dict(host='test');value=entry('kept');key=TaskJournal.key(value['task'])
    with TaskJournal(root,ident) as j:j.save(key,value,'registered')
    # Real writer death inside an uncommitted SQLite transaction. This is a
    # storage fault, not a Windows Job/lifecycle or power-loss test.
    program=('import sqlite3,os,sys; d=sqlite3.connect(sys.argv[1]); '
             'd.execute("BEGIN IMMEDIATE"); '
             'd.execute("UPDATE tasks SET record=\'BROKEN\'"); '
             'd.execute("DELETE FROM events"); os._exit(23)')
    run=subprocess.run([sys.executable,'-c',program,str(root/'tasks.sqlite3')])
    assert run.returncode==23
    with TaskJournal(root,ident) as j:
        assert j.read(key)==value
        assert j.check_database()['integrity']=='ok'
