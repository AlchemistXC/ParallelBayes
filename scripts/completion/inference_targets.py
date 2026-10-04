"""Device-explicit reconstruction of declared F3 targets and frozen geometry.

Research interface, not an arbitrary Stan/CUDA compiler. Historical CPU-only
builders remain unchanged so already frozen experiments keep their identity.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'), str(ROOT/'examples')]


def build_target(item, source, device):
    """Return a torch Model on the requested device, or fail without fallback."""
    if device not in ('cpu', 'cuda', 'cuda:0'):
        raise ValueError('An explicit cpu/cuda device is required')
    if item['name'] == 'W1':
        from external_wells import load_wells, make_wells, propriety_certificate
        data = load_wells(source)
        if not propriety_certificate(data)['certified']:
            raise ValueError('W1 integrability certificate unavailable')
        base = make_wells(data, 'torch', device)
    else:
        from parallelbayes.torch_backend.models import make_model
        specs = json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())['models']
        if item['name'] not in specs:
            raise ValueError('Unknown declared target')
        base = make_model(specs[item['name']], device)
    if base.target_id != item['base_target_id'] or base.dimension != item['dimension']:
        raise ValueError('Frozen base target identity differs')
    g = item['geometry']
    if 'target_id' in g and g['target_id'] != base.target_id:
        raise ValueError('Frozen geometry identity differs')
    from affine_target import affine_model
    return affine_model(base, g['center'], g['factor'])
