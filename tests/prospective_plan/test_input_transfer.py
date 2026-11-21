"""Round-trip and corruption tests for candidate transfer."""
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_plan"))
sys.path.insert(0, str(ROOT/"scripts/prospective_reference"))
from input_transfer import pack, unpack, verify
from prepare_inputs import generate


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        generate(root/"input")
        pack(root/"input", root/"first.zip")
        pack(root/"input", root/"second.zip")
        first, second = (root/"first.zip").read_bytes(), (root/"second.zip").read_bytes()
        assert first == second
        checksum = hashlib.sha256(first).hexdigest()
        verify(root/"first.zip", checksum)
        unpack(root/"first.zip", checksum, root/"received")
        for item in ("manifest.json", "data.npz", "initials.npz"):
            assert (root/"received"/item).read_bytes() == (root/"input"/item).read_bytes()
        try:
            unpack(root/"first.zip", checksum, root/"received")
        except FileExistsError:
            pass
        else:
            raise AssertionError("unpack overwrote existing destination")
        (root/"corrupt.zip").write_bytes(first[:-1] + bytes([first[-1]^1]))
        try:
            verify(root/"corrupt.zip", checksum)
        except ValueError:
            pass
        else:
            raise AssertionError("corrupt bundle accepted")
    print("candidate transfer deterministic, corrupt input refused, overwrite refused")


if __name__ == "__main__":
    main()
