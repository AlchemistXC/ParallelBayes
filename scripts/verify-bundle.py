from pathlib import Path
import hashlib
manifest=Path('SHA256SUMS')
if not manifest.exists():raise SystemExit('SHA256SUMS missing')
count=0
for line in manifest.read_text().splitlines():
 digest,name=line.split('  ',1);p=Path(name)
 if p.is_absolute() or '..' in p.parts:raise SystemExit('Unsafe checksum path')
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit(f'Checksum mismatch: {name}')
 count+=1
print(f'Validated {count} bundle files')
