from pathlib import Path

def get_unique_debug_dir(base_path: Path) -> Path:
    """
    Generates a unique directory path for debug files.
    If the base path exists, appends a counter (e.g., _1, _2) until a unique path is found.
    """
    debug_dir = base_path
    counter = 0
    while debug_dir.exists():
        counter += 1
        debug_dir = Path(f"{base_path}_{counter}")
    return debug_dir
