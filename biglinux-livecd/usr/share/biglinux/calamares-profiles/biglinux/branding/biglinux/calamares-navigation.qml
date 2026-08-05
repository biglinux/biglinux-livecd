/* BigLinux native-looking QML navigation for Calamares. */
import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    implicitHeight: 64
    Layout.preferredHeight: 64
    color: palette.window

    readonly property bool finalStep:
        ViewManager.currentStepIndex === steps.count - 1
    // While the installation runs, back and next are hidden and quit is the
    // only action left: it belongs on the right, where actions live.
    readonly property bool actionsOnRight:
        finalStep || !ViewManager.backAndNextVisible

    function cleanLabel(label) {
        return String(label).replace(/&/g, "")
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    // Only counts the view steps. ListView.count stays 0 without a delegate.
    ListView {
        id: steps
        visible: false
        model: ViewManager
        delegate: Item {}
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: palette.mid
        opacity: 0.65
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 8

        Item {
            Layout.fillWidth: true
            visible: root.actionsOnRight
        }

        Button {
            text: root.cleanLabel(ViewManager.quitLabel)
            icon.name: ViewManager.quitIcon
            enabled: ViewManager.quitEnabled
            visible: ViewManager.quitVisible
            onClicked: ViewManager.quit()

            ToolTip.visible: hovered && ViewManager.quitTooltip !== ""
            ToolTip.delay: 700
            ToolTip.text: ViewManager.quitTooltip
        }

        Item {
            Layout.fillWidth: true
            visible: !root.actionsOnRight
        }

        Button {
            Layout.minimumWidth: 108
            text: root.cleanLabel(ViewManager.backLabel)
            icon.name: ViewManager.backIcon
            enabled: ViewManager.backEnabled
            visible: ViewManager.backAndNextVisible && !root.finalStep
            onClicked: ViewManager.back()
        }

        Button {
            Layout.minimumWidth: 116
            text: root.cleanLabel(ViewManager.nextLabel)
            icon.name: ViewManager.nextIcon
            enabled: ViewManager.nextEnabled
            visible: ViewManager.backAndNextVisible && !root.finalStep
            highlighted: true
            onClicked: ViewManager.next()
        }
    }
}
