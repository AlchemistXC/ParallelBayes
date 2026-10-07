"""Wait for a specific real native manager, then archive/read the closed study.

No sampling/retry/recovery is performed. All directories are new. Every failed
gate preserves its evidence and stops the postprocessing sequence. Holding a
process synchronization handle does not retain a Job's kill-on-close handle.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import uuid


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def wait_for_manager(record, output):
    k=C.WinDLL('kernel32',use_last_error=True)
    opened=k.OpenProcess;opened.argtypes=[W.DWORD,W.BOOL,W.DWORD];opened.restype=W.HANDLE
    times=k.GetProcessTimes;times.argtypes=[W.HANDLE,*[C.POINTER(W.FILETIME)]*4];times.restype=W.BOOL
    wait=k.WaitForSingleObject;wait.argtypes=[W.HANDLE,W.DWORD];wait.restype=W.DWORD
    close=k.CloseHandle;close.argtypes=[W.HANDLE];close.restype=W.BOOL
    h=opened(0x1000|0x100000,False,record['pid'])
    if not h:raise C.WinError(C.get_last_error())
    begin=time.perf_counter()
    try:
        values=[W.FILETIME() for _ in range(4)]
        if not times(h,*[C.byref(v) for v in values]):raise C.WinError(C.get_last_error())
        creation=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
        if creation!=record['creation_filetime']:raise ValueError('Manager PID was reused; refuse')
        while True:
            result=wait(h,30000)
            if result==0:break
            if result!=258:raise C.WinError(C.get_last_error())
            write(output/'WAITING.json',dict(manager_identity=record,native_process_handle_is_held=True,
                observed_utc=datetime.now(timezone.utc).isoformat(),scientific_timeout=False))
        write(output/'MANAGER-ENDED.json',dict(manager_identity=record,native_process_signaled=True,
            wait_seconds=time.perf_counter()-begin,timestamp_is_not_duration=True,
            descendants_not_inferred_from_primary_exit=True))
    finally:close(h)


def write(path,value):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


def inventory(root):
    return {str(p.relative_to(root)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=sha(p))
            for p in root.rglob('*') if p.is_file()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--sequence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();cfg=json.loads(a.config.read_text(encoding='utf-8-sig'))
    root=Path(cfg['root']);bundle=Path(cfg['bundle']);reader=Path(__file__).resolve().parents[2]
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(root/'scripts/windows'),str(root/'scripts/completion')]
    from job_objects import Job,observe_named_job,identity
    from formal_freeze import verify_sealed_study
    from formal_execution import StudyDispatch
    from formal_batch import verify_phase_closure
    from formal_runtime import host_lease
    from formal_owned_runtime import Coordinator
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    env.pop('PYTHONPATH',None)
    started=json.loads((a.sequence/'started.json').read_text())
    bound_sources={str(f.relative_to(reader)).replace('\\','/'):sha(f) for f in
        (reader/'scripts/analysis').glob('*.py')}
    write(out/'STARTED.json',dict(manager_identity=identity(os.getpid()),sequence=str(a.sequence.resolve()),
        watched_manager=started['manager_identity'],configuration=cfg,helper_sha256=sha(__file__),
        reader_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=reader,text=True).strip(),
        reader_sources=bound_sources,started_utc=datetime.now(timezone.utc).isoformat(),sampler_calls=0,
        no_automatic_retry=True,no_total_scientific_time_cutoff=True))
    def call(name,argv,cwd):
        folder=out/name;folder.mkdir(exist_ok=False)
        write(folder/'started.json',dict(argv=argv,cwd=str(cwd),started_utc=datetime.now(timezone.utc).isoformat(),
            scope='Whole postprocessing CLI/descendant wall; nested boundaries not additive'))
        begin=time.perf_counter()
        with Job('Local\\ParallelBayes-formal-post-'+uuid.uuid4().hex) as job:
            write(folder/'job.json',dict(name=job.name,kill_on_last_handle_close=True))
            with (folder/'stdout.log').open('xb') as stdout,(folder/'stderr.log').open('xb') as stderr:
                write(folder/'primary.json',job.launch_suspended(argv,cwd,stdout,stderr,env));job.resume()
                while job.poll() is None or job.observe()['active_processes']:
                    write(folder/'live.json',dict(observed_utc=datetime.now(timezone.utc).isoformat(),native_job=job.observe()))
                    time.sleep(5)
                code=job.poll();final=job.observe()
        write(folder/'finished.json',dict(exit_code=code,native_job_final=final,seconds=time.perf_counter()-begin,
            log_sha256={n:sha(folder/n) for n in ('stdout.log','stderr.log')}))
        if code!=0 or final['active_processes']!=0:raise RuntimeError('Postprocessing failed: '+name)
        return folder
    begin=time.perf_counter()
    try:
        wait_for_manager(started['manager_identity'],out)
        complete=json.loads((a.sequence/'finished.json').read_text())
        if complete['formal_study_execution_framework_closed'] is not True or len(complete['completed_phases'])!=8:
            raise ValueError('Scientific sequence incomplete; never resume/execute it from postprocessing')
        for intent in a.sequence.glob('*.job.json'):
            proof=observe_named_job(json.loads(intent.read_text())['name'])
            if proof['state']=='present' and proof['active_processes']:raise ValueError('Scientific descendants remain')
        marker,protocol=verify_sealed_study(bundle)
        plan=json.loads((bundle/'study-plan.json').read_text());catalog=json.loads((bundle/'catalog.json').read_text())
        dispatch=StudyDispatch(protocol,plan['cache_allocation'],catalog)
        phases=[]
        for batch in range(4):
            for phase in ('main','cache'):
                directory=bundle/'formal-runs'/f'batch-{batch:02d}'/phase
                pointer=verify_phase_closure(directory,dispatch,batch,phase)
                phases.append(json.loads((directory/pointer['summary']).read_text())['summary'])
        with host_lease(Path(cfg['host_lock']),'Formal archive boundary, no sampling'):
            if Coordinator(Path(cfg['host_lock']))._read()['tasks']:raise ValueError('Active scientific registration')
        write(out/'CLOSED-FRAME.json',dict(identity=protocol['identity'],protocol_sha256=protocol['protocol_sha256'],
            source_commit=protocol['source_commit'],phases=phases,all_owned_scientific_descendants_ended=True,
            convergence_claim=False,independent_Mac_intake_complete=False))
        for name,digest in bound_sources.items():
            if sha(reader/name)!=digest:raise ValueError('Bound reader source changed: '+name)
        # No compression forecast: check actual file bytes before making copies.
        original_bytes=sum(f.stat().st_size for base in (bundle,Path(cfg['costs'])) for f in base.rglob('*') if f.is_file())
        disks={v:shutil.disk_usage(v)._asdict() for v in ('C:/','D:/')}
        write(out/'STORAGE-BEFORE-ARCHIVE.json',dict(original_file_bytes=original_bytes,disks=disks,
            tar_allowance_bytes=original_bytes+2*1024**3,analysis_allowance_bytes=200*1024**3,
            future_capacity_not_guaranteed=True))
        if disks['D:/']['free']<original_bytes+152*1024**3:
            raise OSError('Resource wait: actual tar plus declared D reserve does not fit; retain originals')
        if disks['C:/']['free']<original_bytes+600*1024**3:
            raise OSError('Resource wait: fresh extraction/analysis plus C OS reserve does not fit')
        archive_dir=root/'output/formal-return'
        if archive_dir.exists():raise FileExistsError('Archive output already exists; retain it')
        folder=call('01-export',[cfg['python'],'scripts/windows/export_results.py','--run',
            'output/windows-formal-inference-v1','--include','output/formal-costs-v1','--output','output/formal-return'],root)
        archives=list(archive_dir.glob('*.tar'))
        if len(archives)!=1:raise ValueError('Ambiguous exported tar')
        archive=archives[0]
        call('02-verify-archive',[cfg['python'],str(reader/'scripts/verify-windows-return.py'),str(archive),
            '--output',str(out/'archive-verification.json')],reader)
        delivery=Path('C:/ParallelBayes-formal-delivery-v1')
        call('03-extract',[cfg['python'],str(reader/'scripts/windows/extract_verified_return.py'),str(archive),
            '--destination',str(delivery),'--receipt',str(out/'relocation.json')],reader)
        manifest_hash=sha(delivery/'WINDOWS-RETURN-MANIFEST.json')
        # Explicitly deny ordinary writes/deletes only on this newly verified
        # delivery. The owner may later remove this documented rule; no old
        # checkout, input archive, environment or analysis directory is changed.
        acl_code='$p="C:\\ParallelBayes-formal-delivery-v1"; '+\
            '$acl=Get-Acl -LiteralPath $p; '+\
            '$sid=[System.Security.Principal.SecurityIdentifier]::new("S-1-5-11"); '+\
            '$r=[System.Security.AccessControl.FileSystemAccessRule]::new($sid,'+\
            '[System.Security.AccessControl.FileSystemRights]"Write,Delete,DeleteSubdirectoriesAndFiles",'+\
            '[System.Security.AccessControl.InheritanceFlags]"ContainerInherit,ObjectInherit",'+\
            '[System.Security.AccessControl.PropagationFlags]::None,'+\
            '[System.Security.AccessControl.AccessControlType]::Deny); '+\
            '$acl.AddAccessRule($r); Set-Acl -LiteralPath $p -AclObject $acl; '+\
            'Get-Acl -LiteralPath $p | Select-Object Path,Sddl | ConvertTo-Json'
        call('03b-readonly-delivery',['pwsh','-NoProfile','-NonInteractive','-Command',acl_code],reader)
        analysis_root=Path('C:/ParallelBayes-formal-analysis-v1')
        analysis_root.mkdir(parents=True,exist_ok=False)
        index,analysis,statistics,report=(analysis_root/n for n in ('index','analysis','statistics','report'))
        call('04-index',[cfg['python'],str(reader/'scripts/analysis/formal_analyze.py'),'index','--delivery',str(delivery),
            '--bundle-relative','output/windows-formal-inference-v1','--manifest-sha256',manifest_hash,'--output',str(index)],reader)
        command=[cfg['python'],str(reader/'scripts/analysis/formal_analyze.py'),'run','--delivery',str(delivery),
            '--index',str(index),'--output',str(analysis),'--rscript',cfg['rscript'],'--r-library',cfg['r_library']]
        call('05-raw-analysis',command,reader)
        # The original delivery is not written by any of the reader commands.
        before=inventory(analysis);write(out/'analysis-before-resume.json',before)
        (out/'analysis-summary-before-resume.json').write_bytes((analysis/'SUMMARY.json').read_bytes())
        call('06-analysis-resume',command+['--resume'],reader)
        after=inventory(analysis);write(out/'analysis-after-resume.json',after)
        resume_summary=json.loads((analysis/'SUMMARY.json').read_text())
        before_immutable={k:v for k,v in before.items() if k!='SUMMARY.json'}
        after_immutable={k:v for k,v in after.items() if k!='SUMMARY.json'}
        write(out/'analysis-resume-invariance.json',dict(new_analyses=resume_summary['new_analyses'],
            reused_analyses=resume_summary['reused_analyses'],
            immutable_assets_unchanged=before_immutable==after_immutable,
            summary_bookkeeping_changed=before.get('SUMMARY.json')!=after.get('SUMMARY.json'),
            scope='Task/science/identity/database assets; mutable SUMMARY.json retained separately'))
        if (before_immutable!=after_immutable or resume_summary['new_analyses']!=0 or
                resume_summary['reused_analyses']!=50688):
            raise ValueError('Immutable analysis assets changed or resume replayed tasks; preserve inventories')
        call('07-statistics',[cfg['python'],str(reader/'scripts/analysis/formal_statistics.py'),'--delivery',str(delivery),
            '--index',str(index),'--analysis',str(analysis),'--output',str(statistics)],reader)
        call('08-report',[cfg['python'],str(reader/'scripts/analysis/formal_report.py'),'--statistics-directory',str(statistics),
            '--manifest-sha256',sha(statistics/'SHA256.json'),'--output',str(report)],reader)
        write(out/'FINISHED.json',dict(status='local_archive_and_read_only_analysis_completed',
            archive=str(archive),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
            delivery=str(delivery),manifest_sha256=manifest_hash,analysis=str(analysis),statistics=str(statistics),
            report=str(report),analysis_terminal_resume_immutable_assets_unchanged=True,
            analysis_summary_is_mutable_bookkeeping=True,
            post_sequence_seconds_including_wait=time.perf_counter()-begin,
            independent_Mac_intake_complete=False,final_manuscript_complete=False,
            draft_upload_complete=False,formal_research_complete=False))
        return 0
    except BaseException as exc:
        write(out/'FAILED.json',dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
            known_post_sequence_seconds_including_wait=time.perf_counter()-begin,sampler_calls=0,
            preserve_partial_outputs=True,automatic_retry=False,formal_research_complete=False))
        raise


if __name__=='__main__':sys.exit(main())
