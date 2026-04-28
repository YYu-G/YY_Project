import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore
ApplicationWindow {
    id: root
    width: 1280
    height: 820
    visible: true
    title: "车机智能化测试系统（QML）"
    color: "#f4f6fb"

    property string logText: ""
    property string selectedXmlPath: defaultXmlPath
    property var datasetNames: []
    property var modelNames: []

    component AppButton: Button {
        id: btn
        implicitHeight: 44
        implicitWidth: Math.max(136, contentItem.implicitWidth + 28)
        font.pixelSize: 15
        font.bold: true
        contentItem: Text {
            text: btn.text
            color: btn.enabled ? "#ffffff" : "#94a3b8"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: btn.font.pixelSize
            font.bold: btn.font.bold
        }
        background: Rectangle {
            radius: 10
            color: !btn.enabled ? "#e2e8f0" : btn.pressed ? "#0f172a" : btn.hovered ? "#1e293b" : "#111827"
            border.color: color
        }
    }

    component GhostButton: Button {
        id: btn
        implicitHeight: 44
        implicitWidth: 98
        font.pixelSize: 14
        contentItem: Text {
            text: btn.text
            color: btn.enabled ? "#334155" : "#94a3b8"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: btn.font.pixelSize
            font.bold: true
        }
        background: Rectangle {
            radius: 10
            color: !btn.enabled ? "#f1f5f9" : btn.pressed ? "#e2e8f0" : btn.hovered ? "#f1f5f9" : "#ffffff"
            border.width: 1
            border.color: "#cfd8e3"
        }
    }

    component DangerButton: Button {
        id: btn
        implicitHeight: 36
        implicitWidth: 98
        font.pixelSize: 14
        contentItem: Text {
            text: btn.text
            color: btn.enabled ? "#991b1b" : "#fca5a5"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: btn.font.pixelSize
            font.bold: true
        }
        background: Rectangle {
            radius: 10
            color: !btn.enabled ? "#fee2e2" : btn.pressed ? "#fecaca" : btn.hovered ? "#fef2f2" : "#fff1f2"
            border.width: 1
            border.color: "#fca5a5"
        }
    }

    function pageTitle(i) {
        if (i === 0) return "项目配置"
        if (i === 1) return "数据标注"
        if (i === 2) return "模型训练"
        if (i === 3) return "流程执行"
        return "结果中心"
    }

    function pageDesc(i) {
        if (i === 1) return "启动标注并生成 YOLO 数据集"
        if (i === 2) return "使用数据集训练 YOLO 模型"
        if (i === 3) return "执行 XML 脚本并输出测试结果"
        if (i === 4) return "查看和导出结构化结果"
        return "工作区参数与默认路径"
    }

    function normalizePathForWindows(urlOrPath) {
        return appController.normalizePath(urlOrPath)
    }
    function splitLines(text) {
        if (!text || text.length === 0) return []
        return text.split("\n").filter(function(x) { return x.length > 0 })
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 250
            Layout.fillHeight: true
            color: "#edf1f7"
            border.color: "#dfe6f1"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 14

                Label { text: "车机智能测试"; font.pixelSize: 30; font.bold: true; color: "#0f172a" }
                Label { text: "QML 架构原型"; color: "#64748b"; font.pixelSize: 14 }

                Repeater {
                    model: ["项目配置", "数据标注", "模型训练", "流程执行", "结果中心"]
                    delegate: Rectangle {
                        required property int index
                        required property string modelData
                        radius: 10
                        color: nav.currentIndex === index ? "#dbe7f7" : "transparent"
                        Layout.fillWidth: true
                        height: 46

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 14
                            text: modelData
                            color: "#0f172a"
                            font.pixelSize: 24
                        }

                        MouseArea { anchors.fill: parent; onClicked: nav.currentIndex = index }
                    }
                }

                Item { Layout.fillHeight: true }
                Label { text: "提示：左侧导航切换模块"; color: "#64748b"; wrapMode: Text.Wrap }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 108
                    radius: 16
                    color: "#ffffff"
                    border.color: "#dfe6f1"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 14

                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: pageTitle(nav.currentIndex); font.pixelSize: 34; font.bold: true; color: "#0f172a" }
                            Label { text: pageDesc(nav.currentIndex); color: "#64748b"; font.pixelSize: 22 }
                        }

                        Rectangle {
                            radius: 12
                            color: appController.busy ? "#fef3c7" : "#e2e8f0"
                            Layout.preferredWidth: 104
                            Layout.preferredHeight: 58

                            Label {
                                anchors.centerIn: parent
                                text: appController.busy ? "运行中" : "空闲"
                                color: "#334155"
                                font.pixelSize: 22
                                font.bold: true
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: 10
                    color: appController.busy ? "#fef3c7" : "#e8eef7"
                    border.color: "#d8e2ef"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        Label { text: "任务状态："; color: "#334155"; font.pixelSize: 16 }
                        Label { text: appController.statusText; color: "#0f172a"; font.bold: true; font.pixelSize: 16 }
                        Item { Layout.fillWidth: true }
                        Label { text: appController.summaryText; color: "#475569"; font.pixelSize: 14 }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    color: "#ffffff"
                    border.color: "#dfe6f1"

                    ScrollView {
                        id: pageScroll
                        anchors.fill: parent
                        anchors.margins: 10
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: Math.max(pageScroll.availableHeight, (pageStack.currentItem ? pageStack.currentItem.implicitHeight : 0))
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        StackLayout {
                            id: pageStack
                            width: pageScroll.availableWidth
                            currentIndex: nav.currentIndex

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                GhostButton { text: "XML模板下载"; onClicked: templateSaveDialog.open() }
                                Item { Layout.fillWidth: true }
                            }
                            GridLayout {
                                columns: 2
                                columnSpacing: 10
                                rowSpacing: 10
                                Label { text: "数据集目录"; font.pixelSize: 22 }
                                Label { text: appController.datasetsRoot; font.pixelSize: 20; color: "#334155" }
                                Label { text: "模型目录"; font.pixelSize: 22 }
                                Label { text: appController.modelsRoot; font.pixelSize: 20; color: "#334155" }
                                Label { text: "流程报告目录"; font.pixelSize: 22 }
                                Label { text: "auto_system/test/reports"; font.pixelSize: 20; color: "#334155" }
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: paramsContent.implicitHeight + 24
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1

                                ColumnLayout {
                                    id: paramsContent
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8

                                    Label { text: "参数设置"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }

                                    GridLayout {
                                        columns: 2
                                        columnSpacing: 10
                                        rowSpacing: 10
                                        Layout.fillWidth: true

                                        Label { text: "素材目录"; font.pixelSize: 22 }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1

                                            TextField {
                                                id: rawDirOnly
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: "auto_system/images"
                                                font.pixelSize: 20
                                                leftPadding: 10
                                                rightPadding: 96
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }

                                            Rectangle {
                                                anchors.right: parent.right
                                                anchors.rightMargin: 4
                                                anchors.verticalCenter: parent.verticalCenter
                                                width: 84
                                                height: 34
                                                radius: 8
                                                color: dirPickMouse.pressed ? "#dbe5f3" : dirPickMouse.containsMouse ? "#eef3fb" : "#f8fafc"
                                                border.width: 1
                                                border.color: "#c9d5e6"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "选择"
                                                    color: "#334155"
                                                    font.pixelSize: 15
                                                    font.bold: true
                                                }

                                                MouseArea {
                                                    id: dirPickMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: rawDirDialog.open()
                                                }
                                            }
                                        }

                                        Label { text: "数据集名称"; font.pixelSize: 22 }
                                        Rectangle {
                                            Layout.preferredWidth: 320
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: datasetName
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: "qml_dataset"
                                                font.pixelSize: 20
                                                leftPadding: 10
                                                rightPadding: 10
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: actionContent.implicitHeight + 20
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1

                                ColumnLayout {
                                    id: actionContent
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12
                                        AppButton {
                                            text: "开始标注并构建数据集"
                                            enabled: !appController.busy
                                            font.pixelSize: 17
                                            implicitWidth: Math.max(238, contentItem.implicitWidth + 44)
                                            onClicked: appController.buildDataset(rawDirOnly.text, "", datasetName.text, skipUnlabeled.checked)
                                        }
                                        GhostButton { text: "刷新列表"; onClicked: appController.refreshAssetLists() }
                                        Item { Layout.fillWidth: true }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        CheckBox { id: skipUnlabeled; text: "跳过未标注图片"; checked: false }
                                        Item { Layout.fillWidth: true }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: descLabel.implicitHeight + 20
                                radius: 10
                                color: "#f1f5f9"
                                border.color: "#dbe3ef"
                                border.width: 1

                                Label {
                                    id: descLabel
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: "说明：点击“开始标注并构建数据集”后将打开标注窗口。若名称已存在会提示重名。"
                                    color: "#475569"
                                    font.pixelSize: 14
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10
                            GridLayout {
                                columns: 3
                                columnSpacing: 10
                                rowSpacing: 10
                                Label { text: "数据集选择"; font.pixelSize: 22 }
                                ComboBox {
                                    id: datasetCombo
                                    model: datasetNames
                                    Layout.fillWidth: true
                                    enabled: datasetNames.length > 0
                                }
                                GhostButton { text: "刷新列表"; onClicked: appController.refreshAssetLists() }

                                Label { text: "初始权重"; font.pixelSize: 22 }
                                ComboBox {
                                    id: modelCombo
                                    model: modelNames
                                    Layout.fillWidth: true
                                    enabled: modelNames.length > 0
                                }
                                GhostButton { text: "刷新列表"; onClicked: appController.refreshAssetLists() }

                                Label { text: "Epochs"; font.pixelSize: 22 }
                                SpinBox { id: epochs; value: 20; from: 1; to: 3000 }
                                Item {}

                                Label { text: "ImgSz"; font.pixelSize: 22 }
                                SpinBox { id: imgsz; value: 640; from: 64; to: 2048 }
                                Item {}

                                Label { text: "Batch"; font.pixelSize: 22 }
                                SpinBox { id: batch; value: 8; from: 1; to: 256 }
                                Item {}

                                Label { text: "模型名称"; font.pixelSize: 22 }
                                Rectangle {
                                    Layout.preferredWidth: 320
                                    Layout.preferredHeight: 44
                                    radius: 10
                                    color: "#ffffff"
                                    border.color: "#cfd8e3"
                                    border.width: 1
                                    TextField {
                                        id: runName
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        text: "my_model"
                                        font.pixelSize: 20
                                        leftPadding: 10
                                        rightPadding: 10
                                        background: Rectangle { color: "transparent"; border.width: 0 }
                                    }
                                }
                                Item {}
                            }

                            AppButton {
                                text: "开始训练"
                                enabled: !appController.busy && datasetNames.length > 0
                                onClicked: appController.trainModel(
                                    datasetCombo.currentIndex >= 0 ? appController.resolveDatasetPath(datasetNames[datasetCombo.currentIndex]) : "",
                                    modelCombo.currentIndex >= 0 ? appController.resolveModelPath(modelNames[modelCombo.currentIndex]) : "auto_system/yolo11n.pt",
                                    epochs.value, imgsz.value, batch.value, runName.text
                                )
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10
                            GridLayout {
                                columns: 2
                                columnSpacing: 10
                                rowSpacing: 10
                                Label { text: "XML 文件"; font.pixelSize: 22 }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    radius: 10
                                    color: "#ffffff"
                                    border.color: "#cfd8e3"
                                    border.width: 1
                                    TextField {
                                        text: selectedXmlPath
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        font.pixelSize: 20
                                        readOnly: true
                                        leftPadding: 10
                                        rightPadding: 10
                                        background: Rectangle { color: "transparent"; border.width: 0 }
                                    }
                                }

                                Label { text: "模型选择"; font.pixelSize: 22 }
                                ComboBox {
                                    id: processModelCombo
                                    model: modelNames
                                    Layout.fillWidth: true
                                    enabled: modelNames.length > 0
                                }
                                Label { text: "执行选项"; font.pixelSize: 22 }
                                RowLayout {
                                    GhostButton { text: "刷新模型"; onClicked: appController.refreshAssetLists() }
                                    CheckBox { id: simulateBox; text: "模拟模式"; checked: true }
                                }
                            }

                            RowLayout {
                                AppButton {
                                    text: "运行流程"
                                    enabled: !appController.busy
                                    onClicked: appController.runProcessFlow(
                                        selectedXmlPath,
                                        processModelCombo.currentIndex >= 0 ? appController.resolveModelPath(modelNames[processModelCombo.currentIndex]) : "",
                                        simulateBox.checked,
                                        true
                                    )
                                }
                                GhostButton { text: "清空结果"; onClicked: resultBox.text = "" }
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                GhostButton {
                                    text: "打开输出目录"
                                    onClicked: appController.openOutputDir()
                                }
                                GhostButton {
                                    text: "导出报告"
                                    onClicked: appController.exportReport()
                                }
                                DangerButton {
                                    text: "清空历史"
                                    onClicked: appController.clearHistory()
                                }
                                Label {
                                    text: appController.outputDir.length > 0 ? ("输出目录: " + appController.outputDir) : "输出目录: -"
                                    color: "#475569"
                                    font.pixelSize: 14
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                            Label { text: "最近任务历史（最近10条）"; font.pixelSize: 16; color: "#334155" }
                            TextArea {
                                id: historyBox
                                Layout.fillWidth: true
                                Layout.preferredHeight: 120
                                readOnly: true
                                wrapMode: TextArea.Wrap
                                text: appController.historyText
                                font.family: "Consolas"
                                font.pixelSize: 13
                            }
                            TextArea {
                                id: resultBox
                                Layout.fillWidth: true
                                Layout.preferredHeight: 300
                                wrapMode: TextArea.NoWrap
                                readOnly: true
                                font.family: "Consolas"
                                font.pixelSize: 16
                                placeholderText: "结果 JSON"
                            }
                        }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 14
                    color: "#0b1736"

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 12
                        TextArea {
                            id: logArea
                            readOnly: true
                            color: "#dbeafe"
                            font.family: "Consolas"
                            font.pixelSize: 16
                            wrapMode: TextArea.Wrap
                            text: root.logText
                            background: null
                        }
                    }
                }
            }
        }
    }

    Item { id: nav; property int currentIndex: 0 }

    FolderDialog {
        id: rawDirDialog
        title: "选择素材目录"
        onAccepted: rawDirOnly.text = normalizePathForWindows(selectedFolder.toString())
    }

    FileDialog {
        id: xmlDialog
        title: "选择 XML 文件"
        nameFilters: ["XML files (*.xml)", "All files (*)"]
        onAccepted: selectedXmlPath = normalizePathForWindows(selectedFile.toString())
    }

    FileDialog {
        id: templateSaveDialog
        title: "保存 XML 模板"
        fileMode: FileDialog.SaveFile
        nameFilters: ["XML files (*.xml)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: appController.copyXmlTemplate(selectedFile.toString())
    }

    Connections {
        target: appController
        function onLogChanged(line) {
            if (root.logText.length > 0) root.logText += "\n"
            root.logText += line
        }
        function onResultChanged(payload) {
            resultBox.text = payload
            nav.currentIndex = 4
        }
        function onDatasetListChanged() {
            datasetNames = splitLines(appController.datasetListText)
            if (datasetCombo && datasetNames.length > 0 && datasetCombo.currentIndex < 0) datasetCombo.currentIndex = 0
        }
        function onModelListChanged() {
            modelNames = splitLines(appController.modelListText)
            if (modelCombo && modelNames.length > 0 && modelCombo.currentIndex < 0) modelCombo.currentIndex = 0
            if (processModelCombo && modelNames.length > 0 && processModelCombo.currentIndex < 0) processModelCombo.currentIndex = 0
        }
    }

    Component.onCompleted: {
        datasetNames = splitLines(appController.datasetListText)
        modelNames = splitLines(appController.modelListText)
        if (datasetNames.length > 0) datasetCombo.currentIndex = 0
        if (modelNames.length > 0) modelCombo.currentIndex = 0
        if (modelNames.length > 0) processModelCombo.currentIndex = 0
    }
}



