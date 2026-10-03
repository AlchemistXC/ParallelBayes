"""Public research interface. Import sets the explicit fp64 computation policy."""
import os
os.environ.setdefault("JAX_ENABLE_X64", "true")
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
import jax
jax.config.update("jax_enable_x64", True)
__version__ = "0.1.1"

from .models import make_model
from .sampling import sample, capabilities, validate_model

