"""Compatibility entry; implementation lives in changan_ugv.transport.serial_bridge."""
import sys
from _bootstrap import bootstrap
bootstrap()
if __name__ == "__main__":
    import runpy
    runpy.run_module("changan_ugv.transport.serial_bridge", run_name="__main__")
else:
    from importlib import import_module
    sys.modules[__name__] = import_module("changan_ugv.transport.serial_bridge")
