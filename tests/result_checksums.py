"""The checksums of a run's results, for comparing them with what a bundle records."""
from pathlib import Path

from runner.outputs import result_files
from runner.provenance import sha256_file


def output_checksums(outdir: Path) -> dict[str, str]:
    """The run's result files as {path relative to outdir: sha256}, in sorted order.

    What `outputs.snapshot` hashes and a bundle's `outputs.sha256` records: Nextflow's own state
    (`.nextflow*`) and the provenance bundle are not results.
    """
    return {p.relative_to(outdir).as_posix(): sha256_file(p) for p in sorted(result_files(outdir))}
