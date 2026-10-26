"""Only audited output directories avoid consumed-input inspection and snapshots."""
import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from runner import orchestration, path_roles, submodule
from runner.errors import NfclawError
from runner.inputs import local_name_issues


PINNED_DESTINATIONS = [
    ("pathogensurveillance", "temp_dir", "13547eaa7345dab4ac97db49775ae8284af4113d"),
    ("pacvar", "outdir_vep_cache", "20364830237171928c79e59651142460379d1459"),
    ("rnadnavar", "outdir_cache", "8e8debdb0e7208218a4a2f852de7c741a69ca448"),
    ("rnavar", "outdir_cache", "a0e4641409eb7aed4b325e543d20577f9c08e437"),
    ("sarek", "outdir_cache", "8ccac7ad37b05dd792447763bf9671b719824587"),
]


@pytest.mark.parametrize("scheme", ["http", "https", "ftp"])
@pytest.mark.parametrize("filename", ["reads*.txt", "reads[12].txt", "reads{1,2}.txt"])
def test_http_and_ftp_schema_patterns_still_stage_literal_names(scheme, filename):
    issues = local_name_issues(f"{scheme}://host/{filename}", "file-path-pattern")
    assert any("unsafe remote input filename" in issue for issue in issues)


@pytest.mark.parametrize("scheme", ["s3", "gs", "az"])
def test_object_store_schema_patterns_remain_supported(scheme):
    assert local_name_issues(f"{scheme}://bucket/reads*.txt", "file-path-pattern") == []
    assert local_name_issues(f"{scheme}://bucket/reads*.txt", "file-path")


@pytest.mark.parametrize("scheme", ["http", "https", "ftp"])
def test_literal_transport_names_preserve_query_and_fragment_semantics(scheme):
    assert local_name_issues(f"{scheme}://host/reads%20copy.txt?sig=a&b=2#metadata",
                             "file-path-pattern") == []
    assert local_name_issues(f"{scheme}://host/reads.txt#fragment", "file-path-pattern")


@pytest.fixture
def pinned_source():
    def get(name, commit):
        path = Path(__file__).resolve().parents[1] / "pipelines" / name / "upstream"
        status = submodule.resolve_at(name, path)
        if not status.complete or not status.commit:
            pytest.skip("requires initialized pinned pipeline source")
        if status.commit != commit:
            # A release bump (auto-update) moves the pin; the runtime then keeps the directory an
            # input until path_roles.json is re-audited, so there is nothing to exercise here.
            pytest.skip(f"{name} is no longer pinned at the audited commit {commit[:12]}")
        return status
    return get


def _run(st, tmp_path, monkeypatch, overrides, *, check_only=False):
    # Keep runner validation, path resolution and real provenance intact. Only the external
    # engine/environment are replaced: these tests do not claim pipeline execution accuracy.
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *args: "test")
    monkeypatch.setattr(orchestration.execution, "run", lambda *args, **kwargs: None)
    library_entry = tmp_path / "pipelines" / st.name
    library_entry.mkdir(parents=True, exist_ok=True)
    (library_entry / "skill.md").write_text(f"---\nname: {st.name}\n---\n")
    (library_entry / "upstream").mkdir(exist_ok=True)
    return orchestration.run_pipeline(
        st.name, repo_root=tmp_path, input_path=None, outdir=tmp_path / "results",
        profile="docker", params_file=None, cli_overrides=overrides, resume=False,
        demo=True, check_only=check_only, write_provenance=True, timeout_seconds=None,
        resolved_tree=st)


@pytest.mark.parametrize("name,param,commit", PINNED_DESTINATIONS)
@pytest.mark.parametrize("check_only", [True, False])
def test_pinned_output_destination_ignores_unrelated_unsafe_children(
        pinned_source, tmp_path, monkeypatch, name, param, commit, check_only):
    st = pinned_source(name, commit)
    dest = tmp_path / "safe_destination"
    dest.mkdir()
    (dest / "unrelated$(id).txt").write_text("old output")
    (dest / "broken-link").symlink_to(tmp_path / "absent")
    result = _run(st, tmp_path, monkeypatch, {param: str(dest)}, check_only=check_only)
    params = json.loads((result.staging / "params.json" if check_only else
                         result.outdir / "provenance/params.json").read_text())
    assert params[param] == str(dest)
    if check_only:
        assert not result.outdir.exists()
    else:
        assert str(dest) not in (result.outdir / "provenance/inputs.sha256").read_text()


@pytest.mark.parametrize("name,param,commit", PINNED_DESTINATIONS)
def test_pinned_output_destination_contents_are_not_replay_dependencies(
        pinned_source, tmp_path, monkeypatch, name, param, commit):
    st = pinned_source(name, commit)
    dest = tmp_path / "safe_destination"
    dest.mkdir()
    (dest / "old_output.txt").write_text("unrelated output")
    result = _run(st, tmp_path, monkeypatch, {param: str(dest)})
    assert str(dest) not in (result.outdir / "provenance/inputs.sha256").read_text()
    assert json.loads((result.outdir / "provenance/params.json").read_text())[param] == str(dest)


@pytest.mark.parametrize("name,param,commit", PINNED_DESTINATIONS)
def test_output_destination_basename_still_receives_literal_name_guard(
        pinned_source, tmp_path, monkeypatch, name, param, commit):
    st = pinned_source(name, commit)
    dest = tmp_path / "destination$(id)"
    dest.mkdir()
    with pytest.raises(NfclawError, match="unsafe local input filename"):
        _run(st, tmp_path, monkeypatch, {param: str(dest)}, check_only=True)
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("change",
                         ["revision", "tracked_source", "untracked_source", "schema_format"])
def test_destination_exemption_fails_closed_when_audited_source_or_schema_changes(
        pinned_source, tmp_path, monkeypatch, change):
    name, param, commit = PINNED_DESTINATIONS[0]
    original = pinned_source(name, commit)
    clone = tmp_path / "source"
    subprocess.run(["git", "clone", "--shared", "--quiet", str(original.path), str(clone)],
                   check=True)
    if change == "revision":
        subprocess.run(["git", "-C", str(clone), "-c", "user.name=Test", "-c",
                        "user.email=test@example.org", "commit", "--quiet", "--allow-empty",
                        "-m", "different unaudited revision"], check=True)
    elif change == "tracked_source":
        with (clone / "main.nf").open("a") as handle:
            handle.write("\n// unaudited change\n")
    elif change == "untracked_source":
        (clone / "unaudited.config").write_text("params.temp_dir = 'other'\n")
    else:
        load = orchestration.schema_mod.load_param_schema

        def changed_format(path):
            loaded = load(path)
            return replace(loaded, params={**loaded.params,
                           param: replace(loaded.params[param], fmt="path")})

        monkeypatch.setattr(orchestration.schema_mod, "load_param_schema", changed_format)
    st = submodule.resolve_at(name, clone)
    dest = tmp_path / "safe_destination"
    dest.mkdir()
    (dest / "unsafe$(id).txt").write_text("must be inspected")
    loaded = orchestration.schema_mod.load_param_schema(st.path)
    assert not path_roles.output_only_directories(st, loaded)
    assert any("unsafe local input filename" in issue for issue in
               orchestration.parameters.validate_params({param: str(dest)}, loaded))
    expected = ("local modifications" if change == "tracked_source"
                else "unsafe local input filename")
    with pytest.raises(NfclawError, match=expected):
        _run(st, tmp_path, monkeypatch, {param: str(dest)}, check_only=True)
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("evidence", ["missing_registry", "invalid_registry", "failed_git_status",
                                     "non_git_source", "wrong_pipeline"])
def test_unverifiable_destination_roles_restore_input_checks(
        pinned_source, tmp_path, monkeypatch, evidence):
    name, param, commit = PINNED_DESTINATIONS[0]
    st = pinned_source(name, commit)
    if evidence in {"missing_registry", "invalid_registry"}:
        registry = tmp_path / "registry.json"
        if evidence == "invalid_registry":
            registry.write_text("{invalid JSON")
        monkeypatch.setattr(path_roles, "_REGISTRY", registry)
    elif evidence == "failed_git_status":
        capture = path_roles.capture

        def failed_status(args, *args_other, **kwargs):
            if args[:2] == ["git", "status"]:
                raise subprocess.CalledProcessError(1, args)
            return capture(args, *args_other, **kwargs)

        monkeypatch.setattr(path_roles, "capture", failed_status)
    elif evidence == "non_git_source":
        source = tmp_path / "source"
        source.mkdir()
        st = replace(st, path=source)
    else:
        st = replace(st, name="another_pipeline")
    loaded = orchestration.schema_mod.load_param_schema(
        pinned_source(name, commit).path)
    roles = path_roles.output_only_directories(st, loaded)
    dest = tmp_path / "destination"
    dest.mkdir()
    (dest / "unsafe$(id).txt").write_text("must be inspected")
    issues = orchestration.parameters.validate_params({param: str(dest)}, loaded,
                                                       output_only_dirs=roles)
    assert any("unsafe local input filename" in issue for issue in issues)


@pytest.mark.parametrize("name,param,commit", [
    ("sarek", "bwa", "8ccac7ad37b05dd792447763bf9671b719824587"),
    ("ampliseq", "ref_taxonomy_storage", "992e6df34065067185b5e34665b5861b6827981d"),
])
def test_scientific_cache_remains_inspected_and_snapshotted(
        pinned_source, tmp_path, monkeypatch, name, param, commit):
    st = pinned_source(name, commit)
    cache = tmp_path / "reference_cache"
    cache.mkdir()
    data = cache / "cache.bin"
    data.write_bytes(b"scientific reference")
    result = _run(st, tmp_path, monkeypatch, {param: str(cache)})
    snapshot = (result.outdir / "provenance/inputs.sha256").read_text()
    assert f"{hashlib.sha256(b'scientific reference').hexdigest()}  {data}" in snapshot
    (cache / "unsafe$(id).bin").write_text("unsafe reference")
    with pytest.raises(NfclawError, match="unsafe local input filename"):
        _run(st, tmp_path, monkeypatch, {param: str(cache)}, check_only=True)


@pytest.mark.parametrize("parent_name", ["parent with spaces", "parent$(printf expanded)"])
@pytest.mark.parametrize("via_alias", [False, True])
def test_unquoted_temporary_directory_arguments_validate_full_paths(
        pinned_source, tmp_path, monkeypatch, parent_name, via_alias):
    name, param, commit = PINNED_DESTINATIONS[0]
    st = pinned_source(name, commit)
    physical = tmp_path / parent_name / "temporary"
    physical.mkdir(parents=True)
    supplied = physical
    if via_alias:
        supplied = tmp_path / "safe_alias"
        supplied.symlink_to(physical, target_is_directory=True)
    with pytest.raises(NfclawError, match="unsafe local input path"):
        _run(st, tmp_path, monkeypatch, {param: str(supplied)}, check_only=True)
    assert not (tmp_path / "results").exists()
