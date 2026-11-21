"""Make and independently verify a self-contained SQLite checkpoint snapshot."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
import sys


def file_digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(database):
    if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    identity_rows = database.execute("SELECT singleton,value FROM identity").fetchall()
    if len(identity_rows) != 1 or identity_rows[0][0] != 1:
        raise ValueError("checkpoint identity is missing or duplicated")
    identity = json.loads(identity_rows[0][1])
    previous = -1
    count = 0
    for last, first, payload, checksum in database.execute(
            "SELECT last_step,first_step,payload,checksum FROM blocks ORDER BY last_step"):
        if (first != previous + 1 or last < first or (count == 0 and (first, last) != (0, 0))
                or (last > 0 and last-first != 99)):
            raise ValueError("checkpoint block sequence differs")
        if sha256(payload).hexdigest() != checksum:
            raise ValueError("checkpoint payload checksum mismatch")
        previous, count = last, count + 1
    if count == 0:
        raise ValueError("checkpoint has no warmup state")
    return {"identity": identity, "blocks": count, "last_step": previous}


def backup(source, output):
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("source must be an existing checkpoint file")
    output.mkdir()
    snapshot = output / "checkpoint.sqlite"
    # SQLite's backup API captures committed WAL contents consistently.
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(snapshot)) as destination:
            origin.backup(destination)
            mode = destination.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if mode.lower() != "delete":
                raise ValueError("snapshot is not self-contained")
            metadata = inspect(destination)
    if any(output.glob("checkpoint.sqlite-*")):
        raise ValueError("snapshot still has SQLite sidecars")
    snapshot_sha256 = file_digest(snapshot)
    # Open a second copy without any WAL access to prove independent recovery.
    replay = output / "recovery-check.sqlite"
    shutil.copyfile(snapshot, replay)
    with closing(sqlite3.connect(replay.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as restored:
        recovered = inspect(restored)
    if recovered != metadata or file_digest(replay) != snapshot_sha256:
        raise ValueError("independent recovery differs from snapshot")
    replay.unlink()
    result = {"scope": "committed SQLite snapshot; not a sampling or diagnostic pass",
              "source": str(source), "snapshot": snapshot.name, "sha256": snapshot_sha256,
              "tool_sha256": file_digest(Path(__file__).resolve()),
              "python": sys.version, "sqlite": sqlite3.sqlite_version,
              "recovery_verified_without_wal": True, **metadata}
    with (output / "receipt.json").open("x") as file:
        json.dump(result, file, indent=2, allow_nan=False)
        file.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(backup(args.source, args.output), allow_nan=False))
