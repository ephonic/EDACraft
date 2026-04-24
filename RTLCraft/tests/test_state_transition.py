"""Tests for rtlgen.logic.StateTransition FSM helper."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen import Module, Input, Output, Reg, StateTransition, VerilogEmitter, Simulator


class CounterFSM(Module):
    """3-state counter FSM using StateTransition."""

    def __init__(self):
        super().__init__("CounterFSM")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.en = Input(1, "en")
        self.state = Reg(2, "state")
        self.flag = Output(1, "flag")

        IDLE = 0
        COUNT = 1
        DONE = 2

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with StateTransition(self.state) as st:
                st.next(COUNT, when=(self.state == IDLE) & self.en)
                st.next(DONE,  when=(self.state == COUNT) & self.en)
                st.next(IDLE,  when=self.state == DONE)

        @self.comb
        def _out():
            self.flag <<= self.state == DONE


def test_state_transition_verilog():
    """StateTransition should generate a single Mux-chain assignment."""
    m = CounterFSM()
    v = VerilogEmitter().emit(m)
    # Should contain exactly one non-blocking assignment to state_reg
    lines = [l.strip() for l in v.splitlines()]
    state_assigns = [l for l in lines if "state <=" in l]
    assert len(state_assigns) == 1, f"Expected 1 state assignment, got {len(state_assigns)}: {state_assigns}"
    # The assignment should be a Mux chain (nested ?:)
    assert "?" in state_assigns[0], "Expected ternary Mux chain in generated Verilog"


def test_state_transition_simulation():
    """FSM should cycle correctly in Python simulator."""
    m = CounterFSM()
    sim = Simulator(m)
    sim.reset("rst_n")

    # After reset, state should be 0 (IDLE)
    assert sim.peek("state") == 0

    # Without en, stay in IDLE
    sim.poke("en", 0)
    sim.step()
    assert sim.peek("state") == 0

    # With en, transition IDLE -> COUNT
    sim.poke("en", 1)
    sim.step()
    assert sim.peek("state") == 1

    # COUNT -> DONE
    sim.step()
    assert sim.peek("state") == 2
    assert sim.peek("flag") == 1

    # DONE -> IDLE
    sim.step()
    assert sim.peek("state") == 0
    assert sim.peek("flag") == 0


def test_state_transition_manual_commit():
    """Manual commit mode should work identically."""
    class ManualFSM(Module):
        def __init__(self):
            super().__init__("ManualFSM")
            self.clk = Input(1, "clk")
            self.rst_n = Input(1, "rst_n")
            self.state = Reg(1, "state")

            @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
            def _fsm():
                st = StateTransition(self.state)
                st.next(1, when=self.state == 0)
                st.next(0, when=self.state == 1)
                st.commit()

    m = ManualFSM()
    sim = Simulator(m)
    sim.reset("rst_n")
    assert sim.peek("state") == 0
    sim.step()
    assert sim.peek("state") == 1
    sim.step()
    assert sim.peek("state") == 0


def test_state_transition_hold_default():
    """When no transition matches, state should hold by default."""
    class HoldFSM(Module):
        def __init__(self):
            super().__init__("HoldFSM")
            self.clk = Input(1, "clk")
            self.rst_n = Input(1, "rst_n")
            self.go = Input(1, "go")
            self.state = Reg(2, "state")

            @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
            def _fsm():
                with StateTransition(self.state) as st:
                    st.next(1, when=(self.state == 0) & self.go)
                    # No transition from state==1, should hold

    m = HoldFSM()
    sim = Simulator(m)
    sim.reset("rst_n")
    sim.poke("go", 0)
    sim.step()
    assert sim.peek("state") == 0  # No go, stays in 0
    sim.poke("go", 1)
    sim.step()
    assert sim.peek("state") == 1  # go=1, moves to 1
    sim.poke("go", 0)
    sim.step()
    assert sim.peek("state") == 1  # No transition from 1, holds
