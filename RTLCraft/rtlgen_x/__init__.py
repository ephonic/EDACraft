"""Legacy ``rtlgen_x`` compatibility package.

New code should import ``rtlgen`` directly. This package only preserves the
historical seed-flow import paths that still exist in real examples.
"""

from rtlgen import *  # noqa: F401,F403

