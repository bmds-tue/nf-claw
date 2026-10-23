import os
import pathlib
import subprocess
from pathlib import Path

import pytest

from runner import preflight
from runner.submodule import SubmoduleStatus


def _st(path, complete=True):
    return SubmoduleStatus("sarek", path, True, complete, "3.8.1", "abc",
                           () if complete else ("main.nf",))


def test_outdir_inside_repo_flagged(tmp_path, monkeypatch):
    # Inside the repo and NOT gitignored (tmp_path isn't even a git repo) → rejected.
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    inside = tmp_path / "results"
    issues = preflight.check_environment(profile="singularity", output_dir=inside,
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path, resume=False)
    assert any("outside the repo" in i for i in issues)


def test_outdir_gitignored_in_repo_allowed(tmp_path, monkeypatch):
    # A gitignored outdir (the documented `--outdir results`) is allowed inside the repo.
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("results/\n")
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "results",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path, resume=False)
    assert not any("outdir" in i for i in issues)


def test_missing_nextflow_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda x: None)
    issues = preflight.check_environment(profile="docker",
                                         output_dir=tmp_path.parent / "out_xyz",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path, resume=False)
    assert any("nextflow not found" in i for i in issues)


def _clean_env(monkeypatch):
    # tools present, docker daemon healthy — isolate the space check from unrelated issues
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(preflight, "capture",
                        lambda *a, **k: type("R", (), {"returncode": 0})())


def test_space_in_repo_path_blocks(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    spaced = tmp_path / "draft 2"
    spaced.mkdir()
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "out_x",
                                         submodule=_st(spaced / "up"), repo_root=spaced,
                                         resume=False)
    assert any("repo path" in i and "space" in i and "--allow-spaces" in i for i in issues)


def test_space_in_outdir_blocks(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "a b" / "out",
                                         submodule=_st(tmp_path / "up"), repo_root=tmp_path,
                                         resume=False)
    assert any("--outdir" in i and "space" in i for i in issues)


def test_space_in_work_dir_blocks(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "out_x",
                                         submodule=_st(tmp_path / "up"), repo_root=tmp_path,
                                         resume=False, work_dir=Path("/scratch dir/work"))
    assert any("work directory" in i and "NXF_WORK" in i for i in issues)


def test_allow_spaces_overrides_the_block(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    spaced = tmp_path / "draft 2"
    spaced.mkdir()
    issues = preflight.check_environment(profile="singularity", output_dir=spaced / "out",
                                         submodule=_st(spaced / "up"), repo_root=spaced,
                                         resume=False, work_dir=Path("/x y/work"),
                                         allow_spaces=True)
    assert not any("space" in i for i in issues)


def test_nonempty_outdir_blocks_run_but_not_check(tmp_path, monkeypatch):
    # The non-empty-outdir guard protects an actual run from clobbering prior results; it must not
    # block `--check`, which only validates params and prints the command without launching.
    _clean_env(monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"  # outside the repo, so only the empty rule can fire
    out.mkdir()
    (out / "old.txt").write_text("a previous run")
    common = dict(profile="singularity", submodule=_st(repo / "up"),
                  repo_root=repo, resume=False, output_dir=out)
    assert any("--outdir is not empty" in i for i in preflight.check_environment(**common))
    assert not any("not empty" in i
                   for i in preflight.check_environment(**common, check_only=True))


def test_nonempty_outdir_hint_names_nfclaws_resume_flag(tmp_path, monkeypatch):
    # The hint said "use -resume", but `nfclaw run ... -resume` is rejected as an unexpected extra
    # argument — nfclaw's flag is `--resume`.
    _clean_env(monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "old.txt").write_text("a previous run")
    issues = preflight.check_environment(profile="singularity", submodule=_st(repo / "up"),
                                         repo_root=repo, resume=False, output_dir=out)
    hint = next(i for i in issues if "not empty" in i)
    assert "--resume" in hint and " -resume" not in hint


def test_outdir_that_is_a_file_is_flagged_cleanly(tmp_path, monkeypatch):
    # An --outdir pointing at an existing file must be reported clearly, not blow up later in
    # iterdir()/mkdir() with an uncaught NotADirectoryError/FileExistsError.
    _clean_env(monkeypatch)
    f = tmp_path / "afile"
    f.write_text("x")
    issues = preflight.check_environment(profile="singularity", output_dir=f,
                                         submodule=_st(tmp_path / "up"), repo_root=tmp_path,
                                         resume=False, check_only=True)
    assert any("not a directory" in i for i in issues)


def test_no_spaces_no_block(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "out_x",
                                         submodule=_st(tmp_path / "up"), repo_root=tmp_path,
                                         resume=False, work_dir=tmp_path / "work")
    assert not any("space" in i for i in issues)


def test_outdir_that_cannot_be_written_is_flagged(tmp_path, monkeypatch):
    # `--outdir /data/results` under a directory the caller cannot write failed with a raw
    # PermissionError once nfclaw tried to create it. (os.access is stubbed: tests may run as root.)
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    locked = tmp_path / "data"
    locked.mkdir()
    real_access = os.access
    monkeypatch.setattr(preflight.os, "access",
                        lambda p, mode: False if Path(p) == locked else real_access(p, mode))

    def issues_for(out):
        return preflight.check_environment(profile="singularity", output_dir=out,
                                           submodule=_st(tmp_path / "up"),
                                           repo_root=tmp_path / "repo", resume=False,
                                           check_only=True)
    # Not yet created: judged on the nearest existing ancestor, however deep the new path is.
    assert any(f"cannot be created: {locked} is not writable" in i
               for i in issues_for(locked / "results" / "run1"))
    assert any(f"--outdir is not writable: {locked}" in i for i in issues_for(locked))
    assert not any("writ" in i for i in issues_for(tmp_path / "fine" / "results"))


def test_outdir_under_a_file_is_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    (tmp_path / "notes.txt").write_text("x")
    issues = preflight.check_environment(profile="singularity",
                                         output_dir=tmp_path / "notes.txt" / "results",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path / "repo", resume=False)
    assert any("notes.txt is not a directory" in i for i in issues)


def test_outdir_under_an_unsearchable_directory_is_flagged_not_crashed(tmp_path, monkeypatch):
    # `--outdir /root/x` as another user: Path.exists()/is_dir() raise PermissionError there rather
    # than answer, which escaped preflight as a traceback.
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    locked = tmp_path / "locked"
    real_stat = pathlib.Path.stat

    def stat(self, *a, **k):
        if self.is_relative_to(locked) and self != locked:
            raise PermissionError(13, "Permission denied", str(self))
        return real_stat(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "stat", stat)
    issues = preflight.check_environment(profile="singularity", output_dir=locked / "x" / "out",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path / "repo", resume=False)
    assert any("--outdir cannot be reached: Permission denied" in i for i in issues), issues


def test_unwritable_work_dir_is_flagged_with_the_nxf_work_fix(tmp_path, monkeypatch):
    # The default work dir, <repo>/work, belongs to whoever ran first: on a shared clone the next
    # user's run failed inside Nextflow. (os.access is stubbed: tests may run as root.)
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    work = tmp_path / "repo" / "work"
    work.mkdir(parents=True)
    real_access = os.access
    monkeypatch.setattr(preflight.os, "access",
                        lambda p, mode: False if Path(p) == work else real_access(p, mode))
    issues = preflight.check_environment(profile="singularity", output_dir=tmp_path / "out",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path / "repo",
                                         resume=False, work_dir=work)
    assert any("work directory is not writable" in i and "NXF_WORK" in i for i in issues), issues
    fine = preflight.check_environment(profile="singularity", output_dir=tmp_path / "out",
                                       submodule=_st(tmp_path / "up"), repo_root=tmp_path / "repo",
                                       resume=False, work_dir=tmp_path / "elsewhere" / "work")
    assert not any("work directory" in i for i in fine), fine


# LF and CR can become separate shell lines in generated Nextflow scripts. The space override
# must not authorize them in launch paths.
@pytest.mark.parametrize("separator", ["\n", "\r"])
@pytest.mark.parametrize("allow_spaces", [False, True])
def test_launch_path_line_breaks_are_refused_even_with_the_space_override(tmp_path,
                                                                          separator, allow_spaces):
    for field in ("repo_root", "output_dir", "work_dir"):
        paths = {"repo_root": tmp_path / "repo", "output_dir": tmp_path / "out",
                 "work_dir": tmp_path / "work"}
        paths[field] = tmp_path / f"parent{separator}next" / field
        assert any("line break" in issue for issue in preflight._space_issues(
            **paths, allow_spaces=allow_spaces))


@pytest.mark.parametrize("profile,present,expected", [
    ("apptainer,test", set(), "profile uses apptainer but apptainer/singularity not found"),
    ("podman", set(), "profile uses podman but podman not found"),
    ("conda", set(), "profile uses conda but conda/mamba/micromamba not found"),
    ("charliecloud", set(), "profile uses charliecloud but ch-run not found"),
    ("apptainer", {"singularity"}, None),          # Apptainer's `singularity` alias serves it
    ("mamba", {"micromamba"}, None),
    ("test,docker", {"docker"}, None),
])
def test_every_engine_profile_needs_its_engine(tmp_path, monkeypatch, profile, present, expected):
    # A missing engine otherwise only surfaces once Nextflow starts the first task.
    base = {"git", "nextflow", "java"}
    monkeypatch.setattr(preflight.shutil, "which",
                        lambda x: "/usr/bin/" + x if x in base | present else None)
    monkeypatch.setattr(preflight, "capture",
                        lambda *a, **k: type("R", (), {"returncode": 0})())
    issues = preflight.check_environment(profile=profile, output_dir=tmp_path.parent / "out_eng",
                                         submodule=_st(tmp_path / "up"),
                                         repo_root=tmp_path, resume=False)
    engine_issues = [i for i in issues if i.startswith("profile uses")]
    assert engine_issues == ([expected + " on PATH"] if expected else [])
