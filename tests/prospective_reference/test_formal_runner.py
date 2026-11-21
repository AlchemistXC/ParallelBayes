"""End-to-end formal-runner test using an explicitly synthetic test seal."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_reference"))
sys.path.insert(0, str(Path(__file__).parent))
from models import logistic_fixture, ode_fixture
from create_freeze import create
from formal_run import verify_freeze
from restart import blocks, same

RUNNER = ROOT/"scripts/prospective_reference/formal_run.py"
REFERENCE = ROOT/"scripts/prospective_reference"
PROTOCOL = ROOT/"docs/prospective-first-use-v1"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True)+"\n")
    return digest(path)


def main():
    with tempfile.TemporaryDirectory(prefix="parallelbayes-formal-runner-test-") as name:
        root = Path(name)
        model, initial = logistic_fixture()
        ode, ode_initial = ode_fixture(False)
        inputs = root/"inputs"
        inputs.mkdir()
        np.savez(inputs/"data.npz", trials=model.trials, successes=model.successes,
                 ode_log_observations=ode.observations)
        np.savez(inputs/"initials.npz", logistic=np.tile(initial,(10,1)), ode=np.tile(ode_initial,(10,1)))
        manifest = {"scope":"synthetic test fixture", "data_sha256":digest(inputs/"data.npz"),
                    "initials_sha256":digest(inputs/"initials.npz"),
                    "initials":{"formal_random_stream_seed":8819}, "ode":{"center":np.exp(ode.center).tolist()}}
        manifest_hash = write_json(inputs/"manifest.json", manifest)
        preflight_hash = write_json(inputs/"preflight.json", {
            "inputs_manifest_sha256":manifest_hash, "data_sha256":manifest["data_sha256"],
            "initials_sha256":manifest["initials_sha256"],
            "checks":{"logistic":{"passed":True},"ode":{"passed":True}}})
        points_hash = write_json(inputs/"ode-points.json", {"status":"passed","manifest_sha256":manifest_hash})
        required = {"identity":"prospective-first-use-v1", "status":"frozen",
                    "study_protocol":digest(PROTOCOL/"DECISIONS.md"),
                    "model_source":digest(REFERENCE/"models.py"),
                    "runner_source":digest(RUNNER),
                    "checkpoint_source":digest(REFERENCE/"checkpoint.py"),
                    "engine_source":digest(REFERENCE/"run.py"),
                    "cohort_source":digest(REFERENCE/"cohort.py"),
                    "extension_source":digest(REFERENCE/"extend_cohort.py"),
                    "diagnostics_source":digest(ROOT/"scripts/analysis/prospective_reference_diagnostics.py"),
                    "diagnostics_r_source":digest(ROOT/"scripts/analysis/prospective_reference_diagnostics.R"),
                    "environment_lock":digest(PROTOCOL/"mac-environment/requirements-arm64.lock"),
                    "candidate_manifest":manifest_hash, "preflight":preflight_hash, "ode_points":points_hash}
        for field, expected_model in (("restart_logistic","logistic"),("restart_ode","ode-fast")):
            path = root/(field+".json")
            checksum = write_json(path, {"model":expected_model, "steps":2000,
                "position_and_diagnostics_byte_identical":True, "rollback_at_200":True,
                "wrong_chain_rejected":True,"idempotency":True})
            required[field] = {"file":path.name,"sha256":checksum}
        for field, values in (
            ("windows_qualification", {"planned":880, "accounted":880}),
            ("capacity", {"resources":{k:{"conservative":1, "available":10}
                          for k in ("windows_hours","windows_disk","mac_disk","archive")}})):
            path=root/(field+".json")
            checksum=write_json(path, {"identity":"prospective-first-use-v1","status":"passed",**values})
            required[field]={"file":path.name,"sha256":checksum}
        seal=root/"TEST-ONLY-seal.json"
        write_json(seal,required)
        # Builder exercises the production dependency bindings with test-only receipts.
        for model in ("logistic", "ode"):
            built = root/("test-only-built-seal-"+model)
            create(built, inputs, model, root/"windows_qualification.json", root/"capacity.json",
                   root/("restart_"+model+".json"))
            verify_freeze(built/"seal.json", inputs, model)
            other = "ode" if model == "logistic" else "logistic"
            try:
                verify_freeze(built/"seal.json", inputs, other)
            except ValueError:
                pass
            else:
                raise AssertionError("model-specific seal accepted for another model")
        def run(database, steps, *extra, code=0):
            command = [sys.executable, "-B", str(RUNNER), "logistic", str(inputs), str(seal),
                       str(database), "--chain", "1", "--steps", str(steps), *extra]
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode != code:
                raise AssertionError((result.returncode,result.stdout,result.stderr))
            return result
        split, full = root/"split.sqlite", root/"full.sqlite"
        assert json.loads(run(split,1000).stdout)["new_steps"] == 1000
        with sqlite3.connect(split) as database:
            identity = json.loads(database.execute("SELECT value FROM identity").fetchone()[0])
        assert identity["scope"] == "synthetic_test"
        assert json.loads(run(split,2000).stdout)["new_steps"] == 1000
        assert json.loads(run(split,2000).stdout)["new_steps"] == 0
        assert json.loads(run(full,2000).stdout)["new_steps"] == 2000
        same(blocks(split), blocks(full))
        error = run(split,2000,"--chain","2",code=1)
        assert "identity mismatch" in error.stderr
        if len(sys.argv) > 1:
            cohort = root/"cohort"
            command = [sys.executable, "-B", str(REFERENCE/"cohort.py"), "logistic", str(inputs), str(seal),
                       str(cohort), "--rscript", sys.argv[1]]
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            report = json.loads((cohort/"first-checkpoint.json").read_text())
            assert report["all_chains_complete"] and len(report["quantities"]) == 3
            assert len(list(cohort.glob("chain-*.sqlite"))) == 10
            result = subprocess.run([*command, "--resume"], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["new_sampling_steps"] == 0
            resume_logs = list(cohort.glob("chain-*.resume-*.json"))
            assert len(resume_logs) == 10
            assert all(json.loads(json.loads(path.read_text())["stdout"])["new_steps"] == 0
                       for path in resume_logs)
            # Force the previous synthetic diagnostic to represent a valid but
            # imprecise first checkpoint. This is fixture data, never evidence of
            # a real study's precision or Windows qualification.
            diagnostic = cohort/"diagnostics/receipt.json"
            synthetic = json.loads(diagnostic.read_text())
            synthetic["diagnostics_pass"] = True
            for quantity in synthetic["quantities"].values():
                quantity["mcse"] = 0.01
                quantity["precision_pass"] = True
            diagnostic_hash = write_json(diagnostic, synthetic)
            report["diagnostics_sha256"] = diagnostic_hash
            write_json(cohort/"first-checkpoint.json", report)
            extension = [sys.executable, "-B", str(REFERENCE/"extend_cohort.py"), "logistic",
                         str(inputs), str(seal), str(cohort), "--rscript", sys.argv[1], "--steps", "2000"]
            result = subprocess.run(extension, capture_output=True, text=True)
            assert result.returncode != 0 and "precision already passed" in result.stderr
            synthetic["quantities"]["mu"]["precision_pass"] = False
            synthetic["quantities"]["mu"]["mcse"] = None
            report["diagnostics_sha256"] = write_json(diagnostic, synthetic)
            write_json(cohort/"first-checkpoint.json", report)
            result = subprocess.run(extension, capture_output=True, text=True)
            assert result.returncode != 0 and "undefined precision" in result.stderr
            synthetic["quantities"]["mu"]["mcse"] = 0.01
            report["diagnostics_sha256"] = write_json(diagnostic, synthetic)
            write_json(cohort/"first-checkpoint.json", report)
            result = subprocess.run(extension, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["retained_per_chain"] == 2000
            assert len(list(cohort.glob("extension-2000-chain-*.json"))) == 10
            result = subprocess.run(extension, capture_output=True, text=True)
            assert result.returncode != 0 and "prior checkpoint" in result.stderr
            print("synthetic test: ten-chain 1000-to-2000 extension and refusal gates passed")
            for prior, target in ((2000, 4000), (4000, 8000)):
                diagnostic = cohort/f"diagnostics-{prior}/receipt.json"
                synthetic = json.loads(diagnostic.read_text())
                synthetic["diagnostics_pass"] = True
                for quantity in synthetic["quantities"].values():
                    quantity["mcse"] = .01
                    quantity["precision_pass"] = False
                checkpoint = cohort/f"checkpoint-{prior}.json"
                report = json.loads(checkpoint.read_text())
                report["diagnostics_sha256"] = write_json(diagnostic, synthetic)
                write_json(checkpoint, report)
                result = subprocess.run([*extension[:-1], str(target)], capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
                assert json.loads(result.stdout)["retained_per_chain"] == target
            print("synthetic test: ten-chain 2000-to-4000-to-8000 extension passed")
            failure_marker = cohort/"cohort-failed-test.json"
            failure_marker.write_text("{}")
            result = subprocess.run([*command, "--resume"], capture_output=True, text=True)
            assert result.returncode != 0 and "failed calls requiring classification" in result.stderr
            assert len(list(cohort.glob("chain-*.resume-*.json"))) == 10
            failure_marker.unlink()
            with sqlite3.connect(cohort/"chain-01.sqlite") as connection:
                connection.execute("DELETE FROM blocks WHERE last_step=1000")
            result = subprocess.run([*command, "--resume"], capture_output=True, text=True)
            assert result.returncode != 0 and "committed prefix is incomplete" in result.stderr
            assert len(list(cohort.glob("chain-*.resume-*.json"))) == 10
        capacity = root/"capacity.json"
        original = capacity.read_bytes()
        invalid = json.loads(original)
        invalid["resources"]["windows_hours"]["available"] = 0
        required["capacity"]["sha256"] = write_json(capacity,invalid)
        write_json(seal,required)
        error = run(root/"zero-capacity.sqlite",1000,code=1)
        assert "resource capacity exceeded" in error.stderr
        assert not (root/"zero-capacity.sqlite").exists()
        capacity.write_bytes(original)
        required["capacity"]["sha256"] = digest(capacity)
        write_json(seal,required)
        (inputs/"data.npz").write_bytes(b"tampered")
        error = run(root/"refused.sqlite",1000,code=1)
        assert "data_sha256" in error.stderr and not (root/"refused.sqlite").exists()
        if len(sys.argv) > 1:
            refused = root/"refused-cohort"
            result = subprocess.run([sys.executable, "-B", str(REFERENCE/"cohort.py"), "logistic",
                                     str(inputs), str(seal), str(refused), "--rscript", sys.argv[1]],
                                    capture_output=True, text=True)
            assert result.returncode != 0 and not refused.exists()
    print("synthetic test seal: formal runner resume, wrong chain and input tamper checks passed")


if __name__ == "__main__":
    main()
