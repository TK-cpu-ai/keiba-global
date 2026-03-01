from pathlib import Path
import sys
from importlib import import_module


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if __name__ == "__main__":
    main = import_module("keiba.scraping.race_result").main
    main()
