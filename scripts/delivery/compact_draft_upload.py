"""Append exact SHA-bound assets to the existing Windows draft. Never replace/publish.

This is a delivery-only tool, not part of the accepted sampling source. It can
upload one bounded block and its receipt at a time; no full archive is created.
Git credentials stay in memory and are never returned or written to evidence.
"""
import argparse
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, urlsplit

REPO = 'AlchemistXC/ParallelBayes'
RELEASE_ID = 403644544
TAG = 'windows-completion-v2-20261005'
API = 'https://api.github.com/repos/' + REPO
COPY_BUFFER = 1024**2


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(COPY_BUFFER), b''):
            h.update(block)
    return h.hexdigest()


def existing_credential():
    result = subprocess.run(['git', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\npath=' + REPO + '.git\n\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never'))
    if result.returncode:
        raise RuntimeError('Existing authorized Git credential helper unavailable')
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    token = fields.get('password')
    if not token:
        raise RuntimeError('Existing authorized Git credential unavailable')
    return token


def validate_endpoint(method, url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.fragment
        or parsed.port not in (None, 443)):
        raise ValueError('HTTPS GitHub endpoint required')
    if method == 'GET':
        allowed = parsed.hostname == 'api.github.com' and parsed.path in (
            f'/repos/{REPO}/releases/{RELEASE_ID}',
            f'/repos/{REPO}/releases/{RELEASE_ID}/assets')
    elif method == 'POST':
        allowed = (parsed.hostname == 'uploads.github.com'
            and parsed.path == f'/repos/{REPO}/releases/{RELEASE_ID}/assets')
    else:
        allowed = False
    if not allowed:
        raise ValueError('Only reading and appending to the existing Windows draft is permitted')
    return parsed


def authenticated_request(token):
    def request(method, url, path=None):
        parsed = validate_endpoint(method, url)
        if (method == 'POST') != (path is not None):
            raise ValueError('Only asset append requests carry a file body')
        headers = {'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + token, 'User-Agent': 'ParallelBayes-compact-return',
            'X-GitHub-Api-Version': '2026-03-10'}
        connection = http.client.HTTPSConnection(parsed.hostname, timeout=45)
        target = parsed.path + ('?' + parsed.query if parsed.query else '')
        try:
            if path is None:
                connection.request(method, target, headers=headers)
            else:
                path = Path(path)
                headers.update({'Content-Type': 'application/octet-stream',
                    'Content-Length': str(path.stat().st_size)})
                connection.putrequest(method, target)
                for key, value in headers.items():
                    connection.putheader(key, value)
                connection.endheaders()
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(COPY_BUFFER), b''):
                        connection.send(block)
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                # Do not print response text or request headers/credentials.
                raise RuntimeError('GitHub HTTP ' + str(response.status) + ' at authorized asset endpoint')
            return json.loads(response.read())
        finally:
            connection.close()
    return request


def asset_record(asset):
    return {k: asset.get(k) for k in ('id', 'name', 'size', 'state', 'digest')}


def release_identity(value):
    if value['id'] != RELEASE_ID or value['tag_name'] != TAG or value['draft'] is not True:
        raise ValueError('Existing unchanged draft required; do not publish or create a replacement')
    return {k: value[k] for k in ('id', 'tag_name', 'draft', 'target_commitish')}


def list_assets(request):
    assets = []
    page = 1
    while True:
        values = request('GET', API + f'/releases/{RELEASE_ID}/assets?per_page=100&page={page}')
        if not isinstance(values, list) or len(values) > 100:
            raise ValueError('Invalid asset page')
        assets.extend(values)
        if len({a['id'] for a in assets}) != len(assets):
            raise ValueError('Duplicate asset/page; refuse ambiguous remote inventory')
        if len({a['name'].casefold() for a in assets}) != len(assets):
            raise ValueError('Duplicate/aliased asset name')
        if len(values) < 100:
            return assets
        page += 1


def atomic_receipt(path, value):
    path = Path(path)
    partial = path.with_name(path.name + '.writing')
    with partial.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    partial.replace(path)


def upload(plan, plan_sha256, output, *, request=None):
    plan = Path(plan).resolve()
    output = Path(output).resolve()
    if sha(plan) != plan_sha256:
        raise ValueError('Explicit local upload plan SHA differs')
    value = json.loads(plan.read_text(encoding='utf-8'))
    if value.get('schema') != 'compact-draft-assets-v1' or not value['assets']:
        raise ValueError('Explicit nonempty compact draft asset plan required')
    if output.exists():
        raise FileExistsError('Old upload receipt is immutable; use a new receipt path')
    seen = set()
    paths = []
    for item in value['assets']:
        name = item['name']
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name)
            or name.casefold() in seen):
            raise ValueError('Canonical unique asset names required')
        seen.add(name.casefold())
        path = Path(item['path']).resolve()
        if (type(item['bytes']) is not int or not 0 <= item['bytes'] <= 1024**3 or not path.is_file()
            or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']):
            raise ValueError('Local asset size/SHA differs; no network writes')
        paths.append((item, path))
    if request is None:
        request = authenticated_request(existing_credential())
    release = request('GET', API + f'/releases/{RELEASE_ID}')
    baseline = release_identity(release)
    before = list_assets(request)
    receipt = dict(schema='compact-draft-upload-receipt-v1', plan_sha256=plan_sha256,
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        release=baseline, release_url=release['html_url'], previous_assets=[asset_record(a) for a in before],
        appended_or_reused=[], status='in_progress', credentials_persisted=False,
        publish_calls=0, overwrite_calls=0, maximum_copy_buffer_bytes=COPY_BUFFER)
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_receipt(output, receipt)
    try:
        for item, path in paths:
            if release_identity(request('GET', API + f'/releases/{RELEASE_ID}')) != baseline:
                raise ValueError('Draft identity changed during upload')
            current = list_assets(request)
            matches = [a for a in current if a['name'].casefold() == item['name'].casefold()]
            if matches:
                asset = matches[0]
                if asset['name'] != item['name']:
                    raise ValueError('Remote case-alias refused before upload')
                reused = True
            else:
                # Recheck cached bytes immediately before append.
                if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
                    raise ValueError('Local asset changed before upload')
                url = release['upload_url'].split('{', 1)[0] + '?name=' + quote(item['name'], safe='')
                asset = request('POST', url, path)
                reused = False
            if (asset['size'] != item['bytes'] or asset['state'] != 'uploaded'
                or asset.get('digest') != 'sha256:' + item['sha256']):
                raise ValueError('Existing/uploaded remote asset differs; never replace it')
            receipt['appended_or_reused'].append(dict(asset_record(asset), reused=reused))
            atomic_receipt(output, receipt)
        after = list_assets(request)
        by_id = {a['id']: asset_record(a) for a in after}
        if any(by_id.get(a['id']) != asset_record(a) for a in before):
            raise ValueError('A previous remote asset changed')
        by_name = {a['name']: a for a in after}
        for item, _ in paths:
            asset = by_name[item['name']]
            if (asset['size'] != item['bytes'] or asset['state'] != 'uploaded'
                or asset.get('digest') != 'sha256:' + item['sha256']):
                raise ValueError('Final remote asset SHA differs')
        if release_identity(request('GET', API + f'/releases/{RELEASE_ID}')) != baseline:
            raise ValueError('Final draft identity changed')
        receipt.update(status='verified_additive_upload', previous_assets_unchanged=True,
            final_draft=True, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:
        receipt.update(status='failed_originals_preserved', error=type(error).__name__ + ': ' + str(error))
        atomic_receipt(output, receipt)
        raise
    atomic_receipt(output, receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    result = upload(**vars(parser.parse_args()))
    print(json.dumps(dict(status=result['status'], assets=len(result['appended_or_reused']),
        draft=result['final_draft'], previous_assets_unchanged=result['previous_assets_unchanged'])))
