import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    project_root = _project_root()
    auto_system_root = project_root / "auto_system"
    auto_test_dir = auto_system_root / "auto_test"
    if str(auto_test_dir) not in sys.path:
        sys.path.insert(0, str(auto_test_dir))

    from backend import AppController

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    controller = AppController(str(auto_system_root))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("defaultXmlPath", str((auto_system_root / "xml" / "unified_test_flow_example.xml").resolve()))

    qml_main = auto_system_root / "ui_qml" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_main)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
