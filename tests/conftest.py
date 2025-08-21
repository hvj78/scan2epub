import sys
from pathlib import Path

def pytest_configure():
    """
    Ensure the project's src/ directory is on sys.path so tests can import 'scan2epub'.
    """
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_str = str(src_path)
    if src_path.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)
