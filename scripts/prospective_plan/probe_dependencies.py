"""Record Python and R prerequisites without running inference."""
import argparse
from importlib import metadata, util
import json
import platform
from pathlib import Path
import subprocess
import sys


def package(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def inspect(rscript):
    names = ("numpy", "scipy", "torch", "pyro-ppl", "psutil")
    record = {"scope":"prerequisite inventory, no inference or compiler execution",
              "platform":platform.platform(), "python":sys.version,
              "python_executable":sys.executable,
              "packages":{name:package(name) for name in names},
              "torch_compile_symbol":False, "rscript":str(rscript), "r_result":None}
    if util.find_spec("torch"):
        import torch
        record["torch_compile_symbol"] = callable(getattr(torch, "compile", None))
    try:
        command = [str(rscript), "--vanilla", "-e",
                   "cat(R.version.string,'\\n'); for(p in c('posterior','jsonlite')) {"
                   "if(!requireNamespace(p,quietly=TRUE)) quit(status=2);"
                   "cat(p,as.character(packageVersion(p)),'\\n') }"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        record["r_result"] = {"exit_code":result.returncode, "stdout":result.stdout, "stderr":result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        record["r_result"] = {"error":str(error)}
    record["nuts_available"] = all(record["packages"][p] for p in names)
    record["r_diagnostics_available"] = record["r_result"].get("exit_code") == 0
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rscript", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.rscript)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result,file,indent=2,ensure_ascii=False)
    print(json.dumps({"nuts_available":result["nuts_available"],
                      "r_diagnostics_available":result["r_diagnostics_available"]}))
