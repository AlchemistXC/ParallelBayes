"""Check whether archived Mac logistic references target the Windows posterior.

No new sampling; no retroactive change to windows-native-v1 or its error labels.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import expit


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def checked_protocol(path, expected):
    protocol = read(path)
    unsigned = dict(protocol)
    recorded = unsigned.pop("protocol_sha256")
    if recorded != expected or identity(unsigned) != expected:
        raise ValueError("Protocol identity mismatch")
    return protocol


def audit(root, raw_root, output):
    if output.exists():
        raise FileExistsError("Use a new companion output directory")
    if output == raw_root or raw_root in output.parents:
        raise ValueError("Do not write inside reference evidence")
    reference = checked_protocol(root / "benchmark/protocols/reference-v1.json",
        "13f1baa4a13fd25f3fe58d3303948c6ece8186ebcf6eb540eb8feb623206edc0")
    windows = checked_protocol(root / "benchmark/protocols/windows-native-v1.json",
        "1d233dd09956c4575fc5775082310e5edca65407db5fcef40bc2ce329e6f5898")
    summary_path = root / "benchmark/analysis/outputs/reference-summary.json"
    summary = read(summary_path)
    provenance = read(summary_path.with_suffix(".provenance.json"))
    if sha(summary_path) != provenance["summary_sha256"]:
        raise ValueError("Reference summary checksum mismatch")
    if sha(raw_root / "manifest.json") != provenance["manifest_sha256"]:
        raise ValueError("Reference manifest checksum mismatch")
    if read(raw_root / "manifest.json")["identity"] != provenance["identity"]:
        raise ValueError("Reference run identity mismatch")
    expected_tasks = {identity(t)[:20]: t for t in reference["tasks"]}
    actual = {p.parent.name: p for p in raw_root.glob("tasks/*/state.json")}
    if set(expected_tasks) != set(actual) or len(expected_tasks) != len(reference["tasks"]):
        raise ValueError("Reference task set differs")
    arrays, metadata = defaultdict(list), defaultdict(list)
    for tid, statefile in sorted(actual.items()):
        if sha(statefile) != provenance["state_sha256"][tid]:
            raise ValueError("Reference state checksum mismatch")
        state = read(statefile)
        if state["task"] != expected_tasks[tid] or state["status"] != "completed":
            raise ValueError("Reference task mismatch or failure")
        folder = statefile.parent / state["attempt"]
        for filename, digest in state["checksums"].items():
            if sha(folder / filename) != digest:
                raise ValueError("Reference artifact checksum mismatch")
        result = read(folder / "result.json")
        name = state["task"]["model"]
        spec = reference["models"][name]
        if spec != windows["models"][name] or identity(spec) != provenance["model_sha256"][name]:
            raise ValueError("Target, data or coordinates differ")
        if result["target_id"] != identity(spec) or result["status"] != "completed":
            raise ValueError("Saved reference has another target or failed")
        with np.load(folder / "raw.npz", allow_pickle=False) as raw:
            draws = raw["draws"]
            if draws.shape != (4, 16384, 8) or not np.isfinite(draws).all():
                raise ValueError("Unexpected reference samples")
            # Explicitly the common Mac/Windows logistic function contract.
            f = np.stack([draws[..., 0], draws[..., 1], expit(draws[..., 0]), draws[..., 0] > 0], axis=-1)
        arrays[name].append(f)
        metadata[name].append(dict(task_id=tid, seed=state["task"]["config"]["seed"],
            raw_sha256=state["checksums"]["raw.npz"],
            divergences=int(np.asarray(result["diagnostics"]["divergent"]).sum())))
    report = dict(scope="reference-identity and finite-summary reuse audit; no new accuracy pass claim",
        reference_protocol_sha256=reference["protocol_sha256"], windows_protocol_sha256=windows["protocol_sha256"],
        functions=["q1", "q2", "sigmoid(q1)", "q1>0"], checked_reference_fits=len(actual), models={},
        reference_summary_sha256=sha(summary_path), reference_manifest_sha256=sha(raw_root / "manifest.json"),
        source_script_sha256=sha(Path(__file__)))
    windows_seeds={t["config"]["seed"] for t in windows["tasks"]}
    for name, fits in arrays.items():
        if len(fits) != 4 or any(m["seed"] in windows_seeds for m in metadata[name]):
            raise ValueError("Reference fit count or random-stream namespaces differ from expected design")
        joined=np.concatenate(fits,axis=0)
        means=np.array([f.mean((0,1)) for f in fits])
        mean=joined.mean((0,1))
        between=means.std(axis=0,ddof=1)/2
        batches=joined.reshape(16,32,512,4).mean(axis=2).reshape(512,4)
        batch=batches.std(axis=0,ddof=1)/np.sqrt(512)
        mcse=np.maximum(batch,between)
        saved=summary[name]
        np.testing.assert_allclose(mean,saved["mean"],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(batch,saved["batch_mcse"],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(between,saved["between_fit_mcse"],rtol=1e-12,atol=1e-12)
        informative=np.asarray(saved["informative_functions"],bool)
        variance=joined.var(axis=(0,1),ddof=1)
        event_count=int(joined[...,3].sum())
        if saved["event_positive_counts"][3] != event_count:
            raise ValueError("Saved event count differs")
        report["models"][name]=dict(specification_exactly_equal=True,target_id=identity(reference["models"][name]),
            fits=metadata[name],independent_fits=4,chains_per_fit=4,draws_per_chain=16384,
            total_correlated_draws=joined.shape[0]*joined.shape[1],mean=mean.tolist(),
            conservative_mcse=[float(x) if ok else None for x,ok in zip(mcse,informative)],
            raw_function_variance=variance.tolist(),
            # Scale is a descriptive candidate only; it has not been frozen as a new metric.
            reference_mcse_over_function_sd=[float(se/np.sqrt(v)) if ok and v>0 else None
                for se,v,ok in zip(mcse,variance,informative)],
            usable_function_indices=np.flatnonzero(informative).tolist(),
            unresolved_function_indices=np.flatnonzero(~informative).tolist(),
            sign_event_positive_count=event_count,sign_event_negative_count=joined.shape[0]*joined.shape[1]-event_count,
            all_function_mcse_available=bool(informative.all()),
            limitations=["Same target identity permits reuse, but finite reference may have shared sampler bias.",
                "Four fits are the independent reference units, not 262144 independent draws.",
                "Undefined event uncertainty remains undefined; zero observations do not prove zero probability.",
                "Seeds verify distinct recorded namespaces, not a general proof of independent PRNG substreams."])
    output.mkdir(parents=True)
    (output / "reference-reuse.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({name:dict(target_equal=r["specification_exactly_equal"],
        all_mcse_available=r["all_function_mcse_available"],mcse=r["conservative_mcse"])
        for name,r in report["models"].items()},indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument("--reference-run",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    audit(args.root.resolve(),args.reference_run.resolve(),args.output.resolve())
