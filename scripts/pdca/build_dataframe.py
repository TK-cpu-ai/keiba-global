from importlib import import_module
from pathlib import Path
import sys


HERE = Path(__file__).resolve()
ROOT = HERE
while not (ROOT / "src").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


if __name__ == "__main__":
    main = import_module("keiba.dataset.build_dataframe").main
    main()
