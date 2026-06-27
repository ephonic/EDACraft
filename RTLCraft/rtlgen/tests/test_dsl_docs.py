from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_dsl_support_docs_exist_and_describe_public_boundary():
    root = _repo_root()
    support = root / "rtlgen" / "DSL_SUPPORT_MATRIX.md"
    semantics = root / "rtlgen" / "DSL_SEMANTICS.md"
    readability = root / "rtlgen" / "RTL_READABILITY_CONTRACT.md"

    assert support.exists()
    assert semantics.exists()
    assert readability.exists()

    support_text = support.read_text(encoding="utf-8")
    semantics_text = semantics.read_text(encoding="utf-8")
    readability_text = readability.read_text(encoding="utf-8")

    assert "DSL `Module`" in support_text
    assert "LoweredDslModule" in support_text
    assert "raw `SimModule`" in support_text
    assert "public verify, PPA, and UVM APIs" in support_text
    assert "ClockDomainSpec" in support_text
    assert "ResetDomainSpec" in support_text
    assert "Foundation contract preflight" in support_text
    assert "Unified diagnostics report" in support_text

    assert "one public authoring surface" in semantics_text
    assert "Public verify, PPA, and UVM APIs are DSL-facing" in semantics_text
    assert "reject raw `SimModule`" in semantics_text
    assert "clock_domain(...)" in semantics_text
    assert "seq_domain(...)" in semantics_text
    assert "Foundation contract gate" in semantics_text
    assert "Diagnostic report contract" in semantics_text
    assert "Readable RTL contract" in semantics_text

    assert "Review RTL" in readability_text
    assert "Gate Boundary" in readability_text


def test_readme_links_dsl_support_docs():
    root = _repo_root()
    readme = (root / "rtlgen" / "README.md").read_text(encoding="utf-8")

    assert "./DSL_SUPPORT_MATRIX.md" in readme
    assert "./DSL_SEMANTICS.md" in readme
    assert "./RTL_READABILITY_CONTRACT.md" in readme
    assert "Foundation Contract Gate" in readme
