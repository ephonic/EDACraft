#!/usr/bin/env python3
import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")
from rtlgen import Simulator
from examples.sha3_256_pipe import KeccakRound, RC

def get_arr(sim, name, depth):
    st = sim.state.get(name, {})
    return [int(st.get(i, 0)) & ((1<<64)-1) for i in range(depth)]

def test():
    dut = KeccakRound()
    sim = Simulator(dut)
    sim.set("rst_n", 0); sim.set("i_valid", 0); sim.set("o_ready", 1); sim.step()
    sim.set("rst_n", 1); sim.step()
    import random; random.seed(42)
    lanes = [random.getrandbits(64) for _ in range(25)]
    state_int = sum(l << (i*64) for i,l in enumerate(lanes))
    sim.set("state_in", state_int); sim.set("round_idx", 0); sim.set("i_valid", 1); sim.step()

    hw_a = get_arr(sim, "a", 25)
    if hw_a != lanes:
        print("a mismatch"); return
    print("a OK")

    hw_c = get_arr(sim, "c", 5)
    ref_c = [lanes[x] ^ lanes[x+5] ^ lanes[x+10] ^ lanes[x+15] ^ lanes[x+20] for x in range(5)]
    if hw_c != ref_c:
        print("c mismatch"); return
    print("c OK")

    def rotl(v, n):
        n %= 64
        return ((v << n) & ((1<<64)-1)) | (v >> (64-n))
    hw_d = get_arr(sim, "d", 5)
    ref_d = [ref_c[(x-1)%5] ^ rotl(ref_c[(x+1)%5], 1) for x in range(5)]
    if hw_d != ref_d:
        print("d mismatch"); return
    print("d OK")

    hw_a_theta = get_arr(sim, "a_theta", 25)
    ref_a_theta = [lanes[i] ^ ref_d[i%5] for i in range(25)]
    if hw_a_theta != ref_a_theta:
        print("a_theta mismatch"); return
    print("a_theta OK")

    # Rho+Pi reference
    ROT_OFFSETS = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14],
    ]
    ref_b = [0]*25
    for x in range(5):
        for y in range(5):
            idx = x + 5*y
            new_x = y
            new_y = (2*x + 3*y) % 5
            new_idx = new_x + 5*new_y
            ref_b[new_idx] = rotl(ref_a_theta[idx], ROT_OFFSETS[x][y])
    hw_b = get_arr(sim, "b_rhopi", 25)
    if hw_b != ref_b:
        print("b_rhopi mismatch"); return
    print("b_rhopi OK")

    # Chi reference
    ref_a_chi = [0]*25
    for x in range(5):
        for y in range(5):
            idx = x + 5*y
            xp1 = (x+1)%5
            xp2 = (x+2)%5
            idx1 = xp1 + 5*y
            idx2 = xp2 + 5*y
            ref_a_chi[idx] = ref_b[idx] ^ ((~ref_b[idx1]) & ref_b[idx2])
    hw_a_chi = get_arr(sim, "a_chi", 25)
    if hw_a_chi != ref_a_chi:
        print("a_chi mismatch"); return
    print("a_chi OK")

    # Iota + state_out
    ref_a_chi[0] ^= RC[0]
    ref_state = 0
    for i in range(25):
        ref_state |= ref_a_chi[i] << (i*64)
    hw_state = int(sim.state.get("state_out", 0)) & ((1<<1600)-1)
    if hw_state != ref_state:
        print("state_out mismatch")
        print(f"  hw ={hw_state:0400x}")
        print(f"  ref={ref_state:0400x}")
        return
    print("state_out OK")
    print("\nAll KeccakRound steps match!")

if __name__ == "__main__":
    test()
