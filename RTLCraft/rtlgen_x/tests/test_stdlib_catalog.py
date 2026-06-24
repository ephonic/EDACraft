from rtlgen_x.stdlib_catalog import (
    STDLIB_CATALOG,
    StdlibEntry,
    emit_stdlib_support_matrix_markdown,
    get_stdlib_entry,
    list_stdlib_entries,
)
from pathlib import Path
from rtlgen_x.verify import get_stdlib_entry as verify_get_stdlib_entry
from rtlgen_x.verify import list_stdlib_entries as verify_list_stdlib_entries


def test_get_stdlib_entry_accepts_normalized_names_across_kinds():
    assert get_stdlib_entry("ready_valid").name == "ReadyValid"
    assert get_stdlib_entry("apbregisterbank").name == "APBRegisterBank"
    assert get_stdlib_entry("wishbone_clocked_vip").name == "WishboneClockedVIP"


def test_list_stdlib_entries_filters_by_kind_and_status():
    protocols = list_stdlib_entries(kind="protocol")
    components = list_stdlib_entries(kind="component")
    vips = list_stdlib_entries(kind="vip")
    partials = list_stdlib_entries(status="partial")

    assert "APB" in protocols
    assert "APBRegisterBank" in components
    assert "APBVIP" in vips
    assert "APBRegisterBank" in partials
    assert all(entry.kind == "protocol" for entry in protocols.values())
    assert all(entry.kind == "component" for entry in components.values())
    assert all(entry.kind == "vip" for entry in vips.values())
    assert all(entry.status == "partial" for entry in partials.values())


def test_stdlib_catalog_is_exposed_as_entry_mapping():
    assert "apbregisterbank" in STDLIB_CATALOG
    assert isinstance(STDLIB_CATALOG["apbregisterbank"], StdlibEntry)
    assert STDLIB_CATALOG["apbregisterbank"].related == ("APB", "APBVIP")


def test_emit_stdlib_support_matrix_markdown_includes_core_sections():
    text = emit_stdlib_support_matrix_markdown()

    assert "# rtlgen_x Stdlib Support Matrix" in text
    assert "## Protocol entries" in text
    assert "## Component entries" in text
    assert "## Vip entries" in text
    assert "`APBRegisterBank`" in text
    assert "`WishboneClockedVIP`" in text
    assert "| Entry | Family | Status | DSL | Lowering | Python sim | C++ sim | Emitted RTL | Readable RTL |" in text


def test_stdlib_catalog_exposes_readable_rtl_dimension_and_new_component_entries():
    mac = get_stdlib_entry("MAC")
    mult = get_stdlib_entry("SignedMultiplier")
    regfile = get_stdlib_entry("RegisterFile")

    assert mac.kind == "component"
    assert mult.support.readable_rtl == "yes"
    assert regfile.support.emitted_rtl == "yes"
    assert regfile.support.readable_rtl == "yes"


def test_get_stdlib_entry_reports_known_entries_on_error():
    try:
        get_stdlib_entry("no_such_stdlib_entry")
    except KeyError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected KeyError for unknown stdlib entry")

    assert "Known entries" in text
    assert "ReadyValid" in text
    assert "APBRegisterBank" in text


def test_stdlib_support_matrix_doc_matches_catalog_generator():
    repo_root = Path(__file__).resolve().parents[2]
    matrix_path = repo_root / "rtlgen_x" / "STDLIB_SUPPORT_MATRIX.md"

    assert matrix_path.read_text() == emit_stdlib_support_matrix_markdown()


def test_verify_package_reexports_stdlib_catalog_queries():
    assert verify_get_stdlib_entry("apbvip").name == "APBVIP"
    assert "APBRegisterBank" in verify_list_stdlib_entries(kind="component")
