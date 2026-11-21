"""Development-only first-use cost accounting and conservative window selection.

The caller must supply independently developed simultaneous prediction-bound
calibration. This module cannot establish that calibration's coverage and is not
an executable first-use sampling workflow.
"""
import math

WINDOWS = (4, 8, 16, 32, 64)
THRESHOLD = 1.10
DISCARD = 512


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return float(value)


def baseline(retained, shared_seconds, sequential_setup_seconds, sequential_step_seconds,
             delivery_fixed_seconds, delivery_per_step_seconds):
    if type(retained) is not int or retained not in (256, 1024, 4096, 16384):
        raise ValueError("retained steps must be a planned budget")
    shared = number(shared_seconds, "shared_seconds")
    setup = number(sequential_setup_seconds, "sequential_setup_seconds")
    cost = number(sequential_step_seconds, "sequential_step_seconds", positive=True)
    delivery_fixed = number(delivery_fixed_seconds, "delivery_fixed_seconds")
    delivery_per_step = number(delivery_per_step_seconds, "delivery_per_step_seconds")
    return number(shared+setup+(DISCARD+retained)*cost+delivery_fixed+retained*delivery_per_step,
                  "baseline total",positive=True)


def decide(*, retained, shared_seconds, sequential_setup_seconds, sequential_step_seconds,
           delivery_fixed_seconds, delivery_per_step_seconds, probe_seconds, candidates,
           optimistic_upper=None):
    """Return an auditable decision; times are full-four-chain wall-clock estimates.

    Candidates map window to {setup_seconds, progress_per_round, round_seconds,
    simultaneous_lower}; the bound must be supplied by a separately frozen
    simultaneous calibration and must include the entire first-use probe cost.
    Missing/invalid calibration conservatively excludes that candidate.
    `probe_seconds` is incremental and excludes shared work.
    """
    t_seq=baseline(retained,shared_seconds,sequential_setup_seconds,sequential_step_seconds,
                   delivery_fixed_seconds,delivery_per_step_seconds)
    probe=number(probe_seconds,"probe_seconds")
    if optimistic_upper is not None:
        optimistic=number(optimistic_upper,"optimistic_upper",positive=True)
        if optimistic <= THRESHOLD:
            return {"choice":"sequential","reason":"optimistic_upper_not_above_threshold",
                    "probe_performed":False,"baseline_seconds":t_seq,
                    "predicted_strategy_seconds":t_seq,"windows":[]}
    if not isinstance(candidates,dict) or any(type(w) is not int or w not in WINDOWS for w in candidates):
        raise ValueError("candidate windows must be drawn from the planned grid")
    common=number(shared_seconds,"shared_seconds")
    delivery=number(delivery_fixed_seconds,"delivery_fixed_seconds")+retained*number(
        delivery_per_step_seconds,"delivery_per_step_seconds")
    rows=[]
    for w in sorted(candidates):
        row={"window":w}
        try:
            data=candidates[w]
            setup=number(data["setup_seconds"],"setup_seconds")
            progress=number(data["progress_per_round"],"progress_per_round",positive=True)
            if progress>w:
                raise ValueError("progress cannot exceed the window")
            round_cost=number(data["round_seconds"],"round_seconds",positive=True)
            lower=number(data["simultaneous_lower"],"simultaneous_lower")
            t_parallel=number(common+probe+setup+(DISCARD+retained)/progress*round_cost+delivery,
                              "parallel total",positive=True)
            speed=number(t_seq/t_parallel,"predicted speedup",positive=True)
            row.update(predicted_seconds=t_parallel,predicted_speedup=speed,
                       simultaneous_lower=lower,eligible=lower>THRESHOLD)
        except (KeyError,TypeError,ValueError,OverflowError,ZeroDivisionError) as error:
            row.update(eligible=False,invalid_reason=str(error))
        rows.append(row)
    eligible=[row for row in rows if row['eligible']]
    if not eligible:
        return {"choice":"sequential","reason":"no_calibrated_lower_above_threshold",
                "probe_performed":True,"baseline_seconds":t_seq,
                "predicted_strategy_seconds":t_seq+probe,"windows":rows}
    chosen=max(eligible,key=lambda row:(row['simultaneous_lower'],-row['window']))
    return {"choice":chosen['window'],"reason":"highest_calibrated_lower_above_threshold",
            "probe_performed":True,"baseline_seconds":t_seq,
            "predicted_strategy_seconds":chosen['predicted_seconds'],"windows":rows}
