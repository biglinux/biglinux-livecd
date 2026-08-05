/* BigLinux native-looking QML navigation for Calamares. */
import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "i18n.js" as I18n

Rectangle {
    id: root

    implicitHeight: 64
    Layout.preferredHeight: 64
    color: palette.window

    readonly property bool finalStep:
        ViewManager.currentStepIndex === steps.count - 1

    // The disk password is typed on the partitioning page, and GRUB asks for it
    // at boot before any keyboard layout exists, so a character needing a dead
    // key or AltGr cannot be entered there. The page itself belongs to the
    // partition module and cannot be extended, but this bar is ours and knows
    // which page is showing.
    //
    // The index comes from the show sequence in settings.conf, where partition
    // is the fourth step; a test keeps the two in agreement. Whether the
    // encryption box is ticked is not knowable here - the partition module
    // records that only once the installation starts - so the wording covers
    // both cases.
    readonly property int partitionStepIndex: 3
    readonly property bool onPartitionStep:
        ViewManager.currentStepIndex === partitionStepIndex
    // While the installation runs, back and next are hidden and quit is the
    // only action left: it belongs on the right, where actions live.
    readonly property bool actionsOnRight:
        finalStep || !ViewManager.backAndNextVisible

    readonly property string localeKey:
        Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")

    function tr(source) { return I18n.translate(source, localeKey) }

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

        Rectangle {
            Layout.fillWidth: true
            Layout.maximumHeight: 40
            Layout.alignment: Qt.AlignVCenter
            visible: root.onPartitionStep
            implicitHeight: encryptionHint.implicitHeight + 12
            radius: 6
            color: Qt.rgba(0.85, 0.33, 0.10, 0.12)
            border.width: 1
            border.color: Qt.rgba(0.85, 0.33, 0.10, 0.45)

            Accessible.role: Accessible.StaticText
            Accessible.name: encryptionHint.text

            Label {
                id: encryptionHint

                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: root.tr("If you encrypt the disk, the password cannot have accents or the letter c-cedilla")
                color: palette.windowText
                font.weight: Font.DemiBold
            }
        }

        Item {
            Layout.fillWidth: true
            visible: !root.actionsOnRight && !root.onPartitionStep
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
