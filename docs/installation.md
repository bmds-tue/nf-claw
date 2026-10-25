# Installing the executable and pipeline library

Python 3.11 or newer is required. Editable checkouts continue to work:

```bash
git clone https://github.com/bmds-tue/nf-claw.git /data/nf-claw
cd /data/nf-claw
python3 -m venv /data/nfclaw-env
/data/nfclaw-env/bin/pip install -e '.[dev,yaml]'
```

An installed wheel or source distribution can use a separate library checkout:

```bash
python3 -m pip install /path/to/nfclaw-1.0.0-py3-none-any.whl
export NFCLAW_LIBRARY_ROOT=/data/nf-claw
nfclaw list
nfclaw show demo
```

Set the variable in the environment that starts an MCP server too. It selects
the library explicitly and takes precedence over content adjacent to an editable
installation. A bad configured path is an error; nf-claw never silently chooses
another library. CLI `status`, `verify`, `doctor` and job metadata commands can
operate without a library. Python packages carry the audited role registries;
pipeline source, generated pipeline documentation, handoffs and catalogs come
from the selected library. Pinned sources initialize on demand using that
checkout's Git metadata; keep library content writable for initialization and
version materialization. Scientific inputs, outputs and work directories retain
their existing separation requirements.

Build and test a distribution from a clean branch:

```bash
python3 -m pip install build
python3 -m build
python3 scripts/check_package_install.py dist/nfclaw-1.0.0-py3-none-any.whl --library .
```

The installation check creates a fresh environment outside the checkout, installs
the wheel without dependencies and exercises configured discovery, documentation,
handoffs, structured status and packaged registries. The same check runs in CI.

For reproducible development installs use `pip install -c constraints/dev.txt
-e '.[dev,yaml]'`. The minimum-dependency CI job deliberately uses
`constraints/minimum.txt` with the minimum supported Python; ordinary Python CI
also tests current dependency releases within the declared package bounds.
