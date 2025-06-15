import pathlib
import sys

base = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(base.parent))
from rename_buffers import rename_code

def read(name):
    return (base / name).read_text()


def test_example1():
    inp = read('example1.c')
    expected = read('example1_expected.c')
    assert rename_code(inp) == expected


def test_example2():
    inp = read('example2.c')
    expected = read('example2_expected.c')
    assert rename_code(inp) == expected
