"""Exercise an installed distribution outside the source checkout, without runtime dependencies."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--library", type=Path, required=True)
    args = parser.parse_args()
    wheel, library = args.wheel.resolve(), args.library.resolve()
    with tempfile.TemporaryDirectory(prefix="nfclaw-package-check-") as temporary:
        scratch = Path(temporary)
        environment = scratch / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / "bin/python"
        executable = environment / "bin/nfclaw"
        env = {**os.environ, "NFCLAW_LIBRARY_ROOT": str(library),
               "NFCLAW_STATE_DIR": str(scratch / "state")}
        env.pop("PYTHONPATH", None)

        def run(command, expected=0):
            result = subprocess.run([str(p) for p in command], cwd=scratch, env=env,
                                     capture_output=True, text=True, timeout=120)
            if result.returncode != expected:
                raise SystemExit(f"Package check failed: {command}\n"
                                 f"{result.stdout}\n{result.stderr}")
            return result.stdout

        run([python, "-m", "pip", "install", "--no-deps", wheel])
        imported = Path(run([python, "-I", "-c", "import runner; print(runner.__file__)"]).strip())
        assert imported.is_relative_to(environment), imported
        expected = {p.name for p in (library / "pipelines").iterdir() if (p / "skill.md").is_file()}
        found = {line.split("\t")[0] for line in run([executable, "list"]).splitlines()}
        assert expected and found == expected, (expected, found)
        run([executable, "show", sorted(found)[0]])
        run([executable, "chain", "edges"])
        status = json.loads(run([executable, "status", scratch / "absent", "--json"], expected=1))
        assert status["schema_version"] == 1 and status["state"] == "missing"
        run([python, "-I", "-c", "import json; from importlib.resources import files; "
             "[json.loads(files('runner').joinpath(n).read_text()) for n in "
             "('path_roles.json','input_roles.json','param_roles.json')]"])
        print(f"Distribution installed independently; discovered {len(found)} pipelines; "
              "configured documentation, handoffs, status and audited registries passed.")


if __name__ == "__main__":
    main()
