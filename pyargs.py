import sys
import yaml

with open(sys.argv[1]) as f:
    yml = yaml.safe_load(f)
    print(*['{}="{}"'.format(key,val) for key,val in yml.items()],sep='\n',end=None)
