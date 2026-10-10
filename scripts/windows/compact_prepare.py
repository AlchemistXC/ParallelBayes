"""Native compact preparation: fresh addresses, immutable files, no sampling."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows'),str(ROOT/'scripts/analysis'),
    str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from compact_contract import create_plan
from compact_freeze import seal,verify
from formal_freeze import InputArchive,input_bytes,relative_file,FreezeConflict
from formal_runtime import atomic_json,file_hash,host_lease,ResourceWait
from prepare_formal_study import sources as historical_sources,snapshot_file,write_once,gather_environment,LIMITS,CATALOG


def source_files():
    found=historical_sources()
    names=subprocess.check_output(['git','ls-files','scripts/analysis','tests/handoff','tests/windows',
        'benchmark/designs/windows-compact-inference-v1'],cwd=ROOT,text=True).splitlines()
    # Bind analysis plus every finite validation source/fixture, not a version label.
    for name in names:
        if name.endswith(('.py','.R','.json')):
            h=file_hash(ROOT/name)
            if h!=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest():
                raise FreezeConflict('Canonical committed source/test/design bytes required: '+name)
            found[name]=h
    return dict(sorted(found.items()))


def prepare(output,external,host_lock,rscript,r_library,*,technical=False,resume=False,recover_input=None,recovery_reason=None):
    if sys.platform!='win32':raise FreezeConflict('Actual native Windows required')
    if bool(recover_input)!=bool(recovery_reason) or (recover_input and not resume):
        raise FreezeConflict('Explicit named unsealed input recovery and reason required')
    output,external,host_lock,rscript,r_library=map(lambda p:Path(p).resolve(),(output,external,host_lock,rscript,r_library))
    if not output.parent.is_dir() or host_lock.is_relative_to(output):raise FreezeConflict('Existing parent and external shared host lock required')
    with host_lease(host_lock,'prepare separate compact actual inputs'):
        from formal_owned_runtime import Coordinator
        coordinator=Coordinator(host_lock);coordinator._reconcile(coordinator._read())
        plan=create_plan(ROOT,technical=technical);files=source_files()
        env,probe,resources,pip_lock,pip_check=gather_environment(rscript,r_library)
        from external_wells import load_wells,propriety_certificate
        if not propriety_certificate(load_wells(external))['certified']:raise FreezeConflict('W1 fixed source/propriety check failed')
        external_files={r['path']:r['sha256'] for r in json.loads((ROOT/'models/external/wells/source-manifest.json').read_text())['files']}
        binding=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            source_files=files,external_files=external_files,environment=env,
            required_versions={n:importlib.metadata.version(n) for n in ('numpy','scipy','torch','pyro-ppl','psutil')},
            required_R_version=env['required_R_version'],required_R_posterior=env['required_R_posterior'],
            windows_limits=LIMITS,minimum_available_ram_bytes=12*1024**3,shared_host_lock=str(host_lock),
            storage_policy=dict(maximum_bundle_bytes=(2 if technical else 35)*1024**3,
                window_additional_allocation_bytes=40*1024**3,receiver_planned_allocation_bytes=35*1024**3,
                maximum_transfer_block_bytes=1024**3,scope='Per-volume conditional capacity; receiver capacity is not Windows capacity',
                volume=str(output.anchor),whole_tar_allowed=False),
            execution_plan_sha256=plan['plan_sha256'],compact_contract_schema='compact-execution-plan-v1')
        if resources['ram_available']<binding['minimum_available_ram_bytes'] or resources['gpu_free_bytes']<plan['controls']['minimum_gpu_free_bytes']:
            raise ResourceWait('Compact preparation RAM/GPU reserve refused')
        needed=sum(input_bytes(r)+65536 for r in plan['input_requirements'].values())
        reserve=max(needed+8*1024**3,binding['storage_policy']['maximum_bundle_bytes']+1024**3)
        if shutil.disk_usage(output.parent).free<reserve:raise ResourceWait('Compact full local allocation/preparation reserve refused')
        archive=InputArchive(output,plan['identity'],plan['input_requirements'],binding,resume=resume)
        if recover_input:archive.recover_unsealed_input(recover_input,reason=recovery_reason)
        if (output/'FROZEN.json').exists():
            marker,_,_,_=verify(output);return dict(marker,newly_generated_inputs=0)
        documents={'study-plan.json':plan,'catalog.json':json.loads((ROOT/CATALOG).read_text()),'environment.json':env}
        for name,value in documents.items():write_once(output/name,json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
        write_once(output/'pip-freeze.txt',pip_lock);write_once(output/'pip-check.txt',pip_check)
        bound={name:file_hash(output/name) for name in [*documents,'pip-freeze.txt','pip-check.txt']}
        for prefix,original,inventory in [('source/',ROOT,files),('external/',external,external_files)]:
            for name,digest in inventory.items():
                snapshot_file(relative_file(output,prefix+name),original/name,digest);bound[prefix+name]=digest
        from formal_inputs import validate_addresses
        models=sorted({r['model'] for r in plan['input_requirements'].values()})
        reps=sorted({r['replicate'] for r in plan['input_requirements'].values()})
        write_once(output/'address-check.json',json.dumps(validate_addresses(plan['identity'],models,reps),sort_keys=True,indent=2)+'\n')
        bound['address-check.json']=file_hash(output/'address-check.json')
        call=output/'preparation-calls'/uuid.uuid4().hex;call.mkdir(parents=True,exist_ok=False)
        atomic_json(call/'resources.json',dict(resources,disk=shutil.disk_usage(output)._asdict(),
            scope='Preparation/individual-task reserves; not entire-study capacity guarantee'))
        atomic_json(call/'probe.json',probe)
        start=time.perf_counter();generated=0
        try:
            import psutil
            for name in sorted(plan['input_requirements']):
                if psutil.virtual_memory().available<binding['minimum_available_ram_bytes']:
                    raise ResourceWait('Compact input boundary RAM reserve refused')
                existed=(output/'receipts'/(name+'.json')).exists()
                receipt=archive.prepare(name,maximum_member_bytes=plan['controls']['maximum_member_bytes'])
                generated+=not existed
                print(json.dumps(dict(input=name,newly_generated=not existed,file_sha256=receipt['sha256'],actual_sha256=receipt['actual_sha256'])),flush=True)
            for p in (output/'preparation-recovery').rglob('*'):
                if p.is_file():bound[p.relative_to(output).as_posix()]=file_hash(p)
            result=seal(output,plan,archive,binding,bound)
            atomic_json(call/'finished.json',dict(generated_inputs=generated,preparation_seconds=time.perf_counter()-start,
                sampler_calls=0,identity=plan['identity']))
            return result
        except BaseException as exc:
            atomic_json(call/'failed.json',dict(generated_inputs=generated,preparation_seconds=time.perf_counter()-start,
                error=type(exc).__name__+': '+str(exc),sampler_calls=0));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for name in ('output','external','host-lock','rscript','r-library'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--technical',action='store_true');p.add_argument('--resume',action='store_true')
    p.add_argument('--recover-input');p.add_argument('--recovery-reason')
    p=sub.add_parser('verify');p.add_argument('--bundle',type=Path,required=True)
    args=vars(parser.parse_args());cmd=args.pop('command')
    result=prepare(**args) if cmd=='prepare' else verify(args['bundle'])[0]
    print(json.dumps(result,indent=2),flush=True)
