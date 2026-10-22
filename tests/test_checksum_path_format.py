"""Independent checksum-format and filesystem-route oracles for replay provenance."""
import hashlib
import shutil
import subprocess

import pytest

from runner import provenance, replay_guard, verify
from runner.submodule import SubmoduleStatus


def _version(path):
    run = subprocess.run([path, "--version"], capture_output=True, text=True)
    return run.stdout + run.stderr


def _sha256sum():
    """A sha256sum that reads GNU's escaped lines, which the manifests follow: GNU's own when present,
    otherwise the system one (macOS's reads them too). Ubuntu 25.10+ installs uutils as `sha256sum`
    (0.10 rejects even its own escaped carriage-return line) and keeps GNU's as `gnusha256sum`;
    Homebrew's GNU coreutils provides `gsha256sum`."""
    for tool in ("sha256sum", "gnusha256sum", "gsha256sum"):
        path = shutil.which(tool)
        if path and "GNU coreutils" in _version(path):
            return path
    path = shutil.which("sha256sum")
    return path if path and "uutils" not in _version(path) else None


SHA256SUM = _sha256sum()


def record(out, source):
    (out / "provenance").mkdir(parents=True)
    (out / "result.txt").write_bytes(b"fixed result")
    provenance.write(outdir=out, pipeline="fixture", command_str="echo fixture",
        submodule=SubmoduleStatus("fixture", out.parent / "no-source", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source], nextflow_version="25.10.4", env_extra={"NXF_VER": "25.10.4"})


@pytest.mark.parametrize("name,escaped", [
    ("simple.txt", "simple.txt"), ("line\nfeed", r"line\nfeed"),
    ("carriage\rreturn", r"carriage\rreturn"), ("back\\slash", r"back\\slash"),
    ("literal\\n", r"literal\\n"), ("unicode\u2028separator", "unicode\u2028separator"),
    ("tab\tname", "tab\tname"), ("line\vseparator", "line\vseparator"),
])
def test_checksum_text_matches_literal_format_and_round_trips(tmp_path, name, escaped):
    digest = hashlib.sha256(b"fixed data").hexdigest()
    marker = "\\" if name != escaped else ""
    expected = f"{marker}{digest}  {escaped}\n"
    assert provenance.checksum_text({name: digest}) == expected
    manifest = tmp_path / "outputs.sha256"
    manifest.write_bytes(expected.encode())
    assert provenance.read_checksums(manifest) == {name: digest}
    # CRLF physical records must not add a carriage return to a decoded filename.
    manifest.write_bytes(expected.replace("\n", "\r\n").encode())
    assert provenance.read_checksums(manifest) == {name: digest}


@pytest.mark.parametrize("contents", [
    "\\" + "a" * 64 + r"  unknown\q" + "\n",
    "\\" + "a" * 64 + "  trailing\\\n",
    "a" * 64 + "  ../outside.txt\n",
    "\\" + "a" * 64 + r"  ../outside\n.txt" + "\n",
    "a" * 64 + "  duplicated.txt\n\\" + "a" * 64 + "  duplicated.txt\n",
])
def test_escaping_cannot_hide_bad_records_or_relative_traversal(tmp_path, contents):
    path = tmp_path / "outputs.sha256"
    path.write_text(contents)
    with pytest.raises(ValueError):
        provenance.read_checksums(path)


def test_legacy_unmarked_backslashes_remain_literal(tmp_path):
    path = tmp_path / "outputs.sha256"
    path.write_text("a" * 64 + r"  literal\n.txt" + "\n")
    assert provenance.read_checksums(path) == {r"literal\n.txt": "a" * 64}


def test_absolute_checksum_reader_refuses_relative_dependency_names(tmp_path):
    path = tmp_path / "inputs.sha256"
    path.write_text("a" * 64 + "  relative.fastq\n")
    with pytest.raises(ValueError):
        provenance.read_checksums(path, relative=False)


@pytest.mark.parametrize("parent", ["line\nfeed", "carriage\rreturn", "back\\slash", "unicode\u2028separator"])
def test_parent_names_cannot_make_a_fresh_bundle_unreadable(tmp_path, parent):
    data = tmp_path / parent
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    original = tmp_path / "original"
    record(original, source)
    replay_guard.verify_dependencies(original / "provenance")
    expected = hashlib.sha256(b"fixed scientific input").hexdigest()
    assert provenance.read_checksums(original / "provenance/inputs.sha256", relative=False) == {str(source): expected}
    moved = tmp_path / "moved"
    original.rename(moved)
    replay_guard.verify_dependencies(moved / "provenance")
    source.write_bytes(b"changed scientific input")
    with pytest.raises(ValueError, match="content changed"):
        replay_guard.verify_dependencies(moved / "provenance")


def test_parent_traversal_preserves_real_symlink_semantics_and_alias_basename(tmp_path):
    (tmp_path / "real/nested").mkdir(parents=True)
    (tmp_path / "route").symlink_to("real/nested", target_is_directory=True)
    target = tmp_path / "real/stored.data"
    target.write_bytes(b"actual scientific input")
    (tmp_path / "real/reads.fastq").symlink_to("stored.data")
    # Lexically collapsing route/.. would select the deliberately different decoy.
    (tmp_path / "reads.fastq").write_bytes(b"wrong decoy")
    source = tmp_path / "route/../reads.fastq"
    original = tmp_path / "original"
    record(original, source)
    replay_guard.verify_dependencies(original / "provenance")
    hashes = provenance.read_checksums(original / "provenance/inputs.sha256", relative=False)
    assert hashes == {str(source): hashlib.sha256(b"actual scientific input").hexdigest()}
    nodes = provenance.read_input_inventory(original / "provenance/inputs.inventory.json")
    assert nodes[str(source)]["link_target"] == "stored.data"
    assert nodes[str(source)]["resolved_path"] == str(target)
    (tmp_path / "second/nested").mkdir(parents=True)
    (tmp_path / "second/stored.data").write_bytes(b"actual scientific input")
    (tmp_path / "second/reads.fastq").symlink_to("stored.data")
    (tmp_path / "route").unlink()
    (tmp_path / "route").symlink_to("second/nested", target_is_directory=True)
    with pytest.raises(ValueError, match="directory inventory changed"):
        replay_guard.verify_dependencies(original / "provenance")


def test_a_missing_parent_is_not_lexically_removed_from_an_input_route(tmp_path):
    (tmp_path / "reads.fastq").write_bytes(b"wrong decoy")
    with pytest.raises(provenance.MissingInputSource):
        provenance.snapshot_inputs([tmp_path / "missing/../reads.fastq"])


@pytest.mark.parametrize("name", ["result\nname.txt", "result\\name.txt", "result\rname.txt"])
def test_output_names_remain_distinct_in_checksums_and_verification(tmp_path, name):
    source = tmp_path / "data"
    source.write_bytes(b"fixed scientific input")
    original, replay = tmp_path / "original", tmp_path / "replay"
    original.mkdir()
    (original / name).write_bytes(b"fixed result")
    record(original, source)
    replay.mkdir()
    (replay / name).write_bytes(b"fixed result")
    (replay / "result.txt").write_bytes(b"fixed result")
    assert verify.compare(original, replay).byte_identical
    (replay / name).write_bytes(b"changed result")
    assert verify.compare(original, replay).changed == [name]


@pytest.mark.skipif(shutil.which("shasum") is None, reason="requires independent checksum tool")
@pytest.mark.parametrize("name", ["line\nfeed", "back\\slash", "unicode\u2028separator"])
def test_generated_manifest_is_verified_by_an_independent_checksum_tool(tmp_path, name):
    source = tmp_path / name
    source.write_bytes(b"independent scientific data")
    hashes, _ = provenance.snapshot_inputs([source])
    manifest = tmp_path / "inputs.sha256"
    manifest.write_text(provenance.checksum_text(hashes))
    checked = subprocess.run(["shasum", "-a", "256", "-c", str(manifest)],
                             capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.skipif(SHA256SUM is None, reason="requires a sha256sum that reads GNU escapes")
def test_carriage_return_escaping_is_verified_by_gnu_checksum_tool(tmp_path):
    source = tmp_path / "carriage\rreturn"
    source.write_bytes(b"independent scientific data")
    hashes, _ = provenance.snapshot_inputs([source])
    manifest = tmp_path / "inputs.sha256"
    manifest.write_text(provenance.checksum_text(hashes))
    checked = subprocess.run([SHA256SUM, "-c", str(manifest)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr
