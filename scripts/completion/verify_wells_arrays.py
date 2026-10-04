"""Replay the saved external-case arrays with NumPy only, including R transport."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"r-package/inst/python"))
sys.path.insert(0,str(ROOT/"examples"))
from parallelbayes.reference import numpy_reference
from external_wells import make_wells,load_wells


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(source,evidence,output):
    if output.exists():raise FileExistsError("Preserve prior replay receipts")
    p=json.loads((ROOT/"benchmark/protocols/external-wells-validation-v1.json").read_text())
    for name in ["examples/external_wells.py","r-package/inst/python/parallelbayes/reference.py"]:
        if sha(ROOT/name)!=p["source_files"][name]:raise ValueError("Oracle or target source changed")
    model=make_wells(load_wells(source))
    config=p["base_config"]
    with np.load(ROOT/"benchmark/fixtures/wells-validation-v1/inputs.npz",allow_pickle=False) as z:
        tape={k:z[k].copy() for k in z.files}
    h=hashlib.sha256()
    for k in sorted(tape):
        a=np.ascontiguousarray(tape[k],dtype="<f8");h.update(k.encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    if h.hexdigest()!=p["tape_sha256"]:raise ValueError("Frozen actual array identity differs")
    references={}
    for workflow in p["workflows"]:
        if workflow["executor"]!="sequential":continue
        paths=[];events=[]
        for i in range(config["chains"]):
            q,accept=numpy_reference(model,workflow["kernel"],np.asarray(config["initial"][i]),tape["noise"][i],tape["log_uniform"][i],workflow["step_size"])
            paths.append(q);events.append(accept)
        references[workflow["kernel"]]=(np.stack(paths),np.stack(events))
    rows=[];saved={}
    for label,folder in [("torch-v1",evidence/"torch-v1"),("R-v2",evidence/"R-v2/python")]:
        checks=json.loads((folder/"checksums.json").read_text())
        for name,digest in checks.items():
            if sha(folder/name)!=digest:raise ValueError("Saved task checksum mismatch: "+name)
        for workflow in p["workflows"]:
            name=workflow["kernel"]+"-"+workflow["executor"]
            record=json.loads((folder/(name+".json")).read_text())
            if record["status"]!="completed" or record["config"]!=dict(config,**workflow):
                raise ValueError("Failed or altered workflow configuration")
            if record["target_id"]!=model.target_id or record["tape_sha256"]!=p["tape_sha256"]:
                raise ValueError("Different target or actual input")
            with np.load(folder/(name+".npz"),allow_pickle=False) as z:
                path=z["unconstrained"].copy();accept=z["accept"].copy();draws=z["draws"].copy()
            expected,expected_accept=references[workflow["kernel"]]
            if not np.array_equal(path,draws):raise ValueError("Identity parameter transform differs")
            errors=np.max(np.abs(path-expected),axis=(1,2))
            limits=np.array([100*(config["atol"]+config["rtol"]*max(1.,float(np.abs(q).max()))) for q in path])
            events=int(np.sum(accept!=expected_accept))
            if not np.isfinite(path).all() or (errors>limits).any() or events:
                raise ValueError("Independent oracle mismatch")
            saved[label,name]=(draws,accept)
            rows.append(dict(run=label,workflow=name,max_path_error=float(errors.max()),acceptance_mismatches=events,raw_sha256=sha(folder/(name+".npz"))))
    for workflow in p["workflows"]:
        name=workflow["kernel"]+"-"+workflow["executor"]
        if not all(np.array_equal(a,b) for a,b in zip(saved["torch-v1",name],saved["R-v2",name])):
            raise ValueError("R replay differs from first Python run")
    expected=np.transpose(saved["R-v2","rwm-online_picard"][0],(1,0,2)).astype("<f8").ravel(order="F").tobytes()
    if (evidence/"R-v2/draws-f64le.bin").read_bytes()!=expected:raise ValueError("R array byte order/value mismatch")
    report=dict(status="passed",source_script_sha256=sha(Path(__file__)),
        independent_oracle_chains=8,verified_workflows=8,independent_random_tapes=1,
        torch_imported="torch" in sys.modules,jax_imported="jax" in sys.modules,
        R_replay_samples_and_events_identical=True,R_serialized_array_byte_identical=True,
        scope="Independent NumPy trajectory and R transport audit; no inference or speed claim",rows=rows)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--evidence",type=Path,default=ROOT/"benchmark/analysis/outputs/wells-validation")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();verify(a.source.resolve(),a.evidence.resolve(),a.output.resolve())
