"""Transfer candidate input bytes without substituting or overwriting evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

MEMBERS = ("manifest.json", "data.npz", "initials.npz")


def digest(data):
    return sha256(data).hexdigest()


def read_candidates(root):
    contents = {name: (root/name).read_bytes() for name in MEMBERS}
    manifest = json.loads(contents["manifest.json"])
    for name, key in (("data.npz","data_sha256"), ("initials.npz","initials_sha256")):
        if digest(contents[name]) != manifest[key]:
            raise ValueError(f"candidate input hash mismatch: {name}")
    if manifest["scope"] != "candidate, not yet frozen or authorized for formal sampling":
        raise ValueError("unexpected candidate scope")
    return contents


def pack(root, output):
    contents = read_candidates(root)
    with output.open("xb") as target:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in MEMBERS:
                entry = zipfile.ZipInfo(name, date_time=(2026,1,1,0,0,0))
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, contents[name])


def verify(path, expected):
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("expected bundle hash must be lowercase SHA-256")
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError("external bundle hash mismatch")
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != list(MEMBERS):
            raise ValueError("bundle member list differs")
        if any(item.file_size > 1024*1024 for item in archive.infolist()):
            raise ValueError("candidate member unexpectedly large")
        contents = {name: archive.read(name) for name in MEMBERS}
    manifest = json.loads(contents["manifest.json"])
    if manifest["scope"] != "candidate, not yet frozen or authorized for formal sampling":
        raise ValueError("candidate scope differs")
    for name, key in (("data.npz","data_sha256"), ("initials.npz","initials_sha256")):
        if digest(contents[name]) != manifest[key]:
            raise ValueError(f"bundle member hash mismatch: {name}")
    return contents


def unpack(path, expected, output):
    contents = verify(path, expected)
    output.mkdir()
    for name, data in contents.items():
        with (output/name).open("xb") as file:
            file.write(data)
    read_candidates(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("pack")
    make.add_argument("inputs", type=Path)
    make.add_argument("output", type=Path)
    check = commands.add_parser("verify")
    check.add_argument("archive", type=Path)
    check.add_argument("expected_sha256")
    extract = commands.add_parser("unpack")
    extract.add_argument("archive", type=Path)
    extract.add_argument("expected_sha256")
    extract.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.inputs,args.output)
        print(f"bundle_sha256={digest(args.output.read_bytes())}")
    elif args.command == "verify":
        verify(args.archive,args.expected_sha256)
        print("candidate bundle verified")
    else:
        unpack(args.archive,args.expected_sha256,args.output)
        print("candidate bundle unpacked and verified")
