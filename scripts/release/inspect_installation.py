"""Record an installed distribution without importing an optional provider.

Run with the target environment's Python -I from outside the source checkout.
This is installation evidence, not a sampler or hardware performance test.
"""
import argparse
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import platform
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new evidence file")
    import parallelbayes
    distribution = metadata.distribution("parallelbayes")
    if parallelbayes.__version__ != args.expected_version or distribution.version != args.expected_version:
        parser.error("Imported module and installed metadata do not match the expected version")
    record = {
        "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "prefix": sys.prefix, "base_prefix": sys.base_prefix,
        "isolated_mode": sys.flags.isolated,
        "module": str(Path(parallelbayes.__file__).resolve()),
        "version": parallelbayes.__version__,
        "distribution_root": str(Path(distribution.locate_file("")).resolve()),
        "direct_url": json.loads(distribution.read_text("direct_url.json") or "null"),
        "providers_installed": {name: importlib.util.find_spec(name) is not None for name in ("jax", "torch", "pyro", "bridgestan")},
        "distributions": sorted(
            [{"name": item.metadata["Name"], "version": item.version,
              "root": str(Path(item.locate_file("")).resolve())} for item in metadata.distributions()],
            key=lambda item: item["name"].lower(),
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
