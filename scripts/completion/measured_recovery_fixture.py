"""Explicit technical failure injection after a real audited MALA workflow.

Never use this worker for a formal study. Original and retry retain the same
request/source; only the deterministic retry output path distinguishes them.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from measured_audit_worker import main

if __name__=='__main__':
    output=Path(sys.argv[2]);main(sys.argv[1],output)
    if not output.parent.name.endswith('.retry'):
        sys.exit(7)
