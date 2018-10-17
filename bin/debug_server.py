# entry point for PyCharm debugger

import os
import importlib
import sys

sys.path.insert(0,os.getcwd())
mdl = importlib.import_module('run80by24.server.__main__')
mdl.main()