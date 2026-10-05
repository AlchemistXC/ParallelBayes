"""Environment inspection and the legacy JAX protocol runner.

Select a command before importing an optional numerical provider.
"""
import argparse
from importlib.util import find_spec
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="ParallelBayes environment and legacy JAX runner")
    commands = parser.add_subparsers(dest="command", required=True)
    env = commands.add_parser("environment", help="record the numerical environment")
    env.add_argument("--backend", choices=["jax", "torch"], default="jax")
    env.add_argument("--output", default="execution/environment.json")
    run = commands.add_parser("run", help="run a legacy JAX frozen protocol")
    run.add_argument("protocol")
    run.add_argument("--output", required=True)
    run.add_argument("--root", default=".")
    run.add_argument("--platform", choices=["cpu", "gpu"], default="cpu")
    run.add_argument("--retry-failed", action="store_true")
    run.add_argument("--limit", type=int)
    recover = commands.add_parser("recover", help="recover a legacy JAX run lock")
    recover.add_argument("output")
    args = parser.parse_args()

    backend = args.backend if args.command == "environment" else "jax"
    if find_spec(backend) is None:
        hint = " Use 'environment --backend torch' for a torch-only environment." if backend == "jax" else ""
        parser.error(
            f"The optional '{backend}' provider is not installed in this Python environment. "
            f"Install the matching dependencies described in docs/INSTALL-AND-USE.md.{hint}"
        )

    if args.command == "environment":
        if args.backend == "torch":
            from .torch_backend.sampling import environment
        else:
            from .sampling import environment
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(environment(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    elif args.command == "recover":
        from .experiment import recover_lock
        recover_lock(args.output)
    else:
        from .experiment import run_protocol
        run_protocol(args.protocol, args.output, args.root, args.platform, args.retry_failed, args.limit)


if __name__ == "__main__":
    main()
