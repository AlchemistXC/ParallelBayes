"""Freeze a finite external-model correctness protocol, before running it."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"r-package/inst/python"))
from parallelbayes.torch_backend.sampling import random_tape,settings,tape_hash


def freeze(protocol,inputs):
    if protocol.exists() or inputs.exists():raise FileExistsError("Do not overwrite a frozen identity or input")
    if subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip():
        raise RuntimeError("Commit the validation source before freezing")
    config=settings(dict(draws=96,chains=4,window=16,max_iter=1024,device="cpu",audit=True,
        seed=983105,solver_seed=983106,step_size=.0005,
        initial=[[0.,0.],[.8,-1.2],[-.5,.5],[1.,-2.]],on_failure="error"))
    tape=random_tape(config,2)
    names=list(json.loads((ROOT/"benchmark/protocols/windows-native-v1.json").read_text())["source_files"])
    names += ["examples/external_wells.py","examples/external_wells.R",
              "scripts/completion/validate_wells.py","scripts/completion/freeze_wells_validation.py",
              "models/external/wells/source-manifest.json"]
    source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(set(names))}
    p=dict(identity=protocol.stem,stage="model and fixed-tape correctness only",
        source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        source_files=source,created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        base_config=config,torch_cpu_threads=1,tape_sha256=tape_hash(tape),
        points=[[0.,0.],[.5,-.5],[1.,-1.],[-2.,2.],[8.,-8.],[-8.,8.],[.2,-.6]],
        stan_parameter_names=["alpha","beta.1"],output_names=["alpha","beta[1]"],
        target_check="same coordinates; density up to constant; gradient and identity transform; NumPy finite-difference HVP",
        paired_atol=1e-7,acceptance_mismatches_allowed=0,
        workflows=[dict(kernel=k,executor=e,step_size=s) for k,e,s in
            [("mala","sequential",.0005),("mala","quasi_deer",.0005),
             ("rwm","sequential",.05),("rwm","online_picard",.05)]],
        replication="one actual tape with four chains; R integration reuses it, not an independent statistical replicate",
        inference_claim="none; no warmup, accuracy or speed conclusion from this validation",
        runtime="record actual Mac CPU dependencies per stage; Windows/CUDA requires separate actual validation",
        failure="save invalid arrays and errors; never return failed trajectories as ordinary draws; no fallback",
        memory="2048 MiB estimated workspace guard; no global experiment timeout")
    p["protocol_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    protocol.parent.mkdir(parents=True,exist_ok=True);inputs.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(inputs,**tape)
    protocol.write_text(json.dumps(p,indent=2)+"\n")
    print(json.dumps(dict(protocol_sha256=p["protocol_sha256"],tape_sha256=p["tape_sha256"],
        input_file_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest(),source_commit=p["source_commit"]),indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol",type=Path,default=ROOT/"benchmark/protocols/external-wells-validation-v1.json")
    parser.add_argument("--inputs",type=Path,required=True)
    a=parser.parse_args();freeze(a.protocol.resolve(),a.inputs.resolve())
