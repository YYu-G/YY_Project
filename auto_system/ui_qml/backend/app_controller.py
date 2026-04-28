import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote

from PySide6.QtCore import QObject, Property, Signal, Slot

from model_controller import ModelController
from process_controller import ProcessController


class AppController(QObject):
    logChanged = Signal(str)
    resultChanged = Signal(str)
    busyChanged = Signal()
    statusChanged = Signal()
    summaryChanged = Signal()
    historyChanged = Signal()
    outputDirChanged = Signal()
    datasetListChanged = Signal()
    modelListChanged = Signal()

    def __init__(self, auto_system_root: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._status_text = "空闲"
        self._summary_text = "-"
        self._history_items = []
        self._history_text = "暂无任务历史"
        self._last_output_dir = ""
        self._auto_system_root = Path(auto_system_root)
        self._datasets_root = (self._auto_system_root / "datasets").resolve()
        self._models_root = (self._auto_system_root / "yolo").resolve()
        self._dataset_items = []
        self._model_items = []
        self._dataset_name_map = {}
        self._model_name_map = {}
        self._dataset_list_text = ""
        self._model_list_text = ""
        self._history_file = self._auto_system_root / "ui_qml" / "history.json"
        self._last_result_text = ""
        self._load_history()
        self.refreshAssetLists()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(str, notify=summaryChanged)
    def summaryText(self) -> str:
        return self._summary_text

    @Property(str, notify=historyChanged)
    def historyText(self) -> str:
        return self._history_text

    @Property(str, notify=outputDirChanged)
    def outputDir(self) -> str:
        return self._last_output_dir

    @Property(str, constant=True)
    def datasetsRoot(self) -> str:
        return str(self._datasets_root)

    @Property(str, constant=True)
    def modelsRoot(self) -> str:
        return str(self._models_root)

    @Property(str, notify=datasetListChanged)
    def datasetListText(self) -> str:
        return self._dataset_list_text

    @Property(str, notify=modelListChanged)
    def modelListText(self) -> str:
        return self._model_list_text

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _set_status(self, text: str) -> None:
        if self._status_text != text:
            self._status_text = text
            self.statusChanged.emit()

    def _set_summary(self, text: str) -> None:
        if self._summary_text != text:
            self._summary_text = text
            self.summaryChanged.emit()

    def _set_output_dir(self, path: str) -> None:
        normalized = self.normalizePath(path)
        if self._last_output_dir != normalized:
            self._last_output_dir = normalized
            self.outputDirChanged.emit()

    def _append_history(self, task_name: str, status: str, elapsed: float, output_dir: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{now} | {task_name} | {status} | {elapsed:.2f}s | {output_dir or '-'}"
        self._history_items.insert(0, line)
        self._history_items = self._history_items[:10]
        self._history_text = "\n".join(self._history_items) if self._history_items else "暂无任务历史"
        self._save_history()
        self.historyChanged.emit()

    def _load_history(self) -> None:
        try:
            if not self._history_file.exists():
                return
            raw = json.loads(self._history_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                self._history_items = [str(x) for x in raw[:10]]
                self._history_text = "\n".join(self._history_items) if self._history_items else "暂无任务历史"
        except Exception:
            self._history_items = []
            self._history_text = "暂无任务历史"

    def _save_history(self) -> None:
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            self._history_file.write_text(json.dumps(self._history_items, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            self._emit_log(f"保存历史失败：{e}")

    def _emit_log(self, msg: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.logChanged.emit(f"[{now}] {msg}")

    def _update_dataset_text(self) -> None:
        self._dataset_list_text = "\n".join(self._dataset_items)
        self.datasetListChanged.emit()

    def _update_model_text(self) -> None:
        self._model_list_text = "\n".join(self._model_items)
        self.modelListChanged.emit()

    def _make_unique_name(self, base_name: str, used: Dict[str, str], hint: str) -> str:
        if base_name not in used:
            return base_name
        idx = 2
        candidate = f"{base_name} ({hint})"
        if candidate not in used:
            return candidate
        while True:
            candidate = f"{base_name} ({hint}-{idx})"
            if candidate not in used:
                return candidate
            idx += 1

    @Slot()
    def refreshAssetLists(self) -> None:
        datasets = []
        models = []
        self._dataset_name_map = {}
        self._model_name_map = {}
        if self._datasets_root.exists():
            for p in self._datasets_root.rglob("dataset.yaml"):
                resolved = str(p.resolve())
                display = p.parent.name
                display = self._make_unique_name(display, self._dataset_name_map, p.parent.name)
                self._dataset_name_map[display] = resolved
                datasets.append(display)
        if self._models_root.exists():
            for p in self._models_root.rglob("*.pt"):
                resolved = str(p.resolve())
                display = p.name
                hint = p.parent.name
                display = self._make_unique_name(display, self._model_name_map, hint)
                self._model_name_map[display] = resolved
                models.append(display)
        datasets.sort(reverse=True)
        models.sort(reverse=True)
        self._dataset_items = datasets
        self._model_items = models
        self._update_dataset_text()
        self._update_model_text()

    @Slot(str, result=str)
    def resolveDatasetPath(self, display_name: str) -> str:
        return self._dataset_name_map.get((display_name or "").strip(), "")

    @Slot(str, result=str)
    def resolveModelPath(self, display_name: str) -> str:
        return self._model_name_map.get((display_name or "").strip(), "")

    def _check_name_conflict(self, target_root: Path, target_name: str, kind: str) -> bool:
        name = (target_name or "").strip()
        if not name:
            self._emit_log(f"{kind}名称不能为空。")
            return False
        if (target_root / name).exists():
            self._emit_log(f"{kind}重名：{name} 已存在，请更换名称。")
            return False
        return True

    @Slot(str, result=str)
    def normalizePath(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        if v.startswith("file:///"):
            v = v[8:]
            if len(v) >= 2 and v[1] == ":":
                return unquote(v)
            return unquote(v).replace("/", "\\")
        if v.startswith("file://"):
            v = v[7:]
            return unquote(v).replace("/", "\\")
        return v

    def _build_summary(self, result: Dict[str, Any], elapsed: float) -> str:
        sec = f"{elapsed:.2f}s"
        if "summary" in result:
            s = result.get("summary", {}) or {}
            return f"耗时 {sec} | 用例 {s.get('passed_cases', 0)}/{s.get('total_cases', 0)} 通过"
        for key in ("fixed_best_model", "best_model", "best"):
            if result.get(key):
                return f"耗时 {sec} | 输出模型：{result.get(key)}"
        if result.get("yaml_path"):
            return f"耗时 {sec} | 输出数据集：{result.get('yaml_path')}"
        return f"耗时 {sec}"

    def _extract_output_dir(self, result: Dict[str, Any]) -> str:
        for key in ("fixed_best_model", "best_model", "best"):
            if result.get(key):
                return str(Path(str(result.get(key))).resolve().parent)
        if result.get("dataset_dir"):
            return str(Path(str(result.get("dataset_dir"))).resolve())
        if result.get("yaml_path"):
            return str(Path(str(result.get("yaml_path"))).resolve().parent)
        return ""

    @Slot(str, str, bool, bool)
    def runProcessFlow(self, xml_path: str, model_path: str, simulate: bool, continue_on_failure: bool) -> None:
        if self._busy:
            self._emit_log("已有任务在运行，请稍后。")
            return

        def worker() -> None:
            started = time.time()
            self._set_busy(True)
            self._set_status("流程执行中")
            self._emit_log("开始执行 XML 流程任务。")
            try:
                process = ProcessController(
                    simulate=simulate,
                    stop_on_failure=not continue_on_failure,
                    model_path=self.normalizePath(model_path) or None,
                    screen_source="desktop" if simulate else "adb",
                    model_conf=0.25,
                    model_iou=0.7,
                    model_device="cpu",
                )
                result: Dict[str, Any] = process.run(self.normalizePath(xml_path))
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps(result, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps(result, ensure_ascii=False, indent=2)
                self._set_summary(self._build_summary(result, elapsed))
                out_dir = self._extract_output_dir(result)
                self._set_output_dir(out_dir)
                self._append_history("流程执行", "成功", elapsed, out_dir)
                self.refreshAssetLists()
                self._emit_log("流程执行完成。")
                self._set_status("流程执行完成")
            except Exception as e:
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)
                self._set_summary(f"耗时 {elapsed:.2f}s | 执行失败")
                self._append_history("流程执行", "失败", elapsed, "")
                self._emit_log(f"流程执行失败：{e}")
                self._set_status("流程执行失败")
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, str, str, bool)
    def buildDataset(self, raw_dir: str, classes_file: str, dataset_name: str, skip_unlabeled: bool) -> None:
        if self._busy:
            self._emit_log("已有任务在运行，请稍后。")
            return
        if not self._check_name_conflict(self._datasets_root, dataset_name, "数据集"):
            self._set_status("数据集命名冲突")
            return

        def worker() -> None:
            started = time.time()
            self._set_busy(True)
            self._set_status("数据集构建中")
            self._emit_log("开始数据标注与数据集构建。")
            try:
                controller = ModelController(
                    dataset_name=dataset_name.strip() or f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    datasets_root=str((self._auto_system_root / "datasets").resolve()),
                )
                result: Dict[str, Any] = controller.create_dataset_with_annotation(
                    raw_image_dir=self.normalizePath(raw_dir),
                    classes_file=self.normalizePath(classes_file) or None,
                    skip_unlabeled=skip_unlabeled,
                )
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps(result, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps(result, ensure_ascii=False, indent=2)
                self._set_summary(self._build_summary(result, elapsed))
                out_dir = self._extract_output_dir(result)
                self._set_output_dir(out_dir)
                self._append_history("数据集构建", "成功", elapsed, out_dir)
                self.refreshAssetLists()
                self._emit_log("数据集构建完成。")
                self._set_status("数据集构建完成")
            except Exception as e:
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)
                self._set_summary(f"耗时 {elapsed:.2f}s | 构建失败")
                self._append_history("数据集构建", "失败", elapsed, "")
                self._emit_log(f"数据集构建失败：{e}")
                self._set_status("数据集构建失败")
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, str, int, int, int, str)
    def trainModel(self, dataset_yaml: str, weights: str, epochs: int, imgsz: int, batch: int, run_name: str) -> None:
        if self._busy:
            self._emit_log("已有任务在运行，请稍后。")
            return
        if not self._check_name_conflict(self._models_root, run_name, "模型"):
            self._set_status("模型命名冲突")
            return

        def worker() -> None:
            started = time.time()
            self._set_busy(True)
            self._set_status("模型训练中")
            self._emit_log("开始模型训练。")
            try:
                controller = ModelController(
                    datasets_root=str((self._auto_system_root / "datasets").resolve()),
                    conf=0.25,
                    iou=0.7,
                    device="cpu",
                )
                result: Dict[str, Any] = controller.train_model(
                    dataset_yaml=self.normalizePath(dataset_yaml),
                    model_weights=self.normalizePath(weights) or "yolo11n.pt",
                    epochs=int(epochs),
                    imgsz=int(imgsz),
                    batch=int(batch),
                    workers=4,
                    device="cpu",
                    run_name=run_name.strip() or f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    exist_ok=False,
                    auto_load_best=False,
                )
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps(result, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps(result, ensure_ascii=False, indent=2)
                self._set_summary(self._build_summary(result, elapsed))
                out_dir = self._extract_output_dir(result)
                self._set_output_dir(out_dir)
                self._append_history("模型训练", "成功", elapsed, out_dir)
                self.refreshAssetLists()
                self._emit_log("模型训练完成。")
                self._set_status("模型训练完成")
            except Exception as e:
                elapsed = time.time() - started
                self.resultChanged.emit(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2))
                self._last_result_text = json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)
                self._set_summary(f"耗时 {elapsed:.2f}s | 训练失败")
                self._append_history("模型训练", "失败", elapsed, "")
                self._emit_log(f"模型训练失败：{e}")
                self._set_status("模型训练失败")
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def openOutputDir(self) -> None:
        path = self._last_output_dir
        if not path:
            self._emit_log("当前没有可打开的输出目录。")
            return
        p = Path(path)
        if not p.exists():
            self._emit_log(f"输出目录不存在：{path}")
            return
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]
            self._emit_log(f"已打开输出目录：{path}")
        except Exception as e:
            self._emit_log(f"打开输出目录失败：{e}")

    @Slot(str)
    def appendLog(self, text: str) -> None:
        self._emit_log(text)

    @Slot(str)
    def copyXmlTemplate(self, target_path: str) -> None:
        target = self.normalizePath(target_path)
        if not target:
            self._emit_log("未提供模板导出路径。")
            return
        src = (self._auto_system_root / "xml" / "unified_test_flow_template.xml").resolve()
        if not src.exists():
            self._emit_log(f"模板文件不存在：{src}")
            return
        try:
            dst = Path(target)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            self._emit_log(f"XML模板已导出：{dst}")
            self._set_output_dir(str(dst.parent.resolve()))
        except Exception as e:
            self._emit_log(f"XML模板导出失败：{e}")

    @Slot()
    def clearHistory(self) -> None:
        self._history_items = []
        self._history_text = "暂无任务历史"
        self._save_history()
        self.historyChanged.emit()
        self._emit_log("已清空任务历史。")

    @Slot()
    def exportReport(self) -> None:
        if not self._last_result_text:
            self._emit_log("暂无可导出的结果。")
            return
        try:
            report_dir = self._auto_system_root / "test" / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = report_dir / f"report_{ts}.md"
            lines = [
                "# 车机智能化测试报告",
                "",
                f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"- 状态摘要: {self._summary_text}",
                f"- 输出目录: {self._last_output_dir or '-'}",
                "",
                "## 最近任务历史",
                "",
                "```text",
                self._history_text,
                "```",
                "",
                "## 结果 JSON",
                "",
                "```json",
                self._last_result_text,
                "```",
                "",
            ]
            report_path.write_text("\n".join(lines), encoding="utf-8")
            self._emit_log(f"报告已导出：{report_path}")
            self._set_output_dir(str(report_dir))
        except Exception as e:
            self._emit_log(f"导出报告失败：{e}")
