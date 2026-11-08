"""What a built wheel ships (pyproject.toml's setuptools configuration)."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_package_data_lives_in_a_listed_package():
    # setuptools treats any directory under a package as a package of its own, and warns that one
    # `packages` does not list "would be ignored": runner/output_contracts holds only JSON, which
    # the wheel kept only by that deprecated fallback.
    setuptools = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "setuptools"]
    packages = set(setuptools["packages"])
    for package, patterns in setuptools["package-data"].items():
        assert package in packages, package
        for pattern in patterns:
            files = sorted((ROOT / package.replace(".", "/")).glob(pattern))
            assert files, f"{package}: {pattern} matches nothing"
            for path in files:
                owner = ".".join(path.parent.relative_to(ROOT).parts)
                assert owner in packages, f"{path.relative_to(ROOT)} belongs to unlisted {owner}"
