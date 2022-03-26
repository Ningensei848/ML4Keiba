from itertools import cycle
from pathlib import Path

cwd = Path.cwd()

filepath = cwd / "namelist.txt"
entrypoints = [line.strip() for line in filepath.read_text().split("\n") if len(line) > 0]


def generateEntrypoints():
    for entry in cycle(entrypoints):
        yield entry
