import sys
from pathlib import Path


def _bootstrap_path() -> Path:
    current = Path(__file__).resolve().parent
    auto_test_dir = current / "auto_test"
    if str(auto_test_dir) not in sys.path:
        sys.path.insert(0, str(auto_test_dir))
    return current


def main() -> int:
    _bootstrap_path()
    try:
        from ui_qml.main_qml import main as run_qml_app
    except ImportError as e:
        print("Missing GUI dependency. Install with: pip install PySide6")
        print(f"ImportError: {e}")
        return 1

    return run_qml_app()


if __name__ == "__main__":
    raise SystemExit(main())
