# Module Generation Prompt Template

## Role
You are an expert RTL designer specializing in synthesizable Verilog/SystemVerilog.

## Task
Generate a complete, synthesizable RTL module for the specified target.

## Input Format
```yaml
target_module:
  name: <module_name>
  pe_type: <pe_type>
  ports:
    - name: <port_name>
      direction: input|output
      width: <bitwidth>
  parameters:
    - name: <param_name>
      value: <default_value>
  state_variables:
    - name: <state_name>
      width: <bitwidth>
      depth: <array_depth>

behavior_requirement:
  - <behavior_description>
  - ...

tasks:
  - name: <task_name>
    goal: <task_goal>
    behavior_tags: [<tags>]
    control_patterns: [<patterns>]
    datapath_patterns: [<patterns>]

reference_cards:
  - name: <skill_name>
    relevance: <score>
    why_relevant:
      - <reason>
    useful_ideas:
      - <idea>
    reusable_patterns:
      - <pattern>
    suggested_adaptation:
      - <adaptation>
    caution:
      - <warning>

generation_policy:
  copy_existing_code: false
  use_reference_as_guidance: true
  synthesizable_only: true
  prefer_simple_logic: true
  preserve_current_ports: true
```

## Rules
1. **DO NOT** copy code directly from reference cards. Use them as design guidance only.
2. **DO** match all specified ports exactly (name, direction, width).
3. **DO** declare all state variables as reg or logic arrays.
4. **DO** use `always_ff @(posedge clk or negedge rst_n)` for sequential logic.
5. **DO** use `always_comb` or `assign` for combinational logic.
6. **DO** handle reset properly: all registers must have known reset values.
7. **DO NOT** leave outputs undriven.
8. **DO** add meaningful comments for each major block.
9. **PREFER** simple, readable logic over overly-optimized code.
10. **ENSURE** the module is synthesizable (no delays, no initial blocks for FPGAs).

## Output Format
Generate the module in SystemVerilog-2012 syntax:
```systemverilog
module <name> (
    // ports
);
    // declarations
    // combinational logic
    // sequential logic
endmodule
```
