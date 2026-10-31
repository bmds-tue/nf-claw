import pytest

from runner import resources
from runner.errors import NfclawError


def test_config_is_a_nextflow_resource_limits_block():
    text = resources.parse(4, "15.GB", "1.h").config_text()
    assert "process {" in text and "resourceLimits = [" in text
    assert "cpus: 4," in text                       # an int, unquoted — Nextflow expects a number
    assert "memory: '15.GB'," in text               # a quoted MemoryUnit string
    assert "time: '1.h'" in text                    # last entry: no trailing comma (Groovy list)


def _limits_block(text: str) -> str:
    """Just the resourceLimits entries — the comment header names all three flags."""
    return text.split("resourceLimits = [", 1)[1].split("]", 1)[0]


def test_only_the_limits_given_are_written():
    # A ceiling on one dimension must not silently invent one for the others.
    block = _limits_block(resources.parse(None, "15.GB", None).config_text())
    assert "memory: '15.GB'" in block
    assert "cpus" not in block and "time" not in block


def test_empty_when_nothing_is_capped():
    assert resources.parse(None, None, None).is_empty()


# Measured on Nextflow 26.04.3 (`new nextflow.util.MemoryUnit(s)`, `nextflow.util.Duration.of(s)`,
# and a run whose generated resourceLimits holds the value): each of these parses.
@pytest.mark.parametrize("value", ["15.GB", "15 GB", "16GB", "512.MB", "1.5TB", "1.5 TB",
                                   "100.KB", "100 B", "100B", "15.gB", "15  GB"])
def test_accepts_nextflow_memory_spellings(value):
    assert resources.parse(None, value, None).memory == value


@pytest.mark.parametrize("value", ["1.h", "90.min", "2.d", "30 s", "1h", "24.hours", "1.5h",
                                   "1.5 h", "10.ms", "10.millis", "5.sec", "5.seconds", "1day"])
def test_accepts_nextflow_duration_spellings(value):
    assert resources.parse(None, None, value).time == value


# ... and Nextflow refuses each of these, at the first task when it is a ceiling ("Error executing
# process > ... Caused by: multiple points"): accepting them deferred the failure past --check, and
# in a chain past every stage before this one.
@pytest.mark.parametrize("value", ["1.5.TB", "0.5.GB", "100.B", "15.5B", "15.gb", "15 gb",
                                   "15 . GB", "15.Gb", "15.KiB", "\u0661\u0665.GB"])
def test_rejects_memory_spellings_nextflow_refuses(value):
    with pytest.raises(NfclawError, match="--limit-memory"):
        resources.parse(None, value, None)


@pytest.mark.parametrize("value", ["5.secs", "5.mins", "1.H", "5.MIN", "1.Day", "5.Second",
                                   "1 . h", "1.5.h", ".5h", "1.hr", "\u0661.h"])
def test_rejects_duration_spellings_nextflow_refuses(value):
    with pytest.raises(NfclawError, match="--limit-time"):
        resources.parse(None, None, value)


@pytest.mark.parametrize("value", ["15 gigs", "lots", "15", "GB", "15.GB; rm -rf /"])
def test_rejects_a_value_nextflow_could_not_parse(value):
    # Fail fast, naming the flag — better than the engine dying at the first task. This also means
    # no unvalidated text can reach the generated Groovy config.
    with pytest.raises(NfclawError, match="--limit-memory"):
        resources.parse(None, value, None)


@pytest.mark.parametrize("value", ["1 fortnight", "soon", "1.hh", "h"])
def test_rejects_a_duration_nextflow_could_not_parse(value):
    with pytest.raises(NfclawError, match="--limit-time"):
        resources.parse(None, None, value)


def test_rejects_a_non_positive_cpu_count():
    with pytest.raises(NfclawError, match="--limit-cpus"):
        resources.parse(0, None, None)


def test_write_config_creates_the_file_and_parent(tmp_path):
    dest = tmp_path / "provenance" / "resource_limits.config"
    written = resources.write_config(resources.parse(4, "15.GB", "1.h"), dest)
    assert written == dest and "resourceLimits" in dest.read_text()


@pytest.mark.parametrize("value", ["25.10.4", "26.04.3", "25.10.0-edge"])
def test_accepts_a_full_nextflow_version(value):
    assert resources.check_nxf_version(value) == value


@pytest.mark.parametrize("value", ["25.10", "25.10.4-rc1", "latest", "٢٥.١٠.٤",
                                   "25.10.4\n"])
def test_refuses_what_the_nextflow_launcher_cannot_download(value):
    # Python's `\d` matches every script's digits; NXF_VER must be the launcher's ASCII version.
    with pytest.raises(NfclawError, match="--nxf-ver"):
        resources.check_nxf_version(value)
