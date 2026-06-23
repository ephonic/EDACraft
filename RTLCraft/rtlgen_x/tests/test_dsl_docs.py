from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_dsl_support_docs_exist_and_describe_public_boundary():
    root = _repo_root()
    support = root / "rtlgen_x" / "DSL_SUPPORT_MATRIX.md"
    semantics = root / "rtlgen_x" / "DSL_SEMANTICS.md"

    assert support.exists()
    assert semantics.exists()

    support_text = support.read_text(encoding="utf-8")
    semantics_text = semantics.read_text(encoding="utf-8")

    assert "DSL `Module`" in support_text
    assert "LoweredDslModule" in support_text
    assert "raw `SimModule`" in support_text
    assert "public verify, PPA, and UVM APIs" in support_text
    assert "ClockDomainSpec" in support_text
    assert "ResetDomainSpec" in support_text

    assert "one public authoring surface" in semantics_text
    assert "Public verify, PPA, and UVM APIs are DSL-facing" in semantics_text
    assert "reject raw `SimModule`" in semantics_text
    assert "clock_domain(...)" in semantics_text
    assert "seq_domain(...)" in semantics_text


def test_readme_links_dsl_support_docs():
    root = _repo_root()
    readme = (root / "rtlgen_x" / "README.md").read_text(encoding="utf-8")

    assert "./DSL_SUPPORT_MATRIX.md" in readme
    assert "./DSL_SEMANTICS.md" in readme
