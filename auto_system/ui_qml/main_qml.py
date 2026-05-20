import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        if (meipass / "auto_system").exists():
            return meipass
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "auto_system").exists():
            return exe_dir
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
    icon_path = auto_system_root / "ui_qml" / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    engine = QQmlApplicationEngine()

    controller = AppController(str(auto_system_root))
    engine.rootContext().setContextProperty("appController", controller)
    xml_dir = auto_system_root / "xml"
    if not xml_dir.exists():
        xml_dir = auto_system_root / "xml_templates"
    engine.rootContext().setContextProperty(
        "defaultXmlPath",
        str((xml_dir / "unified_test_flow_example.xml").resolve()),
    )

    qml_main = auto_system_root / "ui_qml" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_main)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
