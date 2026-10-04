"""Retrieve one pinned public case; verify cached files without overwriting them."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request


def fetch(manifest, output):
    spec=json.loads(manifest.read_text(encoding="utf-8"))
    commit=spec["upstream_commit"]
    if len(commit)!=40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Expected an immutable upstream Git SHA")
    base="https://raw.githubusercontent.com/stan-dev/posteriordb/"+commit+"/"
    checked=[]
    for row in spec["files"]:
        rel=PurePosixPath(row["path"])
        if rel.is_absolute() or ".." in rel.parts or "\\" in row["path"]:
            raise ValueError("Unsafe source path")
        path=output.joinpath(*rel.parts)
        if path.exists():
            b=path.read_bytes();origin="verified_cache"
        else:
            with urllib.request.urlopen(base+row["path"],timeout=45) as response:
                b=response.read(row["bytes"]+1)
            origin="downloaded"
        if len(b)!=row["bytes"] or hashlib.sha256(b).hexdigest()!=row["sha256"]:
            raise ValueError("Source size/checksum mismatch; existing file is not replaced: "+row["path"])
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("xb") as stream:stream.write(b)
        checked.append(dict(path=row["path"],origin=origin,sha256=row["sha256"]))
    print(json.dumps(dict(upstream_commit=commit,files=checked),indent=2))


if __name__=="__main__":
    root=Path(__file__).resolve().parents[2]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,default=root/"models/external/wells/source-manifest.json")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();fetch(a.manifest.resolve(),a.output.resolve())
