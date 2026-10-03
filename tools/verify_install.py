"""Archive HEAD, build an ordinary wheel, test a fresh isolated installation.

Every module must match Git blob -> archive -> wheel -> installed bytes.
No editable install or PYTHONPATH is used. The CLI path comes from target
interpreter sysconfig rather than assuming Scripts/bin from the host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def run(args, cwd=None, include_stderr=False):
    p = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True,
                       env={k:v for k,v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")})
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {args}\n{p.stdout}\n{p.stderr}")
    return "\n".join(v for v in (p.stdout.strip(), p.stderr.strip() if include_stderr else "") if v)


def verify(repo, ref, probe=None):
    sha = run(["git", "rev-parse", ref], repo)
    with tempfile.TemporaryDirectory(prefix="evalenvelope-wheel-") as temp:
        work = Path(temp); archive = work/"source.tar"
        run(["git", "archive", "--format=tar", "-o", archive, sha], repo)
        source = work/"source"; source.mkdir()
        with tarfile.open(archive) as t: t.extractall(source, filter="data")
        target = work/"env"; venv.EnvBuilder(with_pip=True).create(target)
        python = target/("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([python, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", work/"wheels", source], work)
        wheel = next((work/"wheels").glob("*.whl"))
        run([python, "-m", "pip", "install", "--no-deps", wheel], work)
        locations = json.loads(run([python, "-c", "import sysconfig,evalenvelope,json;print(json.dumps({'scripts':sysconfig.get_path('scripts'),'package':evalenvelope.__file__}))"], work))
        installed = Path(locations["package"]).parent
        checked = {}
        with zipfile.ZipFile(wheel) as z:
            for path in sorted((source/"src/evalenvelope").glob("*.py")):
                relative = "src/evalenvelope/"+path.name
                blob = subprocess.run(["git", "show", sha+":"+relative], cwd=repo, capture_output=True, check=True).stdout
                payload = path.read_bytes()
                if not blob == payload == z.read("evalenvelope/"+path.name) == (installed/path.name).read_bytes():
                    raise RuntimeError("Git/archive/wheel/install bytes differ: "+relative)
                checked[relative] = hashlib.sha256(blob).hexdigest()
        cli = Path(locations["scripts"])/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
        help_text = run([cli, "--help"], work)
        if "Finite paired benchmark" not in help_text: raise RuntimeError("registered CLI missing")
        tests = run([python, "-m", "unittest", "discover", "-s", source/"tests", "-v"], work, include_stderr=True)
        demo = json.loads(run([python, source/"tools/demo.py", cli, work/"demo"], work))
        contrast = json.loads(run([python, source/"tools/contrast.py"], work))
        retained_probes = {}
        for p in sorted((source/"docs/evidence").glob("probe_round*.py")):
            retained_probes[p.name] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                      "output": run([python, p], work)}
        probe_result = run([python, Path(probe).resolve()], work) if probe else None
        return {"commit": sha, "python": run([python, "--version"]), "ordinary_wheel": wheel.name, "module_hashes": checked,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "binding_check": "Git blob == archive == ordinary wheel == installed module bytes",
                "registered_cli_verified": True, "tests": "passed", "test_output": tests,
                "retained_probes": retained_probes, "demo": demo, "contrast": contrast, "probe": probe_result}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--ref", default="HEAD"); p.add_argument("--probe"); p.add_argument("--output")
    args = p.parse_args()
    result = verify(Path(__file__).resolve().parents[1], args.ref, args.probe)
    content = json.dumps(result, indent=2)+"\n"
    if args.output:
        dest = Path(args.output); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(content, encoding="utf-8")
    print(content)
