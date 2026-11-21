from pathlib import Path
import sqlite3
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_reference"))
from checkpoint import Checkpoint
from portable_backup import backup, inspect


def test_backup_includes_live_wal_and_recovers_without_sidecars(tmp_path):
    source = tmp_path / "source.sqlite"
    chain = Checkpoint(source, {"scope": "synthetic", "chain": 1})
    with chain.transaction():
        chain.append(0, 0, {"state": np.array([3.])})
        chain.append(1, 100, {"draws": np.arange(100)})
    wal = tmp_path / "source.sqlite-wal"
    assert wal.stat().st_size > 0
    result = backup(source, tmp_path / "out")
    assert result["blocks"] == 2 and result["last_step"] == 100
    assert result["recovery_verified_without_wal"]
    snapshot = tmp_path / "out/checkpoint.sqlite"
    assert sorted(p.name for p in snapshot.parent.iterdir()) == ["checkpoint.sqlite", "receipt.json"]
    with sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as restored:
        assert inspect(restored)["identity"]["chain"] == 1
    with pytest.raises(FileExistsError):
        backup(source, tmp_path / "out")
    chain.db.close()


def test_corrupt_payload_is_rejected(tmp_path):
    source = tmp_path / "source.sqlite"
    chain = Checkpoint(source, {"scope": "synthetic", "chain": 1})
    with chain.transaction():
        chain.append(0, 0, {"state": np.array([3.])})
        chain.db.execute("UPDATE blocks SET checksum = ?", ("0" * 64,))
    with pytest.raises(ValueError, match="payload checksum mismatch"):
        backup(source, tmp_path / "bad")
    assert not (tmp_path / "bad/receipt.json").exists()
    chain.db.close()
