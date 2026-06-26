#!/bin/bash
# =============================================================================
# Design Compiler Synthesis Runner
# =============================================================================
# Usage: ./run_synthesis.sh [config_file]
# Default: configs/FullSystem.yaml
# =============================================================================

set -e

CONFIG_FILE="${1:-configs/FullSystem.yaml}"

echo "=============================================="
echo "Design Compiler Synthesis"
echo "Config: $CONFIG_FILE"
echo "=============================================="

# Check config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Generate TCL script from YAML config
echo "Generating synthesis script from config..."
python3 -c "
from src.db.config_loader import load_design_config
from src.tools.dc_adapter import DCAdapter

state = load_design_config('$CONFIG_FILE')
adapter = DCAdapter(state)
adapter.setup_work_dir()
script = adapter.generate_script()

with open('work/synthesis/DC/run.tcl', 'w') as f:
    f.write(script)
print('Generated: work/synthesis/DC/run.tcl')
print(f'Script lines: {len(script.splitlines())}')
"

# Run DC synthesis
echo "Running Design Compiler..."
source /share/apps/EDAs/syn22.bash 2>/dev/null || true
dc_shell -no_gui -f work/synthesis/DC/run.tcl | tee work/synthesis/DC/run.log

echo "=============================================="
echo "Synthesis complete"
echo "Reports: work/synthesis/DC/report/"
echo "Outputs: work/synthesis/DC/out/"
echo "=============================================="
