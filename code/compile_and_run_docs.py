

import os

commands = [
    "cd docs && make html",
    "xdg-open docs/_build/html/index.html"
]

for command in commands:
    os.system(command)