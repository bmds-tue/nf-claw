from librarian import discover_pipelines as dp

# A trimmed shape of nf-co.re/pipelines.json -> remote_workflows.
WORKFLOWS = [
    {
        "name": "rnaseq",
        "full_name": "nf-core/rnaseq",
        "archived": False,
        "releases": [{"tag_name": "dev"}, {"tag_name": "3.14.0"}, {"tag_name": "3.26.0"}],
    },
    {
        "name": "abotyper",
        "full_name": "nf-core/abotyper",
        "archived": False,
        "releases": [{"tag_name": "dev"}],  # no stable release -> skipped
    },
    {
        "name": "oldpipe",
        "full_name": "nf-core/oldpipe",
        "archived": True,  # archived -> skipped even with a release
        "releases": [{"tag_name": "1.0.0"}],
    },
    {
        "name": "demo",
        "full_name": "nf-core/demo",
        "archived": False,
        "releases": [{"tag_name": "v1.2.0"}, {"tag_name": "1.0.0"}],
    },
    {
        "name": "clipseq",
        "full_name": "nf-core/clipseq",
        "archived": False,
        "is_DSL2": False,  # DSL1 -> not runnable on a modern Nextflow, must be skipped
        "releases": [{"tag_name": "1.0.0"}],
    },
    {
        "name": "../bad",
        "full_name": "nf-core/bad",
        "archived": False,
        "releases": [{"tag_name": "1.0.0"}],
    },
]


def test_latest_stable_picks_highest_semver_ignoring_dev():
    assert dp.latest_stable(WORKFLOWS[0]["releases"]) == "3.26.0"
    assert dp.latest_stable([{"tag_name": "dev"}]) is None
    assert dp.latest_stable([{"tag_name": "1.0.0-rc1"}]) is None  # pre-release ignored


def test_candidates_filters_archived_dsl1_releaseless_and_builds_url():
    cands = dp.candidates(WORKFLOWS)
    names = [c[0] for c in cands]
    # sorted; abotyper (no release) + oldpipe (archived) + clipseq (DSL1) + bad name dropped
    assert names == ["demo", "rnaseq"]
    assert ("demo", "https://github.com/nf-core/demo.git", "v1.2.0") in cands
    assert ("rnaseq", "https://github.com/nf-core/rnaseq.git", "3.26.0") in cands


def test_candidates_never_trusts_non_nfcore_full_name():
    workflows = [{
        "name": "demo",
        "full_name": "attacker/demo",
        "archived": False,
        "releases": [{"tag_name": "1.0.0"}],
    }]
    assert dp.candidates(workflows) == [
        ("demo", "https://github.com/nf-core/demo.git", "1.0.0")
    ]


def test_new_pipelines_excludes_already_tracked():
    fresh = dp.new_pipelines(WORKFLOWS, existing={"rnaseq"})
    assert [c[0] for c in fresh] == ["demo"]


def test_discovery_reports_partial_addition_failure_and_attempts_every_candidate(tmp_path, monkeypatch):
    sources = tmp_path / "sources.tsv"
    sources.write_text("")
    monkeypatch.setattr(dp, "fetch_catalog", lambda: WORKFLOWS)
    calls = []
    def add(name, *args):
        calls.append(name)
        return name == "rnaseq"
    monkeypatch.setattr(dp, "add_one", add)
    assert dp.main(["--repo-root", str(tmp_path), "--limit", "0"]) == 1
    assert calls == ["demo", "rnaseq"]
    assert sources.read_text() == "rnaseq\thttps://github.com/nf-core/rnaseq.git\tlatest-release\n"


def test_append_source_writes_tab_separated_row(tmp_path):
    src = tmp_path / "sources.tsv"
    src.write_text("# name\turl\tpolicy\nrnaseq\thttps://x\tlatest-release\n", encoding="utf-8")
    dp._append_source(src, "demo", "https://github.com/nf-core/demo.git")
    rows = [line for line in src.read_text().splitlines() if line and not line.startswith("#")]
    assert rows[-1] == "demo\thttps://github.com/nf-core/demo.git\tlatest-release"


def test_remove_source_drops_only_that_row(tmp_path):
    src = tmp_path / "sources.tsv"
    src.write_text(
        "# name\turl\tpolicy\n"
        "rnaseq\thttps://x/rnaseq.git\tlatest-release\n"
        "demo\thttps://x/demo.git\tlatest-release\n",
        encoding="utf-8",
    )
    dp._remove_source(src, "demo")
    rows = [line for line in src.read_text().splitlines() if line and not line.startswith("#")]
    assert rows == ["rnaseq\thttps://x/rnaseq.git\tlatest-release"]
