from parallelbayes.experiment import write_json,source_hash,file_hash
from parallelbayes.sampling import environment
write_json('execution/gpu/correctness-receipt.json',dict(source_sha256=source_hash('.'),
 test_sha256=file_hash('execution/gpu/pytest.xml'),environment=environment()))
