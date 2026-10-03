"""Record local skill files without copying private code into project outputs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HOME=Path.home()
inventory=json.loads((ROOT/'handoff/windows-native/skills-inventory.json').read_text(encoding='utf-8'))
archive=ROOT/'downloads'/inventory['archive_name']
records=[]
for row in inventory['skills']:
    locations=[p for p in (HOME/'.agents/skills'/row['folder'],HOME/'.codex/skills'/row['folder']) if p.exists()]
    records.append(dict(name=row['declared_name'],folder=row['folder'],source='private Mac transfer',
        expected_archive_sha256=inventory['archive_sha256'],installed_paths=[str(p) for p in locations],
        file_installation='absent' if not locations else 'present_not_hash_verified',
        discovery='not_in_current_session_catalog',runtime_validation='not_run_missing_archive',
        portability_markers=row['portability_review_markers'],dependencies='inspect private skill before use',
        manual_connection=None,platform_limitations='not_yet_reviewed'))
plugins=[]
mapping={'data-analytics':'openai-curated-remote','pdf':'openai-primary-runtime','documents':'openai-primary-runtime',
    'presentations':'openai-primary-runtime','spreadsheets':'openai-primary-runtime','google-drive':'openai-curated-remote',
    'pages':'openai-curated-remote','sites':'openai-curated-remote','visualize':'openai-bundled',
    'work-pets':'openai-curated-remote','plugin-management':'openai-curated-remote','computer-use':'openai-bundled'}
for name,group in mapping.items():
    base=HOME/'.codex/plugins/cache'/group/name
    skills=list(base.rglob('SKILL.md')) if base.exists() else []
    plugins.append(dict(name=name,source=group,files_present=bool(skills),discovery='provided_in_session_catalog',
        skill_metadata=[dict(path=str(s),sha256=hashlib.sha256(s.read_bytes()).hexdigest()) for s in skills],
        tool_validation='directory_search_passed' if name=='plugin-management' else 'not_exercised',
        manual_connection='Account-dependent cloud services not probed; no credentials migrated' if name in ('google-drive','pages','sites','work-pets') else None,
        platform_limitations='macOS native app automation is not migrated; current native APIs disabled' if name=='computer-use' else None))
plugins.append(dict(name='LaTeX',discovery='plugin directory search returned no matches',
    files_present=False,tool_validation='not_run',manual_connection=None,
    platform_limitations='Built-in single-file editor available; multi-file manuscript compilation not verified'))
systems=[]
for name in ('skill-installer','skill-creator','openai-docs','imagegen'):
    p=HOME/'.codex/skills/.system'/name/'SKILL.md'
    systems.append(dict(name=name,path=str(p),file_installation=p.exists(),discovery='provided_in_session_catalog',
        sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
        runtime_validation='instructions_read' if name=='skill-installer' else 'not_exercised'))
out=dict(date='2026-10-04',archive=str(archive),archive_present=archive.exists(),
    installation_destination=str(HOME/'.agents/skills'),user_skills=records,system_skills=systems,plugins=plugins,
    next_turn='After archive installation confirm discovery in a later turn; restart Codex only if missing.',
    privacy='No skill text, credentials, Mac binaries or plugin caches are copied into this repository.')
(ROOT/'execution/windows-native/skills-status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(records)} private skills inventoried; archive present={archive.exists()}; {len(plugins)} plugin groups recorded')
