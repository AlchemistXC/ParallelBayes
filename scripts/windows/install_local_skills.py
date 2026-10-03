"""Install the separately transferred private skill archive without overwriting skills.

Only standard-library modules are used. No skill scripts or hooks are executed.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import shutil
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or ':' in name
            or any(p in {'', '.', '..'} or p.endswith(('.', ' ')) for p in name.split('/'))):
        raise ValueError('Unsafe skill path')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    if any(p.split('.')[0].upper() in reserved for p in path.parts):
        raise ValueError('Reserved Windows path')
    return path


def existing_matches(directory, rows):
    if directory.is_symlink() or not directory.is_dir():
        return False
    expected = {PurePosixPath(r['path']).relative_to(directory.name).as_posix(): r for r in rows}
    actual = {p.relative_to(directory).as_posix(): p for p in directory.rglob('*') if p.is_file()}
    if set(actual) != set(expected) or any(p.is_symlink() for p in directory.rglob('*')):
        return False
    return all(p.stat().st_size == expected[n]['bytes'] and sha(p.read_bytes()) == expected[n]['sha256']
               for n, p in actual.items())


def install(archive, expected_sha, destination):
    archive, destination = Path(archive), Path(destination)
    if sha(archive.read_bytes()) != expected_sha:
        raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        names = [item.filename for item in z.infolist()]
        if len({n.casefold() for n in names}) != len(names):
            raise ValueError('Duplicate or case-colliding archive paths')
        for item in z.infolist():
            safe_path(item.filename)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Symlink entries are not accepted')
        manifest = json.loads(z.read('MANIFEST.json'))
        rows = manifest['files']
        folders = [r['folder'] for r in manifest['skills']]
        if len(set(folders)) != len(folders) or any(not re.fullmatch('[a-z0-9][a-z0-9-]*', f) for f in folders):
            raise ValueError('Invalid skill folders')
        if len({r['path'] for r in rows}) != len(rows):
            raise ValueError('Duplicate manifest paths')
        if set(names) != {'MANIFEST.json'} | {'skills/' + r['path'] for r in rows}:
            raise ValueError('Archive and manifest differ')
        grouped = {folder: [] for folder in folders}
        for row in rows:
            path = safe_path(row['path'])
            if len(path.parts) < 2 or path.parts[0] not in grouped:
                raise ValueError('File is outside a declared skill')
            data = z.read('skills/' + row['path'])
            if len(data) != row['bytes'] or sha(data) != row['sha256']:
                raise ValueError('Skill file checksum mismatch: ' + row['path'])
            grouped[path.parts[0]].append(row)
        for folder in folders:
            if folder + '/SKILL.md' not in {r['path'] for r in grouped[folder]}:
                raise ValueError('Missing SKILL.md: ' + folder)
        # Resolve all conflicts before creating or copying any skill.
        skipped, pending = [], []
        for folder in folders:
            target = destination / folder
            if target.exists() or target.is_symlink():
                if not existing_matches(target, grouped[folder]):
                    raise FileExistsError('Preserve existing different skill: ' + str(target))
                skipped.append(folder)
            else:
                pending.append(folder)
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='pb-skill-install-') as temporary:
            stage = Path(temporary)
            for folder in pending:
                for row in grouped[folder]:
                    target = stage / row['path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read('skills/' + row['path']))
            for folder in pending:
                shutil.copytree(stage / folder, destination / folder, dirs_exist_ok=False)
    return {'installed': pending, 'already_identical': skipped,
            'destination': str(destination), 'skill_scripts_executed': False,
            'next': 'Check discovery on the next turn; restart Codex if needed. Windows runtime compatibility remains to be checked.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=ROOT / 'handoff/windows-native/skills-inventory.json')
    parser.add_argument('--dest', type=Path, default=Path.home() / '.agents/skills')
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
    print(json.dumps(install(args.archive, inventory['archive_sha256'], args.dest), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
