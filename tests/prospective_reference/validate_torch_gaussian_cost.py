"""Validate development-domain dense Gaussian costs against exact statistics."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
from gaussian_cost import build


def digest(path):
    h=sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda:file.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(output, device):
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable; no substitution")
    output.mkdir()
    torch.set_num_threads(1)
    reports=[]
    for d in (8,128):
        for m in (256,2048,16384,65536):
            started=time.monotonic()
            model,(x,y,diagonal,linear)=build(d,m,device)
            points=np.stack((np.zeros(d),np.linspace(-2,2,d),np.linspace(2,-2,d)))
            name=f"d{d}-m{m}.npz"
            with (output/name).open("xb") as file:
                np.savez(file,design=x,response=y,diagonal=diagonal,linear=linear,points=points)
            gram=float(np.max(np.abs(x.T@x-np.diag(diagonal))))
            cross=float(np.max(np.abs(x.T@y-linear)))
            yy=float(abs(y@y-(np.sum(linear**2/diagonal)+1)))
            errors=[]
            for point in points:
                q=torch.tensor(point,dtype=torch.float64,device=device,requires_grad=True)
                value=model.log_density(q)
                grad=torch.autograd.grad(value,q)[0]
                if q.device.type == "cuda": torch.cuda.synchronize(q.device)
                errors.append([abs(float(value.detach().cpu())-model.reference(point)),
                               float(np.max(np.abs(grad.detach().cpu().numpy()-model.gradient_reference(point))))])
            density,gradient=np.max(errors,axis=0)
            row={"dimension":d,"rows":m,"gram_error":gram,"cross_error":cross,"response_error":yy,
                 "density_error":float(density),"gradient_error":float(gradient),
                 "actual_input":name,"actual_input_sha256":digest(output/name),
                 "seconds":time.monotonic()-started}
            row["passed"]=bool(np.isfinite([gram,cross,yy,density,gradient]).all()
                               and max(gram,cross,yy,density,gradient)<=1e-8)
            reports.append(row)
            print(json.dumps(row,allow_nan=False),flush=True)
    report={"scope":"development dimensions 8 and 128 only; no held-out dimension 32",
            "device":device,"torch":torch.__version__,"rows":reports,
            "passed":len(reports)==8 and all(r["passed"] for r in reports)}
    with (output/"receipt.json").open("x") as file:
        json.dump(report,file,indent=2,allow_nan=False);file.write("\n")
    if not report["passed"]:
        raise SystemExit("one or more Gaussian static checks failed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    args=parser.parse_args()
    main(args.output,args.device)
