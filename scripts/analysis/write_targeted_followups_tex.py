#!/usr/bin/env python3
"""Rebuild H1/L2 manuscript fragments from pinned, independently audited summaries.

This reporter does not run sampling or change any frozen protocol. The input root
may be a relocated summary capsule; templates and the manifest are explicit inputs.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

H1 = "benchmark/analysis/outputs/h1-function-path-companion-v1/"
L2 = "benchmark/analysis/outputs/l2-rare-reference-is-v1/"
FUNCTIONS = {"v_over_3": r"$v/3$", "tanh_v_over_3": r"$\tanh(v/3)$",
             "x1_positive": r"$\ind(x_1>0)$", "cos_z1": r"$\cos(x_1e^{-v/2})$"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sci(x, digits=4):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError("nonfinite manuscript number")
    if x == 0:
        return "0"
    mantissa, exponent = f"{x:.{digits-1}e}".split("e")
    return rf"{mantissa}\times10^{{{int(exponent)}}}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def render(root, manifest_path, templates):
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    raw = {}
    for relative, expected in manifest["files"].items():
        p = Path(relative)
        require(not p.is_absolute() and ".." not in p.parts, "unsafe input path")
        raw[relative] = (root / p).read_bytes()
        require(digest(raw[relative]) == expected, f"input SHA256 mismatch: {relative}")
    def read_json(name):
        return json.loads(raw[name])
    h = read_json(H1 + "SUMMARY.json")
    provenance = read_json(H1 + "provenance.json")
    direct = read_json(H1 + "h1-direct-array-validation.json")
    require(provenance["source_summary_sha256"] == digest(raw[H1 + "SUMMARY.json"]), "H1 summary binding")
    require(provenance["source_data_sha256"]["function-differences.csv"] == digest(raw[H1 + "function-differences.csv"]), "H1 table binding")
    require(direct["passed"] and direct["rows"] == 3200 and direct["tasks"] == 80, "H1 audit incomplete")
    require(h["total"] == 80 and h["original_outcomes"] == {"valid":38, "numerical_failure":42}, "H1 scope changed")
    require(all(h[k] == 0 for k in ("acceptance_mismatches", "new_formal_repetitions", "new_random_inputs", "new_sampler_workflow_calls", "classifications_changed", "failed_paths_promoted", "function_metrics_with_nonfinite")), "H1 evidence boundary changed")
    rows = list(csv.DictReader(io.StringIO(raw[H1 + "function-differences.csv"].decode())))
    require(len(rows) == 3200 and len({r["task_id"] for r in rows}) == 80, "H1 incomplete rows")
    require(all(r["status"] == "finite" and int(r["nonfinite_count"]) == 0 for r in rows), "H1 nonfinite rows")
    tokens = {"H1_TRANSITIONS": str(h["deterministic_reference_transitions"])}
    h1_table = []
    maxima = {}
    for name, label in FUNCTIONS.items():
        pooled = [r for r in rows if r["scope"] == "retained" and r["chain"] == "pooled" and r["function"] == name]
        chains = [r for r in rows if r["scope"] == "retained" and r["chain"] != "pooled" and r["function"] == name]
        require(len(pooled) == 80 and len(chains) == 320, "H1 missing group")
        values = [max(float(r["max_abs"]) for r in pooled), max(abs(float(r["signed_mean"])) for r in pooled), max(abs(float(r["signed_mean"])) for r in chains)]
        maxima[name] = values
        require(math.isclose(values[2], direct["max_abs_single_chain_mean"][name], rel_tol=1e-12, abs_tol=1e-30), "H1 audit disagreement")
        h1_table.append(label + " & " + " & ".join("$"+sci(v)+"$" for v in values) + r"\\")
    require(all(int(r["event_disagreements"]) == 0 for r in rows if r["function"] == "x1_positive"), "H1 event mismatch")
    tokens.update(H1_TABLE="\n".join(h1_table), H1_POINT=sci(max(v[0] for v in maxima.values()),3), H1_MEAN=sci(max(v[1] for v in maxima.values()),3))
    l = read_json(L2 + "SUMMARY.json")
    audit = read_json(L2 + "audit.json")
    selection = read_json(L2 + "SELECTION.json")
    batches = read_json(L2 + "batches-reaggregated.json")
    sensitivity = read_json(L2 + "old-L2-event-sensitivity.json")
    require(audit["passed"] and audit["source_summary_sha256"] == digest(raw[L2 + "SUMMARY.json"]), "L2 audit binding")
    require(l["formal_reference_points"] == 2097152 and l["pilot_points"] == 16384 and l["new_mcmc_fits"] == 0, "L2 budget changed")
    require(selection["selected"] == [0, 1] and selection["pilot_excluded"], "L2 selection changed")
    require(audit["old_frame_counts"]["valid"] == 414 and audit["old_frame_counts"]["output_failure_unclassified"] == 18, "L2 old outcomes changed")
    estimates, weights, batch_rows = [], [], []
    require(len(l["reference_estimates"]) == 2, "L2 missing proposal")
    for i, e in enumerate(l["reference_estimates"]):
        bb = [b for b in batches if b["candidate"] == e["candidate"]]
        require(len(bb) == 8 and len({b["batch"] for b in bb}) == 8, "L2 independent batch count")
        require(len({b["shift"] for b in bb}) == 1, "L2 unequal log shifts")
        aa = math.fsum(b["scaled_A"] for b in bb)/8
        dd = math.fsum(b["scaled_B"] for b in bb)/8
        probability = aa/dd
        variance = math.fsum(((b["scaled_A"]-aa)-probability*(b["scaled_B"]-dd))**2 for b in bb)/7
        mcse = math.sqrt(variance/8)/dd
        require(math.isclose(probability, e["probability"], rel_tol=1e-12), "L2 ratio disagreement")
        require(math.isclose(mcse, e["mcse"], rel_tol=1e-10), "L2 MCSE disagreement")
        require(e["quality_targets_met"], "L2 quality status changed")
        group = [r for r in sensitivity if r["reference_candidate"] == e["candidate"]]
        require(len(group) == 18 and all(r["empirical_all_zero"] and r["old_task_outcomes_unchanged"] and r["undefined_chain_diagnostics_unchanged"] for r in group), "L2 sensitivity boundary changed")
        require(all(math.isclose(r["event_only_mse"], probability**2, rel_tol=1e-12) for r in group), "L2 squared-reference disagreement")
        name = f"Q{i+1}"
        estimates.append(name + " & $"+sci(probability,6)+"$ & $"+sci(mcse,4)+f"$ & {100*e['relative_mcse']:.3f}\\%" + r"\\")
        weights.append(name + f" & {e['numerator_ess']:.2f} & {e['denominator_ess']:.2f} & $"+sci(e['maximum_numerator_weight'])+"$ & $"+sci(e['maximum_denominator_weight'])+r"$\\")
        tokens[f"L2_P{i+1}"] = sci(probability,3)
        tokens[f"L2_MSE{i+1}"] = sci(probability**2,4)
    for k in range(8):
        values = []
        for e in l["reference_estimates"]:
            b = e["batches"][k]
            values.extend([f"{b['probability']*1e9:.5f}",f"{b['numerator_ess']:.2f}", f"{b['maximum_numerator_weight']:.5f}"])
        batch_rows.append(str(k+1)+" & "+" & ".join(values)+r"\\")
    tokens.update(L2_ESTIMATES="\n".join(estimates), L2_WEIGHTS="\n".join(weights), L2_BATCHES="\n".join(batch_rows))
    rendered, template_hashes = {}, {}
    for name in ("h1-main", "h1-si", "l2-main", "l2-si"):
        file = templates/f"targeted-{name}.template.tex"
        data = file.read_bytes()
        source = data.decode()
        used = set(re.findall(r"@([A-Z0-9_]+)@", source))
        require(not (used-set(tokens)), f"unknown template tokens: {used-set(tokens)}")
        rendered[f"targeted-{name}.generated.tex"] = "% Generated by write_targeted_followups_tex.py; edit the template.\n" + re.sub(r"@([A-Z0-9_]+)@", lambda m: tokens[m.group(1)], source)
        template_hashes[file.name] = digest(data)
    provenance = {"identity":manifest["identity"],"manifest_sha256":digest(manifest_bytes),"inputs":manifest["files"],"templates":template_hashes,"generator_sha256":digest(Path(__file__).read_bytes()),"new_mcmc_calls":0,"h1_maxima_retained":maxima,"generated":{k:digest(v.encode()) for k,v in rendered.items()}}
    rendered["targeted-paper.provenance.json"] = json.dumps(provenance,ensure_ascii=False,indent=2)+"\n"
    return rendered


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--templates",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=render(args.root,args.manifest,args.templates)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,text in result.items():
        (args.output/name).write_text(text,encoding="utf-8")
    print(json.dumps({"files":list(result),"new_mcmc_calls":0}))


if __name__ == "__main__":
    main()
