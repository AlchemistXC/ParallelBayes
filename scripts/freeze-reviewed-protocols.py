"""Freeze unchanged experiment designs against the reviewed candidate source."""
from pathlib import Path
import argparse,json
from parallelbayes.experiment import freeze,file_hash
p=argparse.ArgumentParser();p.add_argument('--source-root',default='.');a=p.parse_args();root=Path(a.source_root)
for original,new in [('protocol-v1','protocol-v3'),('pilot-v2','pilot-v4'),('reference-v1','reference-v3')]:
 old=json.loads(Path(f'benchmark/protocols/{original}.json').read_text())
 for k in ['source_sha256','runtime_lock_sha256','protocol_sha256','frozen_at']:old.pop(k,None)
 old.update(name=new,parent_protocol=original,revision_reason='Reviewed release 0.1.1 output/record/resume repairs; partial-window mask. Formal lengths are exact multiples of 64; no task, seed, estimand or threshold selection.')
 freeze(f'benchmark/protocols/{new}.json',old,root)
freeze('benchmark/protocols/statistical-v4.json',dict(name='statistical-v4',replicates=64,platforms=['cpu','gpu'],seed=551103,sampling_seed=173000,
 script='scripts/statistical-validation.py',script_sha256=file_hash('scripts/statistical-validation.py'),
 scope='Same 64 planned fresh datasets as unexecuted v2; retain all diagnostics including finite NUTS divergences',
 parent_protocol='statistical-v2',revision_reason='Review-driven diagnostic preservation and software boundary repairs; v2 and v3 were never executed; final R scalar-array bridge correction validated'),root)
print('Reviewed GPU and SBC protocols frozen against',root)
