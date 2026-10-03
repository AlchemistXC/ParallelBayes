import argparse,json
from pathlib import Path
import xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--require-pilot',action='store_true');a=p.parse_args()
device=json.loads(Path('execution/gpu/device-check.json').read_text())
if not device['passed']:raise SystemExit('GPU device gate failed')
from parallelbayes.experiment import source_hash,file_hash,check_installed_lock
check_installed_lock('environment/locks/gpu-candidate.txt')
check_installed_lock('environment/locks/python-runtime-transitive.txt')
receipt=json.loads(Path('execution/gpu/correctness-receipt.json').read_text())
if receipt['source_sha256']!=source_hash('.') or receipt['test_sha256']!=file_hash('execution/gpu/pytest.xml'):
 raise SystemExit('Correctness evidence is stale or changed')
root=ET.parse('execution/gpu/pytest.xml').getroot()
suites=[root] if root.tag=='testsuite' else root.findall('testsuite')
if not suites or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise SystemExit('Correctness tests did not pass')
executed=sum(int(s.get('tests',0))-int(s.get('skipped',0)) for s in suites)
if executed<40:raise SystemExit('Expected at least 40 executed non-Stan correctness tests')
if a.require_pilot:
 registry=json.loads(Path('benchmark/runs/gpu-pilot-v4/registry.json').read_text())
 from parallelbayes.experiment import load_protocol
 pilot=load_protocol('benchmark/protocols/pilot-v4.json','.')
 if registry['identity'] != dict(protocol_sha256=pilot['protocol_sha256'],source_sha256=pilot['source_sha256'],platform='gpu') or len(registry['tasks'])!=len(pilot['tasks']):
  raise SystemExit('Pilot evidence has wrong identity or task count')
 if any(t['status'] in ['pending','running'] for t in registry['tasks']):raise SystemExit('Pilot is incomplete')
 if any(t['status']=='failed' for t in registry['tasks']):raise SystemExit('Pilot failures require diagnosis and a documented protocol decision before formal runs')
 stats=Path('execution/gpu/statistical-v4/summary.json')
 if not stats.exists():raise SystemExit('Statistical stage is incomplete')
 summary=json.loads(stats.read_text())
 if any(x['failed'] for x in summary['methods']):raise SystemExit('Statistical fit failures require diagnosis before formal runs')
 import importlib.util
 spec=importlib.util.spec_from_file_location('sbc_evidence','scripts/verify-statistical-evidence.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.verify('execution/gpu/statistical-v4','benchmark/protocols/statistical-v4.json','gpu',True)
print('GPU evidence gate passed')
