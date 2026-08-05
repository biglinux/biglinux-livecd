/* BigLinux welcome page for Calamares welcomeq. */
import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "i18n.js" as I18n

Page {
    id: root

    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    property bool activatedInCalamares: true
    readonly property string localeKey: Qt.locale().name + "|" + config.localeIndex + "|" + qsTr("__biglinux_language_marker__")
    readonly property bool animateArtwork: activatedInCalamares && visible

    function tr(source) { return I18n.translate(source, localeKey) }

    function onActivate() {
        activatedInCalamares = true
        intro.restart()
    }

    function onLeave() { activatedInCalamares = false }

    padding: 0
    background: Rectangle { color: root.palette.window }

    FontMetrics { id: appFont; font: Qt.application.font }

    contentItem: Item {
        opacity: 0
        scale: 0.985

        ParallelAnimation {
            id: intro
            NumberAnimation { target: root.contentItem; property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
            NumberAnimation { target: root.contentItem; property: "scale"; from: 0.985; to: 1; duration: 260; easing.type: Easing.OutCubic }
        }

        Component.onCompleted: intro.start()

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 8

            Item { Layout.fillHeight: true; Layout.minimumHeight: 2 }

            Item {
                id: artwork

                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: Math.min(360, root.availableWidth * 0.52)
                Layout.preferredHeight: Math.min(320, root.availableHeight * 0.50)
                Layout.minimumHeight: 190

                readonly property real span: Math.min(width, height)

                Accessible.role: Accessible.Graphic
                Accessible.name: root.tr("BigLinux logo surrounded by slowly moving rings")

                Image {
                    anchors.centerIn: parent
                    width: artwork.span
                    height: width
                    source: "visuals/orbit-glow.svg"
                    sourceSize.width: width
                    sourceSize.height: height
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                // Static tracks: the icons below travel along them, so the
                // ellipses themselves must stay put.
                Repeater {
                    model: [
                        "visuals/orbit-track-a.svg",
                        "visuals/orbit-track-b.svg",
                        "visuals/orbit-track-c.svg"
                    ]

                    Image {
                        anchors.centerIn: parent
                        width: artwork.span
                        height: width
                        source: modelData
                        sourceSize.width: width
                        sourceSize.height: height
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                Image {
                    anchors.centerIn: parent
                    width: artwork.span * 0.38
                    height: width
                    source: "logo-transition.svg"
                    sourceSize.width: width
                    sourceSize.height: height
                    fillMode: Image.PreserveAspectFit
                    smooth: true

                    // A slow breath keeps the brand alive without distracting.
                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        running: root.animateArtwork
                        NumberAnimation { from: 1.0; to: 1.035; duration: 2600; easing.type: Easing.InOutSine }
                        NumberAnimation { from: 1.035; to: 1.0; duration: 2600; easing.type: Easing.InOutSine }
                    }
                }

                // Installation steps orbit the brand. Each chip keeps its own
                // ellipse (matching a track above), phase and period; it never
                // spins, so the icon stays upright all the way around.
                Repeater {
                    model: [
                        { icon: "location", rx: 0.460, ry: 0.305, tilt: -16, period: 28000, phase: 0 },
                        { icon: "users", rx: 0.460, ry: 0.305, tilt: -16, period: 28000, phase: 180 },
                        { icon: "keyboard", rx: 0.425, ry: 0.355, tilt: 24, period: 38000, phase: 60 },
                        { icon: "finish", rx: 0.425, ry: 0.355, tilt: 24, period: 38000, phase: 240 }
                    ]

                    Item {
                        id: orbiter

                        readonly property real chipSize: Math.max(
                            26, Math.round(artwork.span * 0.115)
                        )
                        readonly property real radians: angle * Math.PI / 180
                        readonly property real tiltRadians: modelData.tilt * Math.PI / 180
                        readonly property real ellipseX:
                            modelData.rx * artwork.span * Math.cos(radians)
                        readonly property real ellipseY:
                            modelData.ry * artwork.span * Math.sin(radians)

                        property real angle: modelData.phase

                        width: chipSize
                        height: chipSize
                        x: artwork.width / 2 - width / 2
                            + ellipseX * Math.cos(tiltRadians)
                            - ellipseY * Math.sin(tiltRadians)
                        y: artwork.height / 2 - height / 2
                            + ellipseX * Math.sin(tiltRadians)
                            + ellipseY * Math.cos(tiltRadians)

                        NumberAnimation on angle {
                            from: modelData.phase
                            to: modelData.phase + 360
                            duration: modelData.period
                            loops: Animation.Infinite
                            running: root.animateArtwork
                        }

                        Rectangle {
                            anchors.fill: parent
                            radius: width / 2
                            color: root.palette.base
                            border.width: 1
                            border.color: Qt.rgba(
                                root.palette.text.r,
                                root.palette.text.g,
                                root.palette.text.b,
                                0.10
                            )

                            Image {
                                anchors.centerIn: parent
                                width: parent.width * 0.56
                                height: width
                                source: "icons/" + modelData.icon + "-accent.svg"
                                sourceSize.width: width
                                sourceSize.height: height
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                    }
                }
            }

            Frame {
                Layout.fillWidth: true
                Layout.maximumWidth: 700
                Layout.alignment: Qt.AlignHCenter
                visible: config.requirementsModel && !config.requirementsModel.satisfiedRequirements

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 6

                    Label {
                        Layout.fillWidth: true
                        text: root.tr("Installation requirements need attention")
                        font.weight: Font.DemiBold
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.tr("A required condition is not satisfied. Review the items below before continuing.")
                        wrapMode: Text.WordWrap
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(contentHeight, 96)
                        clip: true
                        spacing: 3
                        model: config.unsatisfiedRequirements
                        interactive: contentHeight > height
                        delegate: Label {
                            required property bool mandatory
                            required property string negatedText
                            width: ListView.view.width
                            text: "• " + negatedText
                            color: mandatory ? root.palette.windowText : root.palette.placeholderText
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true; Layout.minimumHeight: 2 }

            RowLayout {
                Layout.fillWidth: true
                Layout.bottomMargin: 6
                Layout.maximumWidth: 520
                Layout.alignment: Qt.AlignHCenter
                spacing: 10

                Image {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    source: "icons/language-accent.svg"
                    sourceSize.width: 20
                    sourceSize.height: 20
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                Label {
                    text: root.tr("Choose the language")
                    color: root.palette.windowText
                    font.pixelSize: Math.max(14, Math.round(appFont.height * 0.88))
                    font.weight: Font.Medium
                }

                ComboBox {
                    Layout.fillWidth: true
                    textRole: "label"
                    model: config.languagesModel
                    currentIndex: config.localeIndex
                    onActivated: function(index) { config.localeIndex = index }
                    Accessible.name: root.tr("Choose the language")
                }
            }
        }
    }
}
