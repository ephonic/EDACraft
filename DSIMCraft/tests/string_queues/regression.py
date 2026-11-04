"""Owned string queue elements in ordinary, object and activation storage."""
from pathlib import Path
import runpy,sys
sys.argv.append('string_queues')
runpy.run_path(str(Path(__file__).resolve().parents[1]/'typed_execution.py'),run_name='__main__')
