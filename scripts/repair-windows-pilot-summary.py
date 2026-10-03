"""Clarify pilot accuracy aggregation without changing any frozen formal source.

The pilot repeats a tape across chain/window configurations, so the generic
analyzer's configuration-pooled accuracy bootstrap is not an inferential interval.
Keep its original output, then label the descriptive estimand and remove those
intervals. Paired per-configuration timing summaries (one tape each) are unchanged.
"""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'execution/windows-native/pilot-analysis'
source=root/'summary.json';original=root/'summary.original.json'
if not original.exists():original.write_bytes(source.read_bytes())
data=json.loads(original.read_text(encoding='utf-8'))
for row in data['accuracy']:
    if 'function_mse' in row:row['descriptive_mse_across_pilot_configurations']=row.pop('function_mse')
    row.pop('function_mse_ci95',None)
    row['inference_status']='not_assessed: same tape across different chain/window configurations'
data['pilot_accuracy_correction']=dict(original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    reason='Configuration variation is not independent sampling replication. Formal groups have four distinct tapes and are unaffected.')
source.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Pilot configuration-pooled accuracy intervals removed; original output retained.')
