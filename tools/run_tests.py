"""Run host/admin regressions only; no firmware build or serial access."""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'host/src'))
sys.path.insert(0,str(root/'tools'))
loader=unittest.TestLoader()
suite=unittest.TestSuite()
for directory in (root/'tests',root/'host/tests'):
    suite.addTests(loader.discover(str(directory),top_level_dir=str(directory)))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
