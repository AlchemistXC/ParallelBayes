"""Read archived Windows evidence without rewriting its integrity records."""
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/followups'))
from nuts_events import atomic_json, sha
from nuts_runtime import seal, verify


def windows_fixture(root):
    (root / 'chain-0').mkdir(parents=True)
    (root / 'chain-0' / 'evidence.txt').write_text('saved state\n')
    outcome = seal(root, dict(status='completed', managed_active_processes=0,
                             kernel_terminal_verified=True,
                             posterior_samples_eligible=False))
    manifest = root / 'checksums.json'
    hashes = json.loads(manifest.read_text())
    atomic_json(manifest, {name.replace('/', '\\'): value for name, value in hashes.items()})
    outcome['checksums_sha256'] = sha(manifest)
    return outcome


def test_archived_windows_manifest_is_read_only_and_still_detects_tamper(tmp_path):
    outcome = windows_fixture(tmp_path)
    before = {p.relative_to(tmp_path).as_posix(): sha(p)
              for p in tmp_path.rglob('*') if p.is_file()}
    assert verify(tmp_path, outcome) == 2
    assert {p.relative_to(tmp_path).as_posix(): sha(p)
            for p in tmp_path.rglob('*') if p.is_file()} == before
    (tmp_path / 'chain-0' / 'evidence.txt').write_text('changed state\n')
    with pytest.raises(ValueError, match='Call asset differs'):
        verify(tmp_path, outcome)


@pytest.mark.parametrize('alias', ['chain-0/evidence.txt', '../outside.txt',
                                  '..\\outside.txt', 'C:\\outside.txt',
                                  '/outside.txt'])
def test_manifest_rejects_ambiguous_or_escaping_paths(tmp_path, alias):
    outcome = windows_fixture(tmp_path)
    manifest = tmp_path / 'checksums.json'
    hashes = json.loads(manifest.read_text())
    hashes[alias] = hashes['chain-0\\evidence.txt']
    atomic_json(manifest, hashes)
    outcome['checksums_sha256'] = sha(manifest)
    with pytest.raises(ValueError, match='Duplicate portable path|Unsafe relative path'):
        verify(tmp_path, outcome)


def test_prepared_input_manifest_uses_same_legacy_path_rules(tmp_path):
    from run_nuts_localization import verify_files
    folder = tmp_path / 'inputs'
    folder.mkdir()
    source = folder / 'case.json'
    source.write_text('{"fixed": true}\n')
    hashes = {'inputs\\case.json': sha(source)}
    verify_files(tmp_path, hashes)
    source.write_text('{"fixed": false}\n')
    with pytest.raises(ValueError, match='checksum differs'):
        verify_files(tmp_path, hashes)
