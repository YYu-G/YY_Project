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
    title: "车载屏幕智能化测试系统"
    color: "#f4f6fb"

    property string logText: ""
    property string selectedXmlPath: ""
    property var datasetNames: []
    property var modelNames: []
    property bool suppressNextResultAutoNav: false
    property int sideBarW: Math.max(220, Math.min(320, Math.round(width * 0.2)))
    property int headH: Math.max(92, Math.min(132, Math.round(height * 0.12)))
    property int statusH: Math.max(32, Math.min(46, Math.round(height * 0.045)))
    property int logH: Math.max(120, Math.min(260, Math.round(height * 0.18)))
    palette.windowText: "#0f172a"
    palette.text: "#0f172a"
    palette.buttonText: "#0f172a"
    palette.placeholderText: "#475569"

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

    component LightComboBox: ComboBox {
        id: control
        implicitHeight: 44
        font.pixelSize: 16
        property string placeholderText: ""
        palette.text: "#0f172a"
        palette.buttonText: "#0f172a"
        palette.button: "#ffffff"
        palette.base: "#ffffff"

        contentItem: Text {
            readonly property bool showPlaceholder: control.currentIndex < 0 && control.placeholderText.length > 0
            text: showPlaceholder ? control.placeholderText : control.displayText
            color: showPlaceholder ? "#94a3b8" : (control.enabled ? "#0f172a" : "#64748b")
            font: control.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            leftPadding: 14
            rightPadding: 42
        }

        indicator: Text {
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            text: control.popup.visible ? "▲" : "▼"
            color: control.enabled ? "#334155" : "#94a3b8"
            font.pixelSize: 16
            font.bold: true
        }

        background: Rectangle {
            implicitHeight: 44
            radius: 8
            color: control.enabled ? "#ffffff" : "#f1f5f9"
            border.width: 1
            border.color: control.activeFocus ? "#334155" : "#cfd8e3"
        }

        delegate: ItemDelegate {
            width: control.width
            height: 38
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: modelData
                color: "#0f172a"
                font: control.font
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: highlighted ? "#e8eef7" : "#ffffff"
            }
        }

        popup: Popup {
            y: control.height + 2
            width: control.width
            implicitHeight: Math.min(contentItem.implicitHeight, 260)
            padding: 1

            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
            }

            background: Rectangle {
                color: "#ffffff"
                radius: 8
                border.width: 1
                border.color: "#cfd8e3"
            }
        }
    }

    component LightSpinBox: SpinBox {
        id: control
        implicitWidth: 210
        implicitHeight: 44
        font.pixelSize: 18
        palette.text: "#0f172a"
        palette.buttonText: "#0f172a"
        palette.button: "#ffffff"
        palette.base: "#ffffff"

        contentItem: TextInput {
            z: 2
            text: control.textFromValue(control.value, control.locale)
            font: control.font
            color: "#0f172a"
            selectionColor: "#bfdbfe"
            selectedTextColor: "#0f172a"
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter
            readOnly: !control.editable
            validator: control.validator
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }

        up.indicator: Rectangle {
            x: control.mirrored ? 0 : parent.width - width
            height: parent.height
            implicitWidth: 52
            color: control.up.pressed ? "#dbe5f3" : control.up.hovered ? "#eef3fb" : "#f8fafc"
            border.width: 1
            border.color: "#cfd8e3"
            Text {
                anchors.centerIn: parent
                text: "+"
                color: "#0f172a"
                font.pixelSize: 22
                font.bold: true
            }
        }

        down.indicator: Rectangle {
            x: control.mirrored ? parent.width - width : 0
            height: parent.height
            implicitWidth: 52
            color: control.down.pressed ? "#dbe5f3" : control.down.hovered ? "#eef3fb" : "#f8fafc"
            border.width: 1
            border.color: "#cfd8e3"
            Text {
                anchors.centerIn: parent
                text: "-"
                color: "#0f172a"
                font.pixelSize: 22
                font.bold: true
            }
        }

        background: Rectangle {
            implicitWidth: 210
            implicitHeight: 44
            radius: 8
            color: "#ffffff"
            border.width: 1
            border.color: control.activeFocus ? "#334155" : "#cfd8e3"
        }
    }

    component LightCheckBox: CheckBox {
        id: control
        implicitHeight: 30
        spacing: 10
        font.pixelSize: 14

        indicator: Rectangle {
            x: 0
            y: (control.height - height) / 2
            implicitWidth: 22
            implicitHeight: 22
            radius: 4
            color: control.checked ? "#dbeafe" : "#ffffff"
            border.width: 2
            border.color: control.checked ? "#2563eb" : "#cfd8e3"

            Text {
                anchors.centerIn: parent
                text: "✓"
                visible: control.checked
                color: "#1d4ed8"
                font.pixelSize: 16
                font.bold: true
            }
        }

        contentItem: Text {
            text: control.text
            color: "#0f172a"
            font: control.font
            verticalAlignment: Text.AlignVCenter
            leftPadding: control.indicator.width + control.spacing
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
    function clampIntText(valueText, minVal, maxVal, fallbackVal) {
        var v = parseInt(valueText)
        if (isNaN(v)) v = fallbackVal
        if (v < minVal) v = minVal
        if (v > maxVal) v = maxVal
        return String(v)
    }
    function clampBatchToDataset() {
        var datasetPath = datasetCombo.currentIndex >= 0 ? appController.resolveDatasetPath(datasetNames[datasetCombo.currentIndex]) : ""
        var trainCount = appController.datasetTrainImageCount(datasetPath)
        if (trainCount <= 0) trainCount = 1
        var nextBatch = clampIntText(batchInput.text, 1, Math.min(256, trainCount), 8)
        batchInput.text = nextBatch
        return parseInt(nextBatch)
    }
    function normalizeTrainingInputs() {
        epochsInput.text = clampIntText(epochsInput.text, 1, 3000, 20)
        imgszInput.text = clampIntText(imgszInput.text, 64, 2048, 640)
        clampBatchToDataset()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: sideBarW
            Layout.fillHeight: true
            color: "#edf1f7"
            border.color: "#dfe6f1"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 14

                Label { text: "模拟测试系统"; font.pixelSize: 30; font.bold: true; color: "#0f172a" }

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
                Label { text: "提示：左侧导航切换模块"; color: "#334155"; wrapMode: Text.Wrap }
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
                    Layout.preferredHeight: headH
                    radius: 16
                    color: "#ffffff"
                    border.color: "#dfe6f1"

                    Item {
                        anchors.fill: parent
                        anchors.margins: 14

                        Rectangle {
                            id: topStatusPill
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: 104
                            height: 58
                            radius: 12
                            color: appController.busy ? "#fef3c7" : "#e2e8f0"

                            Label {
                                anchors.centerIn: parent
                                text: appController.busy ? "运行中" : "空闲"
                                color: "#334155"
                                font.pixelSize: 22
                                font.bold: true
                            }
                        }

                        Column {
                            anchors.left: parent.left
                            anchors.right: topStatusPill.left
                            anchors.rightMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            Label {
                                width: parent.width
                                text: pageTitle(nav.currentIndex)
                                font.pixelSize: 30
                                font.bold: true
                                color: "#0f172a"
                                elide: Text.ElideRight
                            }
                            Label {
                                width: parent.width
                                text: pageDesc(nav.currentIndex)
                                color: "#334155"
                                font.pixelSize: 18
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: statusH
                    radius: 10
                    color: appController.busy ? "#fef3c7" : "#e8eef7"
                    border.color: "#d8e2ef"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        Label { text: "任务状态："; color: "#334155"; font.pixelSize: 16 }
                        Label { text: appController.statusText; color: "#0f172a"; font.bold: true; font.pixelSize: 16 }
                        Item { Layout.fillWidth: true }
                        Label { text: appController.summaryText; color: "#334155"; font.pixelSize: 14 }
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
                        contentHeight: Math.max(
                            pageScroll.availableHeight,
                            (pageStack.currentItem ? pageStack.currentItem.implicitHeight + 12 : 0)
                        )
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        StackLayout {
                            id: pageStack
                            width: pageScroll.availableWidth
                            currentIndex: nav.currentIndex

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: projectPathContent.implicitHeight + 24
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1
                                ColumnLayout {
                                    id: projectPathContent
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    GridLayout {
                                        id: projectPathGrid
                                        Layout.fillWidth: true
                                        columns: 2
                                        columnSpacing: 14
                                        rowSpacing: 12

                                        Label { text: "内置路径"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                        Item {}

                                        Label { text: "数据集目录"; font.pixelSize: 18; color: "#0f172a" }
                                        Label {
                                            text: appController.datasetsRoot
                                            font.pixelSize: 16
                                            color: "#334155"
                                            Layout.fillWidth: true
                                            elide: Text.ElideMiddle
                                        }

                                        Label { text: "模型目录"; font.pixelSize: 18; color: "#0f172a" }
                                        Label {
                                            text: appController.modelsRoot
                                            font.pixelSize: 16
                                            color: "#334155"
                                            Layout.fillWidth: true
                                            elide: Text.ElideMiddle
                                        }

                                        Label { text: "流程报告目录"; font.pixelSize: 18; color: "#0f172a" }
                                        Label {
                                            text: "auto_system/test/reports"
                                            font.pixelSize: 16
                                            color: "#334155"
                                            Layout.fillWidth: true
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                GhostButton { text: "XML模板下载"; onClicked: templateSaveDialog.open() }
                                Item { Layout.fillWidth: true }
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

                                        Label { text: "素材目录"; font.pixelSize: 22; color: "#0f172a" }
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
                                                text: ""
                                                color: "#0f172a"
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

                                        Label { text: "数据集名称"; font.pixelSize: 22; color: "#0f172a" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 240
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: datasetName
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: ""
                                                color: "#0f172a"
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
                                        LightCheckBox { id: skipUnlabeled; text: "跳过未标注图片"; checked: false }
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
                                    color: "#334155"
                                    font.pixelSize: 14
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: dataSourceGrid.implicitHeight + 24
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1
                                GridLayout {
                                    id: dataSourceGrid
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    columns: 3
                                    columnSpacing: 10
                                    rowSpacing: 10
                                    Label { text: "数据源"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                    Item {}
                                    Item {}
                                    Label { text: "数据集选择"; font.pixelSize: 18; color: "#0f172a" }
                                    LightComboBox { id: datasetCombo; model: datasetNames; Layout.fillWidth: true; enabled: datasetNames.length > 0 }
                                    GhostButton { text: "刷新列表"; onClicked: appController.refreshAssetLists() }
                                    Label { text: "初始权重"; font.pixelSize: 18; color: "#0f172a" }
                                    LightComboBox {
                                        id: modelCombo
                                        model: modelNames
                                        placeholderText: "yolo11n.pt"
                                        Layout.fillWidth: true
                                        enabled: modelNames.length > 0
                                    }
                                    GhostButton { text: "刷新列表"; onClicked: appController.refreshAssetLists() }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 700
                                    Layout.minimumWidth: 520
                                    Layout.preferredHeight: trainParamGrid.implicitHeight + 24
                                    radius: 12
                                    color: "#f8fafc"
                                    border.color: "#e2e8f0"
                                    border.width: 1
                                    GridLayout {
                                        id: trainParamGrid
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        columns: 3
                                        columnSpacing: 10
                                        rowSpacing: 10
                                        Label { text: "训练参数"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                        Item {}
                                        Item {}

                                        Label { text: "训练轮数"; font.pixelSize: 18; color: "#0f172a" }
                                        Rectangle {
                                            Layout.preferredWidth: 120
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: epochsInput
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: "20"
                                                validator: IntValidator { bottom: 1; top: 3000 }
                                                onEditingFinished: text = clampIntText(text, 1, 3000, 20)
                                                onActiveFocusChanged: if (!activeFocus) text = clampIntText(text, 1, 3000, 20)
                                                horizontalAlignment: Text.AlignHCenter
                                                color: "#0f172a"
                                                font.pixelSize: 20
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }
                                        }
                                        Label { text: "范围 1-3000；轮数越大训练越充分，但耗时更长"; font.pixelSize: 13; color: "#64748b" }

                                        Label { text: "图像尺寸"; font.pixelSize: 18; color: "#0f172a" }
                                        Rectangle {
                                            Layout.preferredWidth: 120
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: imgszInput
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: "640"
                                                validator: IntValidator { bottom: 64; top: 2048 }
                                                onEditingFinished: text = clampIntText(text, 64, 2048, 640)
                                                onActiveFocusChanged: if (!activeFocus) text = clampIntText(text, 64, 2048, 640)
                                                horizontalAlignment: Text.AlignHCenter
                                                color: "#0f172a"
                                                font.pixelSize: 20
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }
                                        }
                                        Label { text: "范围 64-2048；尺寸越大细节更好，但显存/耗时更高"; font.pixelSize: 13; color: "#64748b" }

                                        Label { text: "批次大小"; font.pixelSize: 18; color: "#0f172a" }
                                        Rectangle {
                                            Layout.preferredWidth: 120
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: batchInput
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: "8"
                                                validator: IntValidator { bottom: 1; top: 256 }
                                                onEditingFinished: text = clampIntText(text, 1, 256, 8)
                                                onActiveFocusChanged: if (!activeFocus) clampBatchToDataset()
                                                horizontalAlignment: Text.AlignHCenter
                                                color: "#0f172a"
                                                font.pixelSize: 20
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }
                                        }
                                        Label { text: "范围 1-256 且不超过数据集大小；批次越大训练更快，但更占显存"; font.pixelSize: 13; color: "#64748b" }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 320
                                    Layout.minimumWidth: 280
                                    Layout.preferredHeight: trainParamGrid.implicitHeight + 24
                                    radius: 12
                                    color: "#f8fafc"
                                    border.color: "#e2e8f0"
                                    border.width: 1
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 12
                                        Label { text: "执行"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                        Label { text: "模型名称"; font.pixelSize: 16; color: "#0f172a" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            radius: 10
                                            color: "#ffffff"
                                            border.color: "#cfd8e3"
                                            border.width: 1
                                            TextField {
                                                id: runName
                                                anchors.fill: parent
                                                anchors.margins: 2
                                                text: ""
                                                color: "#0f172a"
                                                font.pixelSize: 20
                                                leftPadding: 10
                                                rightPadding: 10
                                                background: Rectangle { color: "transparent"; border.width: 0 }
                                            }
                                        }
                                        AppButton {
                                            text: "开始训练"
                                            Layout.fillWidth: true
                                            enabled: !appController.busy && datasetNames.length > 0
                                            onClicked: {
                                                normalizeTrainingInputs()
                                                appController.trainModel(
                                                    datasetCombo.currentIndex >= 0 ? appController.resolveDatasetPath(datasetNames[datasetCombo.currentIndex]) : "",
                                                    modelCombo.currentIndex >= 0 ? appController.resolveModelPath(modelNames[modelCombo.currentIndex]) : "auto_system/yolo11n.pt",
                                                    parseInt(epochsInput.text),
                                                    parseInt(imgszInput.text),
                                                    parseInt(batchInput.text),
                                                    runName.text
                                                )
                                            }
                                        }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            width: pageStack.width
                            spacing: 10
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: flowSourceContent.implicitHeight + 24
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1
                                ColumnLayout {
                                    id: flowSourceContent
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 10
                                    Label { text: "脚本与模型"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 2
                                        columnSpacing: 10
                                        rowSpacing: 10
                                        Label { text: "XML 文件"; font.pixelSize: 18; color: "#0f172a" }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 44
                                                radius: 10
                                                color: "#ffffff"
                                                border.color: "#cfd8e3"
                                                border.width: 1
                                                TextField {
                                                    id: xmlPathField
                                                    text: selectedXmlPath
                                                    anchors.fill: parent
                                                    anchors.margins: 2
                                                    color: "#0f172a"
                                                    placeholderText: "请选择 XML 脚本文件"
                                                    font.pixelSize: 20
                                                    readOnly: true
                                                    selectByMouse: true
                                                    leftPadding: 10
                                                    rightPadding: 10
                                                    background: Rectangle { color: "transparent"; border.width: 0 }
                                                }
                                            }
                                            GhostButton { text: "选择文件"; onClicked: xmlDialog.open() }
                                        }
                                        Label { text: "模型选择"; font.pixelSize: 18; color: "#0f172a" }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            LightComboBox {
                                                id: processModelCombo
                                                model: modelNames
                                                Layout.fillWidth: true
                                                enabled: modelNames.length > 0
                                            }
                                            GhostButton { text: "刷新模型"; onClicked: appController.refreshAssetLists() }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 68
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 10
                                    Label { text: "执行配置与操作"; font.pixelSize: 18; font.bold: true; color: "#0f172a" }
                                    LightCheckBox { id: simulateBox; text: "模拟模式"; checked: true }
                                    AppButton {
                                        text: "运行流程"
                                        enabled: !appController.busy && selectedXmlPath.length > 0
                                        onClicked: appController.runProcessFlow(
                                            selectedXmlPath,
                                            processModelCombo.currentIndex >= 0 ? appController.resolveModelPath(modelNames[processModelCombo.currentIndex]) : "",
                                            simulateBox.checked,
                                            true
                                        )
                                    }
                                    GhostButton {
                                        text: "检测设备"
                                        enabled: !appController.busy
                                        onClicked: {
                                            suppressNextResultAutoNav = true
                                            appController.checkDeviceConnection()
                                        }
                                    }
                                    Item { Layout.fillWidth: true }
                                }
                            }
                        }

                        ColumnLayout {
                            id: resultCenterPage
                            width: pageStack.width
                            spacing: 10
                            property int bodyHeight: Math.max(240, Math.min(380, Math.floor(pageScroll.availableHeight * 0.36)))

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 98
                                radius: 12
                                color: "#f8fafc"
                                border.color: "#e2e8f0"
                                border.width: 1
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        GhostButton { text: "打开输出目录"; onClicked: appController.openOutputDir() }
                                        GhostButton { text: "导出报告"; onClicked: appController.exportReport() }
                                        GhostButton { text: "清空结果"; implicitWidth: 120; onClicked: appController.clearResult() }
                                        GhostButton { text: "清空历史"; implicitWidth: 120; onClicked: appController.clearHistory() }
                                        Item { Layout.fillWidth: true }
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: appController.outputDir.length > 0 ? ("输出目录: " + appController.outputDir) : "输出目录: -"
                                        color: "#334155"
                                        font.pixelSize: 14
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: resultCenterPage.bodyHeight
                                Layout.minimumHeight: 220
                                spacing: 10

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 12
                                    color: "#f8fafc"
                                    border.color: "#e2e8f0"
                                    border.width: 1
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 8
                                        Label { text: "最近任务历史（最近10条）"; font.pixelSize: 15; font.bold: true; color: "#0f172a" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 8
                                            color: "#ffffff"
                                            border.color: "#d7e0ec"
                                            Flickable {
                                                id: historyFlick
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                clip: true
                                                contentWidth: width
                                                contentHeight: Math.max(height, historyBox.contentHeight + 8)
                                                boundsBehavior: Flickable.StopAtBounds
                                                flickableDirection: Flickable.VerticalFlick
                                                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
                                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                                                TextEdit {
                                                    id: historyBox
                                                    width: historyFlick.width
                                                    height: Math.max(historyFlick.height, contentHeight + 8)
                                                    readOnly: true
                                                    selectByMouse: true
                                                    wrapMode: TextEdit.WrapAnywhere
                                                    textFormat: TextEdit.PlainText
                                                    text: appController.historyText
                                                    color: "#0f172a"
                                                    font.family: "Consolas"
                                                    font.pixelSize: 13
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 12
                                    color: "#f8fafc"
                                    border.color: "#e2e8f0"
                                    border.width: 1
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 8
                                        Label { text: "结果输出"; font.pixelSize: 15; font.bold: true; color: "#0f172a" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 8
                                            color: "#ffffff"
                                            border.color: "#d7e0ec"
                                            Flickable {
                                                id: resultFlick
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                clip: true
                                                contentWidth: width
                                                contentHeight: Math.max(height, resultBox.contentHeight + 8)
                                                boundsBehavior: Flickable.StopAtBounds
                                                flickableDirection: Flickable.VerticalFlick
                                                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
                                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                                                TextEdit {
                                                    id: resultBox
                                                    width: resultFlick.width
                                                    height: Math.max(resultFlick.height, contentHeight + 8)
                                                    wrapMode: TextEdit.WrapAnywhere
                                                    textFormat: TextEdit.PlainText
                                                    readOnly: true
                                                    selectByMouse: true
                                                    font.family: "Consolas"
                                                    font.pixelSize: 14
                                                    color: "#0f172a"
                                                    text: ""
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        }
                    }
                }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: logH
                        radius: 14
                        color: "#0b1736"

                        Flickable {
                            id: logFlick
                            anchors.fill: parent
                            anchors.margins: 12
                            clip: true
                            contentWidth: width
                            contentHeight: Math.max(height, logArea.contentHeight + 4)
                            boundsBehavior: Flickable.StopAtBounds
                            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            TextEdit {
                                id: logArea
                                width: logFlick.width
                                height: Math.max(logFlick.height, contentHeight + 4)
                                readOnly: true
                                selectByMouse: true
                                color: "#dbeafe"
                                font.family: "Consolas"
                                font.pixelSize: 16
                                wrapMode: TextEdit.Wrap
                                text: root.logText
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
        onAccepted: {
            selectedXmlPath = normalizePathForWindows(selectedFile.toString())
        }
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
            if (suppressNextResultAutoNav) {
                suppressNextResultAutoNav = false
            } else {
                nav.currentIndex = 4
            }
        }
        function onDatasetListChanged() {
            datasetNames = splitLines(appController.datasetListText)
            if (datasetCombo) datasetCombo.currentIndex = -1
        }
        function onModelListChanged() {
            modelNames = splitLines(appController.modelListText)
            if (modelCombo) modelCombo.currentIndex = -1
            if (processModelCombo) processModelCombo.currentIndex = -1
        }
    }

    Component.onCompleted: {
        datasetNames = splitLines(appController.datasetListText)
        modelNames = splitLines(appController.modelListText)
        datasetCombo.currentIndex = -1
        modelCombo.currentIndex = -1
        processModelCombo.currentIndex = -1
    }
}



