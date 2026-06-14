# {{ project_name }} — Top-Level Design Specification

| Document ID | {{ doc_id }} |
|-------------|--------------|
| Version     | {{ version }} |
| Date        | {{ date }} |
| Author      | {{ author }} |
| Owner       | {{ owner }} |
| Status      | {{ status }} |

---

## 1. Purpose and Scope

### 1.1 Purpose
<!-- Describe why this document exists and what it specifies. -->
{{ purpose }}

### 1.2 Scope
<!-- Define what is in scope (functions, blocks, interfaces) and what is out of scope. -->
{{ scope }}

### 1.3 Intended Audience
- System architects
- RTL designers
- Verification engineers
- Software/firmware engineers
- Project management

---

## 2. References

### 2.1 External References
| Document ID | Title | Version | Source |
|-------------|-------|---------|--------|
| {{ ref_id }} | {{ ref_title }} | {{ ref_version }} | {{ ref_source }} |

### 2.2 Internal References
| Document ID | Title | Description |
|-------------|-------|-------------|
| {{ int_ref_id }} | {{ int_ref_title }} | {{ int_ref_desc }} |

---

## 3. Definitions and Abbreviations

| Term / Abbreviation | Definition |
|---------------------|------------|
| {{ term }} | {{ definition }} |

---

## 4. System Overview

### 4.1 High-Level Architecture
<!-- Insert a block diagram or describe the major blocks. -->
{{ high_level_arch }}

```text
+----------------+        +----------------+        +----------------+
|   {{ block_a }}   |<------>|   {{ block_b }}   |<------>|   {{ block_c }}   |
+----------------+        +----------------+        +----------------+
```

### 4.2 Key Features
| ID | Feature | Priority | Notes |
|----|---------|----------|-------|
| F-01 | {{ feature_01 }} | Must | {{ feature_note_01 }} |
| F-02 | {{ feature_02 }} | Should | {{ feature_note_02 }} |

### 4.3 Target Application
{{ target_application }}

---

## 5. Functional Description

### 5.1 Operating Modes
| Mode | Description | Entry Condition | Exit Condition |
|------|-------------|-----------------|----------------|
| {{ mode }} | {{ mode_desc }} | {{ mode_entry }} | {{ mode_exit }} |

### 5.2 Data Flow
<!-- Describe the primary data paths through the system. -->
{{ data_flow }}

### 5.3 Control Flow
<!-- Describe reset, boot, configuration, and error-handling flows. -->
{{ control_flow }}

---

## 6. Interface Definition

### 6.1 External Interfaces
| Interface Name | Protocol | Width | Direction | Description |
|----------------|----------|-------|-----------|-------------|
| {{ if_name }} | {{ if_protocol }} | {{ if_width }} | {{ if_dir }} | {{ if_desc }} |

### 6.2 Internal Interfaces
| Source Block | Destination Block | Protocol | Description |
|--------------|-------------------|----------|-------------|
| {{ src }} | {{ dst }} | {{ proto }} | {{ desc }} |

---

## 7. Memory Map

| Base Address | End Address | Region | Description | Access |
|--------------|-------------|--------|-------------|--------|
| {{ base_addr }} | {{ end_addr }} | {{ region }} | {{ region_desc }} | {{ access }} |

---

## 8. Clock, Reset, and Power

### 8.1 Clock Domains
| Clock Name | Frequency | Source | Description |
|------------|-----------|--------|-------------|
| {{ clk_name }} | {{ clk_freq }} | {{ clk_src }} | {{ clk_desc }} |

### 8.2 Reset Strategy
| Reset Name | Type (sync/async) | Active Level | Scope |
|------------|-------------------|--------------|-------|
| {{ rst_name }} | {{ rst_type }} | {{ rst_active }} | {{ rst_scope }} |

### 8.3 Power Domains
| Power Domain | Voltage | Blocks | Power State |
|--------------|---------|--------|-------------|
| {{ pd_name }} | {{ pd_voltage }} | {{ pd_blocks }} | {{ pd_state }} |

---

## 9. Performance Requirements

| ID | Requirement | Target | Unit | Verification Method |
|----|-------------|--------|------|---------------------|
| P-01 | {{ perf_req_01 }} | {{ perf_target_01 }} | {{ perf_unit_01 }} | {{ perf_method_01 }} |

---

## 10. Power Requirements

| ID | Requirement | Target | Unit | Condition |
|----|-------------|--------|------|-----------|
| PWR-01 | {{ power_req_01 }} | {{ power_target_01 }} | {{ power_unit_01 }} | {{ power_cond_01 }} |

---

## 11. Quality and Reliability

### 11.1 Design Quality Goals
- Lint clean: {{ lint_goal }}
- Synthesis constraints met: {{ synth_goal }}
- Formal equivalence: {{ formal_goal }}

### 11.2 Reliability Requirements
| ID | Requirement | Target |
|----|-------------|--------|
| R-01 | {{ rel_req_01 }} | {{ rel_target_01 }} |

---

## 12. Verification Strategy

### 12.1 Verification Approach
{{ verification_approach }}

### 12.2 Verification Levels
| Level | Method | Owner | Exit Criteria |
|-------|--------|-------|---------------|
| Unit | {{ unit_method }} | {{ unit_owner }} | {{ unit_exit }} |
| Integration | {{ int_method }} | {{ int_owner }} | {{ int_exit }} |
| System | {{ sys_method }} | {{ sys_owner }} | {{ sys_exit }} |

---

## 13. Register Map

See the associated register specification document: {{ register_spec_link }}

---

## 14. Deliverables

| ID | Deliverable | Format | Owner | Due Date |
|----|-------------|--------|-------|----------|
| D-01 | {{ deliverable_01 }} | {{ deliverable_fmt_01 }} | {{ deliverable_owner_01 }} | {{ deliverable_date_01 }} |

---

## 15. Revision History

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| {{ version }} | {{ date }} | {{ author }} | Initial draft. |
