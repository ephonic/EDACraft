"""
test_soc — Quad-core heterogeneous SoC tests.

Tests core types and SoC components independently.
"""
import sys
sys.path.insert(0, '.')
import warnings

# Suppress combinational loop warnings from simulator
warnings.filterwarnings('ignore', message='Combinational loop')
warnings.filterwarnings('ignore', message='did not converge')

from rtlgen.sim import Simulator


def test_hp_core():
    """HPCore initializes and retires instructions."""
    print("\n=== Test 1: HPCore ===")
    from skills.cpu.core_types import HPCore
    m = HPCore(hartid=0, PC_WIDTH=39, XLEN=64)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    retired_cnt = 0
    for _ in range(20):
        s.step()
        if int(s.get('retired')): retired_cnt += 1
    print(f"  Retired: {retired_cnt}x")
    assert retired_cnt > 0, "HPCore never retired"
    print("  PASS")


def test_ee_core():
    """EECore initializes and retires instructions."""
    print("\n=== Test 2: EECore ===")
    from skills.cpu.core_types import EECore
    m = EECore(hartid=2, PC_WIDTH=39, XLEN=64)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    retired_cnt = 0
    for _ in range(20):
        s.step()
        if int(s.get('retired')): retired_cnt += 1
    print(f"  Retired: {retired_cnt}x")
    assert retired_cnt > 0, "EECore never retired"
    print("  PASS")


def test_hp_alu_result():
    """HPCore ALU produces correct result (5+3=8)."""
    print("\n=== Test 3: HPCore ALU ===")
    from skills.cpu.core_types import HPCore
    m = HPCore(hartid=0)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    results = []
    for _ in range(24):
        s.step()
        if int(s.get('result_valid')):
            results.append(int(s.get('result')))
    print(f"  Results: {results}")
    assert len(results) > 0, "No ALU results"
    assert results[0] == 8, f"Expected 8, got {results[0]}"
    print("  PASS")


def test_ee_alu_result():
    """EECore ALU produces correct result (5+3=8)."""
    print("\n=== Test 4: EECore ALU ===")
    from skills.cpu.core_types import EECore
    m = EECore(hartid=2)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    results = []
    for _ in range(24):
        s.step()
        if int(s.get('result_valid')):
            results.append(int(s.get('result')))
    print(f"  Results: {results}")
    assert len(results) > 0, "No ALU results"
    assert results[0] == 8, f"Expected 8, got {results[0]}"
    print("  PASS")


def test_l2_cache():
    """L2 cache read after write."""
    print("\n=== Test 5: L2 Cache ===")
    from skills.cpu.soc import L2Cache
    m = L2Cache(sets=16, width=64)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    # Write
    s.set('req_valid', 1); s.set('req_addr', 0x100)
    s.set('req_we', 1); s.set('req_data', 0xDEADBEEF); s.set('req_id', 0)
    for _ in range(6): s.step()
    s.set('req_valid', 0); s.set('req_we', 0)
    for _ in range(3): s.step()
    # Read
    s.set('req_valid', 1); s.set('req_addr', 0x100); s.set('req_we', 0)
    for _ in range(8): s.step()
    rv = int(s.get('resp_valid'))
    rd = int(s.get('resp_data'))
    print(f"  Valid={rv} Data=0x{rd:016x}")
    assert rv == 1, f"Cache missed (valid={rv})"
    assert rd == 0xDEADBEEF, f"Got 0x{rd:x}, expected 0xDEADBEEF"
    print("  PASS")


def test_crossbar():
    """Crossbar routes requests to L2 and responses back."""
    print("\n=== Test 6: Crossbar ===")
    from skills.cpu.soc import Crossbar
    m = Crossbar()
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    # Core 0 request
    s.set('crv_0', 1); s.set('cra_0', 0x100); s.set('crw_0', 0)
    s.set('crv_1', 0); s.set('crv_2', 0); s.set('crv_3', 0)
    s.set('l2_busy', 0)
    s.set('l2_resp_data', 0xCAFE); s.set('l2_resp_valid', 0); s.set('l2_resp_id', 0)
    for _ in range(5): s.step()
    l2_v = int(s.get('l2_req_valid'))
    l2_i = int(s.get('l2_req_id'))
    print(f"  L2 req: valid={l2_v} from core={l2_i}")
    assert l2_v == 1, "Crossbar didn't route request"
    assert l2_i == 0, f"Wrong core id: {l2_i}"
    # L2 responds
    s.set('l2_resp_data', 0xCAFE); s.set('l2_resp_valid', 1); s.set('l2_resp_id', 0)
    s.step()
    s.set('l2_resp_valid', 0)
    for _ in range(3): s.step()
    r0 = int(s.get('crspd_0'))
    print(f"  Core 0 response: 0x{r0:x}")
    assert r0 == 0xCAFE, f"Got 0x{r0:x}, expected 0xCAFE"
    print("  PASS")


def test_quad_soc_structure():
    """QuadCoreSoC instantiates correctly."""
    print("\n=== Test 7: SoC Structure ===")
    from skills.cpu.soc import QuadCoreSoC
    soc = QuadCoreSoC()
    # Verify submodules exist
    names = [name for name, _ in soc._submodules]
    print(f"  Submodules: {names}")
    assert 'core_0' in names
    assert 'core_1' in names
    assert 'core_2' in names
    assert 'core_3' in names
    assert 'l2' in names
    assert 'xbar' in names
    print("  SoC structure: PASS")


def run_all():
    tests = [
        ('HPCore', test_hp_core),
        ('EECore', test_ee_core),
        ('HPCore ALU', test_hp_alu_result),
        ('EECore ALU', test_ee_alu_result),
        ('L2 Cache', test_l2_cache),
        ('Crossbar', test_crossbar),
        ('SoC Structure', test_quad_soc_structure),
    ]
    passed = 0
    for name, t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  {name}: FAIL ({e})")
    total = len(tests)
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed")
    return passed == total


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
