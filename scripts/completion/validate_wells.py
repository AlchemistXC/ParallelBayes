"""Run the frozen external-target validation, with separate Stan and torch jobs.

This is an integration/correctness fixture, not a convergence or speed study.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"r-package/inst/python"))
sys.path.insert(0,str(ROOT/"examples"))
from external_wells import load_wells,make_wells,propriety_certificate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def plain(value):
    if isinstance(value,np.ndarray):return plain(value.tolist())
    if isinstance(value,np.generic):return plain(value.item())
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):return None
    return value


def write(path,value):
    path.write_text(json.dumps(plain(value),indent=2,allow_nan=False)+"\n",encoding="utf-8")


def verify_protocol(protocol_path):
    p=json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    unsigned=dict(p);expected=unsigned.pop("protocol_sha256")
    if identity(unsigned)!=expected:raise ValueError("Validation protocol checksum differs")
    for name,digest in p["source_files"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Validation source changed: "+name)
    return p


def run_validation(source_root,output,stage="torch",protocol_path=None,tape_from=None):
    output=Path(output).resolve();source_root=Path(source_root).resolve()
    if output.exists():raise FileExistsError("Use a fresh validation attempt")
    if output==source_root or source_root in output.parents:raise ValueError("Do not write into upstream evidence")
    p=verify_protocol(protocol_path or ROOT/"benchmark/protocols/external-wells-validation-v1.json")
    data=load_wells(source_root);certificate=propriety_certificate(data)
    if not certificate["certified"]:raise ValueError("Selected flat-prior target lacks required certificate")
    output.mkdir(parents=True)
    record=dict(protocol_sha256=p["protocol_sha256"],scientific_source_commit=p["source_commit"],
        stage=stage,status="started",source_manifest_sha256=sha(ROOT/"models/external/wells/source-manifest.json"),
        propriety=certificate,python=sys.version,platform=platform.platform(),
        scope="Model and fixed-tape integration validation only; not performance, convergence or posterior accuracy evidence")
    record["versions"]={name:importlib.metadata.version(name) for name in ["numpy","scipy"]}
    write(output/"started.json",record)
    last=None
    try:
        native=make_wells(data)
        record["target_id"]=native.target_id
        points=np.asarray(p["points"],float)
        if stage=="stan":
            # Compile a copy; never write compiler products into pinned sources.
            source=source_root/"posterior_database/models/stan/wells_dist100_model.stan"
            copied=output/source.name;shutil.copyfile(source,copied)
            from parallelbayes.stan import stan_model,cross_validate
            stan=stan_model(dict(stan_file=str(copied),data={k:data[k] for k in ["N","dist","switched"]}))
            check=cross_validate(stan,native,points)
            record.update(validation=check,compile_seconds=stan.compile_seconds,
                          parameter_names=stan.names,stan_model_sha256=sha(copied))
            record["versions"]["bridgestan"]=importlib.metadata.version("bridgestan")
            record["parameter_name_map"]=list(zip(stan.names,native.names))
            if not check["passed"] or stan.names!=p["stan_parameter_names"] or native.names!=p["output_names"]:
                raise ValueError("Stan/NumPy target contract failed")
        elif stage=="torch":
            import torch
            from parallelbayes import sample,validate_model
            from parallelbayes.torch_backend.sampling import random_tape,settings,tape_hash,environment
            torch.set_num_threads(p["torch_cpu_threads"])
            model=make_wells(data,"torch",p["base_config"]["device"])
            record["environment"]=environment()
            record["jax_imported"]="jax" in sys.modules
            record["versions"]["torch"]=torch.__version__
            record["validation"]=validate_model(model,points,backend="torch")
            if not record["validation"]["passed"]:raise ValueError("Torch/NumPy target contract failed")
            config=settings(p["base_config"])
            if tape_from is None:tape=random_tape(config,2)
            else:
                with np.load(Path(tape_from),allow_pickle=False) as archive:tape={k:archive[k].copy() for k in archive.files}
            record["tape_sha256"]=tape_hash(tape)
            if record["tape_sha256"]!=p["tape_sha256"]:raise ValueError("Actual arrays differ from frozen validation input")
            np.savez_compressed(output/"inputs.npz",**tape)
            record["tape_file_sha256"]=sha(output/"inputs.npz")
            runs={};record["runs"]=runs
            keys=["draws","unconstrained","accept","primary_accept","failed_trajectory","primary_failed_trajectory"]
            for workflow in p["workflows"]:
                name=workflow["kernel"]+"-"+workflow["executor"]
                result=sample(model,dict(config,**workflow),tape,backend="torch")
                arrays={k:result[k] for k in keys if result.get(k) is not None}
                np.savez_compressed(output/(name+".npz"),**arrays)
                small={k:v for k,v in result.items() if k not in keys}
                write(output/(name+".json"),small)
                runs[name]=dict(status=result["status"],audit=result["audit"],
                    accepted=int(np.asarray(result["accept"]).sum()),sample_seconds=result["timing"]["sample"],
                    raw_sha256=sha(output/(name+".npz")),record_sha256=sha(output/(name+".json")))
                # Keep every completed workflow/failed output before any rejection.
                if result["status"]=="completed":last=result["draws"]
            record["pairs"]=[]
            for kernel,executor in [("mala","quasi_deer"),("rwm","online_picard")]:
                left=kernel+"-sequential";right=kernel+"-"+executor
                if runs[left]["status"]!="completed" or runs[right]["status"]!="completed":
                    record["pairs"].append(dict(kernel=kernel,passed=False,reason="workflow failed"));continue
                with np.load(output/(left+".npz"),allow_pickle=False) as a,np.load(output/(right+".npz"),allow_pickle=False) as b:
                    error=float(np.max(np.abs(a["unconstrained"]-b["unconstrained"])))
                    mismatches=int(np.sum(a["accept"]!=b["accept"]))
                passed=error<=p["paired_atol"] and mismatches==0
                record["pairs"].append(dict(kernel=kernel,max_path_difference=error,acceptance_mismatches=mismatches,passed=passed))
            if not all(r["status"]=="completed" for r in runs.values()) or not all(r["passed"] for r in record["pairs"]):
                raise ValueError("External target fixed-tape workflow verification failed")
        else:raise ValueError("Unknown validation stage")
        record["status"]="passed"
    except Exception as exc:
        import traceback
        record.update(status="failed",error=f"{type(exc).__name__}: {exc}",traceback=traceback.format_exc())
        last=None
    write(output/"result.json",record)
    checks={f.name:sha(f) for f in output.iterdir() if f.is_file()}
    write(output/"checksums.json",checks)
    return dict(record=plain(record),draws=None if last is None else np.transpose(last,(1,0,2)))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stage",choices=["stan","torch"],required=True)
    parser.add_argument("--protocol",type=Path)
    parser.add_argument("--tape-from",type=Path)
    args=parser.parse_args()
    r=run_validation(args.source,args.output,args.stage,args.protocol,args.tape_from)
    print(json.dumps(r["record"],indent=2))
    sys.exit(0 if r["record"]["status"]=="passed" else 1)
