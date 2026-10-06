"""Full planned-count artificial persistence exercise; never invokes MCMC.

Bindings are shaped by archived technical records, explicitly marked as
artificial. No fixture is a valid scientific run, protocol or live process.
"""
import argparse,copy,hashlib,json,os,shutil,sys,time
from pathlib import Path

def run(source,evidence,output):
    if output.exists():raise FileExistsError('Preserve previous exercise')
    sys.path.insert(0,str(source/'scripts/completion'))
    from task_journal import TaskJournal
    from batch_contract import create_tasks,WORKFLOWS
    from formal_measurement_plan import create_measurement_plan
    from formal_runtime import atomic_json,fingerprint,file_hash
    import psutil
    identity='ARTIFICIAL-formal-journal-scale-v1'
    models=['G1','G2','A1','L1','L2','H1','H2','M1','W1']
    groups=[dict(models=models,replicates=list(range(128)),budgets=[256,1024,4096,16384],workflows=list(WORKFLOWS))]
    tasks=create_tasks(identity,groups)
    allocation=create_measurement_plan(identity,tasks)
    assert len(tasks)==41472 and len(allocation['probes'])==9216
    frames=[dict(t,protocol_sha256=identity,artifact_kind='posterior') for t in tasks]
    frames += [dict(id=p['id'],batch=p['batch'],model=p['model'],replicate=p['replicate'],
                    protocol_sha256=identity+'-cache',artifact_kind='cache_measurement') for p in allocation['probes']]
    templates={}
    for path in (evidence/'main/tasks').glob('*/attempt-0001/binding.json'):
        binding=json.loads(path.read_text());task=binding['task']
        if task['device']=='cpu' and task['kernel']=='rwm' and task['executor']=='sequential':templates[task['model']]=binding
    assert set(templates)=={'G1','G2','L1'}
    output.mkdir(parents=True);root=output/'journal'
    host=dict(schema='ARTIFICIAL-storage-exercise',host_lock='NO-OS-COHORT-USED')
    process=psutil.Process();peak=process.memory_info().rss;written=0;logical=0;started=time.perf_counter()
    selected={};counts={};last_key=None
    # Public journal interface, real SQLite durable commits, full planned count.
    with TaskJournal(root,host) as journal:
        for i,t in enumerate(frames):
            if i%256==0:
                if shutil.disk_usage(output).free<4*1024**3:raise RuntimeError('Preserve partial output: insufficient disk margin')
                peak=max(peak,process.memory_info().rss)
            shape='G2' if t['model'] in ('G2','A1') else 'L1' if t['model'] in ('L1','L2','W1') else 'G1'
            binding=copy.deepcopy(templates[shape])
            location='/ARTIFICIAL/'+t['id']
            binding.update(task=t,output=location,artificial_persistence_fixture=True,
                           fixture_source_model=shape,not_executable=True)
            entry=dict(task=t,output=location,binding=binding,attempts=[],calls=[])
            key=TaskJournal.key(t);journal.save(key,entry,'artificial_registered')
            outcome=('numerical_failure' if i%23==0 else 'infrastructure_interruption' if i%37==0 else
                     'measurement_available' if t['artifact_kind']=='cache_measurement' else 'valid')
            if i==len(frames)-1:outcome='active';last_key=key
            entry['attempts']=[dict(id='attempt-0001',outcome=outcome,job_name='ARTIFICIAL-NO-KERNEL-JOB')]
            entry['calls']=[dict(seconds=None,outcome=outcome,fixture_only=True)]
            journal.save(key,entry,'artificial_state')
            logical+=len(json.dumps(entry,sort_keys=True,allow_nan=False).encode())
            counts[outcome]=counts.get(outcome,0)+1;written+=1
            if i in (0,1,len(frames)//2,len(frames)-1):selected[key]=fingerprint(entry)
            if written%2048==0:print(json.dumps(dict(artificial_records=written,rss_bytes=process.memory_info().rss)),flush=True)
    write_seconds=time.perf_counter()-started;peak=max(peak,process.memory_info().rss)
    # Reopen, access all keys one at a time, check both indices and every chain.
    started=time.perf_counter();checked=0
    with TaskJournal(root,host) as journal:
        assert list(journal.active())==[last_key]
        for protocol,count in [(identity,41472),(identity+'-cache',9216)]:
            batch_counts=[]
            for batch in range(4):
                n=0
                for key in journal.keys(protocol,batch):
                    row=journal.read(key);assert row['binding']['artificial_persistence_fixture'] is True
                    if key in selected:assert fingerprint(row)==selected[key]
                    checked+=1;n+=1
                    if checked%256==0:peak=max(peak,process.memory_info().rss)
                batch_counts.append(n)
            assert sum(batch_counts)==count
            assert len(set(batch_counts))==1
        integrity=journal.check_database()
        for i,key in enumerate(selected):journal.export(key,output/('task-export-'+str(i)+'.json'))
    assert checked==written==50688
    result=dict(scope='Artificial full-count persistent metadata, not a native runtime or scientific test',
        main_task_headers=41472,cache_task_headers=9216,total=written,checked=checked,events=written*2,
        outcomes_are_artificial=counts,active_index_records=1,logical_record_bytes=logical,
        database_bytes=(root/'tasks.sqlite3').stat().st_size,sqlite_integrity=integrity,
        write_seconds=write_seconds,read_verify_seconds=time.perf_counter()-started,sampled_receiver_rss_peak_bytes=peak,
        source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),
        source_sha256={n:file_hash(source/n) for n in ['scripts/completion/task_journal.py','scripts/completion/batch_contract.py','scripts/completion/formal_measurement_plan.py']},
        script_sha256=file_hash(__file__),new_sampler_calls=0,new_formal_repetitions=0,
        Windows_runtime_validated=False,formal_protocol_frozen=False,selected_entry_sha256=selected,
        note='Durable metadata only. No inference timing, RAM bound, power-loss proof, full kernel lifecycle or formal output-size prediction.')
    atomic_json(output/'SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--technical-evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source.resolve(),a.technical_evidence.resolve(),a.output.resolve())
