"""Final representability gate shared by all sampling providers."""
import numpy as np


def constrain_checked(model, path):
    try:
        with np.errstate(over='raise', invalid='raise', under='ignore'):
            theta=np.asarray(model.constrain(path), dtype=float)
        if theta.shape != path.shape[:-1]+(len(model.names),):
            raise ValueError('constrained output shape differs from parameter names')
        if not np.isfinite(theta).all():
            raise FloatingPointError('nonfinite constrained output')
        if model.spec['kind']=='lognormal' and not np.all(theta>0):
            raise FloatingPointError('positive output underflowed outside the open support')
        if model.backend=='bridgestan':
            # Stan owns its constraint semantics. An invalid or rounded-to-boundary
            # transform must not silently become an ordinary posterior object.
            for row in theta.reshape(-1,len(model.names)):
                back=model.stan.param_unconstrain(np.ascontiguousarray(row))
                if not np.isfinite(back).all():
                    raise FloatingPointError('Stan constrained output is not representable in its open support')
        return theta, None
    except (ValueError, RuntimeError, FloatingPointError, OverflowError) as exc:
        return None, f'{type(exc).__name__}: {exc}'
