"""Compile both standalone Chinese documents (Python standard library only)."""
from pathlib import Path
import argparse
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
DOCUMENTS = ("研究计划.tex", "研究结果报告.tex")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", default="auto", help="auto, tectonic, xelatex, or executable path")
    p.add_argument("--output", type=Path, default=HERE / "build")
    a = p.parse_args()
    executable = a.compiler
    if executable == "auto":
        executable = shutil.which("tectonic") or shutil.which("xelatex")
    elif executable in ("tectonic", "xelatex"):
        executable = shutil.which(executable)
    if not executable:
        raise SystemExit("Install Tectonic or a TeX Live/MacTeX/MiKTeX XeLaTeX with ctex and Fandol fonts.")
    out = a.output.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    name = Path(executable).name.lower()
    for document in DOCUMENTS:
        if name.startswith("tectonic"):
            command = [str(executable), "-X", "compile", "--outdir", str(out), "--keep-logs", "--keep-intermediates", document]
            passes = 1
        elif name.startswith("xelatex"):
            command = [str(executable), "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(out), document]
            passes = 3
        else:
            raise SystemExit("Compiler executable must be named tectonic or xelatex.")
        logs = []
        for _ in range(passes):
            result = subprocess.run(command, cwd=HERE, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logs.append(result.stdout)
            if result.returncode:
                print(result.stdout)
                raise SystemExit(result.returncode)
        (out / (Path(document).stem + ".build.txt")).write_text("\n".join(logs), encoding="utf-8")
        pdf = out / Path(document).with_suffix(".pdf")
        if not pdf.is_file():
            raise SystemExit("Compiler returned without PDF: " + str(pdf))
        print(pdf)

if __name__ == "__main__":
    main()
