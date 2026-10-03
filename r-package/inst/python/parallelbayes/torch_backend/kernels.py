"""Fixed actual randomness MH maps, strict finite flags and hard-forward JVP."""
import math
import torch


def transition(logp, kernel):
    if kernel not in ("mala", "rwm"):
        raise ValueError("unsupported MH kernel")
    grad = torch.func.grad(logp)

    def step(q, z, logu, scale, surrogate=False):
        lp = logp(q)
        if kernel == "mala":
            g = grad(q)
            proposal = q + scale*g + math.sqrt(2*scale)*z
            lp2, g2 = logp(proposal), grad(proposal)
            reverse, forward = q-proposal-scale*g2, proposal-q-scale*g
            ratio = lp2-lp-(reverse.square().sum()-forward.square().sum())/(4*scale)
            finite = torch.isfinite(g).all() & torch.isfinite(g2).all()
        else:
            proposal = q + scale*z
            lp2 = logp(proposal)
            ratio = lp2-lp
            finite = torch.ones((),dtype=torch.bool,device=q.device)
        finite = finite & torch.isfinite(lp) & torch.isfinite(lp2) & torch.isfinite(proposal).all() & torch.isfinite(ratio)
        accept = (logu < ratio) & finite
        hard = torch.where(accept,proposal,q)
        if surrogate:
            smooth = torch.sigmoid(ratio-logu)
            gate = accept.to(q.dtype).detach() + (smooth-smooth.detach())
            soft = q + gate*(proposal-q)
            # Parentheses preserve bitwise hard forward even at extreme magnitudes.
            out = hard.detach() + (soft-soft.detach())
        else:
            out = hard
        return out, accept, finite
    return step
