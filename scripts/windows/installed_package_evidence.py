"""Run only through -I in the new installed environment from outside Git."""
import importlib.util,json,sys
from pathlib import Path
import parallelbayes
from parallelbayes.torch_backend.sampling import environment
output=Path(sys.argv[1]);root=Path(parallelbayes.__file__).resolve()
assert 'site-packages' in str(root).lower(),root
assert parallelbayes.__version__=='0.2.0.dev2'
assert importlib.util.find_spec('jax') is None
record=dict(package_file=str(root),version=parallelbayes.__version__,python=sys.version,
    executable=sys.executable,prefix=sys.prefix,sys_path=sys.path,JAX_available=False,
    environment=environment(),installed_noneditable=True)
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
