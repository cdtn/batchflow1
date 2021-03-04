import re
import sys

with open('batchflow/__init__.py', 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if version != sys.argv[1]:
    sys.exit(0)
else:
    sys.exit(1)
