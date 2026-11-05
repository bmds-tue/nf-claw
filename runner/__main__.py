import sys

# `python3 -m runner` needs no install, so nothing has checked `requires-python` (macOS's python3 is
# 3.9, where the imports below fail with an ImportError about something else).
if sys.version_info < (3, 11):  # noqa: UP036
    raise SystemExit(f"nfclaw needs Python 3.11 or newer; {sys.executable} is "
                     f"{sys.version.split()[0]}. Run it with a newer python3.")

from runner.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
