"""Per-chain transactional checkpoints. Array bytes and metadata are checksummed."""
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import json
import sqlite3

import numpy as np


def digest(data):
    return sha256(data).hexdigest()


def pack(record):
    stream = BytesIO()
    np.savez(stream, **record)
    return stream.getvalue()


def unpack(blob, expected):
    if digest(blob) != expected:
        raise ValueError("checkpoint checksum mismatch")
    with np.load(BytesIO(blob), allow_pickle=False) as data:
        return dict(data)


class Checkpoint:
    def __init__(self, path, identity):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS identity (singleton INTEGER PRIMARY KEY CHECK(singleton=1), value TEXT NOT NULL)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS blocks
            (last_step INTEGER PRIMARY KEY, first_step INTEGER NOT NULL,
             payload BLOB NOT NULL, checksum TEXT NOT NULL)""")
        expected = json.dumps(identity, sort_keys=True)
        with self.transaction():
            self.db.execute("INSERT OR IGNORE INTO identity VALUES (1, ?)", (expected,))
            if self.db.execute("SELECT value FROM identity").fetchone() != (expected,):
                raise ValueError("checkpoint chain or environment identity mismatch")

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def blocks(self):
        previous = -1
        for last, first, blob, checksum in self.db.execute(
                "SELECT last_step, first_step, payload, checksum FROM blocks ORDER BY last_step"):
            if first != previous + 1 or last < first or (last > 0 and last-first != 99):
                raise ValueError("checkpoint step sequence mismatch")
            yield last, unpack(blob, checksum)
            previous = last

    def append(self, first, last, record):
        blob = pack(record)
        self.db.execute("INSERT INTO blocks VALUES (?, ?, ?, ?)", (last, first, blob, digest(blob)))
