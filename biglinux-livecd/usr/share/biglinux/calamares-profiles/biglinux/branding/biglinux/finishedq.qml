import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "i18n.js" as I18n

Page {
    id: root

    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    readonly property string localeKey: Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")
    readonly property bool installationSucceeded: !config.failed

    readonly property color accentColor: installationSucceeded ? "#2E9E63" : "#D08014"
    readonly property color mutedText: Qt.rgba(
        palette.text.r, palette.text.g, palette.text.b, 0.68
    )

    // Drives the entrance: the badge pops in, then the texts settle.
    property real reveal: 0

    function tr(source) { return I18n.translate(source, localeKey) }

    padding: 40
    background: Rectangle { color: root.palette.window }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item { Layout.fillHeight: true }

        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: 520
            spacing: 0

            Rectangle {
                id: badge

                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 104
                Layout.preferredHeight: 104
                radius: width / 2
                color: Qt.rgba(
                    root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.06
                )
                opacity: root.reveal
                scale: 0.86 + 0.14 * root.reveal

                // Pulse ring: a calm "done" beacon, not a spinner.
                Rectangle {
                    id: pulse

                    anchors.centerIn: parent
                    width: parent.width
                    height: parent.height
                    radius: width / 2
                    color: "transparent"
                    border.width: 2
                    border.color: root.accentColor
                    opacity: 0

                    SequentialAnimation {
                        running: root.reveal > 0.9
                        loops: Animation.Infinite

                        ParallelAnimation {
                            NumberAnimation {
                                target: pulse; property: "scale"
                                from: 1.0; to: 1.32; duration: 2000
                                easing.type: Easing.OutCubic
                            }
                            SequentialAnimation {
                                NumberAnimation {
                                    target: pulse; property: "opacity"
                                    from: 0; to: 0.35; duration: 500
                                }
                                NumberAnimation {
                                    target: pulse; property: "opacity"
                                    from: 0.35; to: 0; duration: 1500
                                }
                            }
                        }

                        PauseAnimation { duration: 900 }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 80
                    height: 80
                    radius: width / 2
                    color: Qt.rgba(
                        root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16
                    )

                    Image {
                        anchors.centerIn: parent
                        width: 44
                        height: 44
                        source: root.installationSucceeded
                            ? "visuals/status-check.svg"
                            : "visuals/status-alert.svg"
                        sourceSize.width: width
                        sourceSize.height: height
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                Accessible.role: Accessible.Graphic
                Accessible.name: statusTitle.text
            }

            Label {
                id: statusTitle

                Layout.fillWidth: true
                Layout.topMargin: 24
                opacity: root.reveal
                text: root.installationSucceeded
                    ? root.tr("Installation completed")
                    : root.tr("Installation interrupted")
                color: root.palette.text
                font.pixelSize: 26
                font.weight: Font.Bold
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: 8
                opacity: root.reveal
                text: root.installationSucceeded
                    ? root.tr("BigLinux has been installed on your computer.")
                    : root.tr("The installer encountered an error and will close. Review the error details before trying again.")
                color: root.mutedText
                font.pixelSize: 16
                lineHeight: 1.35
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: 6
                visible: root.installationSucceeded
                text: root.tr("You may restart into the new system or continue using the live environment.")
                color: root.mutedText
                font.pixelSize: 14
                lineHeight: 1.3
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Button {
                id: restartButton

                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 28
                Layout.preferredHeight: 44
                leftPadding: 24
                rightPadding: 24
                visible: root.installationSucceeded
                text: root.tr("Restart system")
                onClicked: config.doRestart(true)

                contentItem: Label {
                    text: restartButton.text
                    color: "white"
                    font.pixelSize: 15
                    font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    radius: 10
                    color: restartButton.down
                        ? Qt.darker(root.palette.highlight, 1.18)
                        : restartButton.hovered
                            ? Qt.lighter(root.palette.highlight, 1.08)
                            : root.palette.highlight
                    border.width: restartButton.visualFocus ? 2 : 0
                    border.color: Qt.lighter(root.palette.highlight, 1.5)

                    Behavior on color {
                        ColorAnimation { duration: 120 }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: 16
                visible: !root.installationSucceeded && text !== ""
                text: config.failureMessage
                color: root.mutedText
                font.pixelSize: 14
                textFormat: Text.StyledText
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }

        Item { Layout.fillHeight: true }

        Label {
            Layout.fillWidth: true
            Layout.maximumWidth: 760
            Layout.alignment: Qt.AlignHCenter
            visible: root.installationSucceeded
            text: root.tr("The installation log is available in the live user's home directory and in /var/log/installation.log on the installed system.")
            color: Qt.rgba(
                root.palette.text.r, root.palette.text.g, root.palette.text.b, 0.45
            )
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }

    NumberAnimation {
        id: entrance

        target: root
        property: "reveal"
        from: 0
        to: 1
        duration: 520
        easing.type: Easing.OutBack
        easing.overshoot: 1.1
    }

    Component.onCompleted: entrance.start()

    function onActivate() {
        reveal = 0
        entrance.restart()
    }
    function onLeave() {}
}
