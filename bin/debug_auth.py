# entry point for PyCharm debugger

import os
import importlib
import sys

sys.path.insert(0,os.path.join(os.path.split(os.getcwd())[0],'run80by24-auth'))
mdl = importlib.import_module('app')
mdl.debug()