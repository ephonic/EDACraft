# Activate using: source /path/to/ftimer/env.sh
_ftimer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$_ftimer_root/bin:$PATH"
export PYTHONPATH="$_ftimer_root/python${PYTHONPATH:+:$PYTHONPATH}"
export FTIMER_BIN="$_ftimer_root/bin/ftimer"
unset _ftimer_root
