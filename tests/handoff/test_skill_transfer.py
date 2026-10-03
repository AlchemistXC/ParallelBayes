"""Private archive integrity and non-overwrite behavior, independent of Codex discovery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('skill_install', ROOT / 'scripts/windows/install_local_skills.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def archive_fixture(tmp_path, unsafe=False):
    files = {'a-skill/SKILL.md': b'---\nname: a-skill\ndescription: example\n---\n',
             'a-skill/scripts/example.py': b'raise RuntimeError("must never execute")\n',
             'b-skill/SKILL.md': b'---\nname: b-skill\ndescription: example\n---\n'}
    if unsafe:
        files['a-skill/../../escaped'] = b'invalid'
    rows = [{'path': n, 'bytes': len(b), 'sha256': installer.sha(b)} for n, b in files.items()]
    manifest = {'skills': [{'folder': 'a-skill'}, {'folder': 'b-skill'}], 'files': rows}
    archive = tmp_path / 'skills.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('MANIFEST.json', json.dumps(manifest))
        for n, b in files.items():
            z.writestr('skills/' + n, b)
    return archive, installer.sha(archive.read_bytes()), files


def test_full_copy_is_exact_and_idempotent_without_executing_scripts(tmp_path):
    archive, digest, files = archive_fixture(tmp_path)
    dest = tmp_path / 'destination'
    first = installer.install(archive, digest, dest)
    assert first['installed'] == ['a-skill', 'b-skill']
    assert first['skill_scripts_executed'] is False
    for name, data in files.items():
        assert (dest / name).read_bytes() == data
    again = installer.install(archive, digest, dest)
    assert again['installed'] == [] and again['already_identical'] == ['a-skill', 'b-skill']


def test_any_conflict_is_found_before_other_skills_are_copied(tmp_path):
    archive, digest, _ = archive_fixture(tmp_path)
    dest = tmp_path / 'destination'
    (dest / 'b-skill').mkdir(parents=True)
    (dest / 'b-skill/SKILL.md').write_text('User custom version')
    with pytest.raises(FileExistsError):
        installer.install(archive, digest, dest)
    assert not (dest / 'a-skill').exists()
    assert (dest / 'b-skill/SKILL.md').read_text() == 'User custom version'


def test_corrupt_archive_does_not_create_destination(tmp_path):
    archive, digest, _ = archive_fixture(tmp_path)
    archive.write_bytes(archive.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='checksum'):
        installer.install(archive, digest, tmp_path / 'destination')
    assert not (tmp_path / 'destination').exists()


def test_traversal_archive_rejected_before_install(tmp_path):
    archive, digest, _ = archive_fixture(tmp_path, unsafe=True)
    with pytest.raises(ValueError, match='Unsafe'):
        installer.install(archive, digest, tmp_path / 'destination')
    assert not (tmp_path / 'destination').exists()


@pytest.mark.parametrize('name', ['C:/x', '../x', 'a\\b', 'a/CON.py', 'a/n.'])
def test_windows_unsafe_paths_rejected(name):
    with pytest.raises(ValueError):
        installer.safe_path(name)
