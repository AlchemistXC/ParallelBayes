"""Optional numerical providers; importing NumPy or torch never imports JAX."""
import os
os.environ.setdefault("JAX_ENABLE_X64", "true")
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
__version__ = "0.2.0.dev2"

def make_model(spec, backend="jax", device="cpu"):
    if backend == "torch":
        from .torch_backend.models import make_model as factory
        return factory(spec, device)
    if backend == "numpy":
        from .reference import make_reference
        return make_reference(spec)
    if backend != "jax":
        raise ValueError("unknown numerical provider")
    from .models import make_model as factory
    return factory(spec)


def sample(spec, config=None, tape=None, backend="jax"):
    if backend == "torch" or getattr(spec, "backend", None) == "torch":
        from .torch_backend.sampling import sample as run
    elif backend == "jax":
        from .sampling import sample as run
    else:
        raise ValueError("unknown numerical provider")
    return run(spec, config, tape)


def capabilities(spec=None, backend="jax"):
    if backend == "torch":
        from .torch_backend.sampling import capabilities as query
    elif backend == "jax":
        from .sampling import capabilities as query
    else:
        raise ValueError("unknown numerical provider")
    return query(spec)


def validate_model(spec, points=None, backend="jax"):
    if backend == "torch" or getattr(spec, "backend", None) == "torch":
        from .torch_backend.models import validate_model as validate
    elif backend == "jax":
        from .sampling import validate_model as validate
    else:
        raise ValueError("unknown numerical provider")
    return validate(spec, points)

