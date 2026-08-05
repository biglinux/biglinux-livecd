import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "i18n.js" as I18n

Rectangle {
    id: root

    // Calamares fixes the sidebar width (qBound(100, fontHeight * 12, 190)),
    // so this is a floor, not a request: the layout must fit ~190 pixels.
    implicitWidth: 190
    Layout.preferredWidth: 190
    Layout.minimumWidth: 190

    // The window background continues behind the steps so the sidebar never
    // clashes with the title bar, which always follows the desktop theme.
    color: palette.window

    readonly property string localeKey:
        Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")
    // Rows share whatever height the panel has left, so the list never
    // scrolls: the logo slot changes the available space between steps.
    readonly property int stepHeight: Math.max(
        46, Math.min(64, Math.floor(stepList.height / root.stepCount))
    )
    readonly property int markerColumnWidth: 34
    readonly property int markerSize: 30

    readonly property int currentStep: Math.max(0, ViewManager.currentStepIndex)
    readonly property int stepCount: Math.max(1, stepList.count)

    property real logoReveal: currentStep > 0 ? 1 : 0

    Behavior on logoReveal {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }

    // The panel is a dark surface on purpose: it separates navigation from
    // the content area while the window keeps the desktop background color.
    readonly property color panelBackground: "#16273C"
    readonly property color panelBorder: Qt.rgba(1, 1, 1, 0.10)
    readonly property color trackDone: "#42C8F5"
    readonly property color currentTint: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22
    )
    readonly property color currentOutline: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.55
    )
    readonly property color hairline: Qt.rgba(1, 1, 1, 0.16)
    readonly property color primaryText: "#FFFFFF"
    readonly property color secondaryText: Qt.rgba(1, 1, 1, 0.74)
    readonly property color mutedText: Qt.rgba(1, 1, 1, 0.50)

    LayoutMirroring.enabled:
        Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    function tr(source) { return I18n.translate(source, localeKey) }

    // Each step shows what it is about. The icons are drawn in white, which
    // is what the dark panel needs on every state.
    function stepIcon(stepIndex) {
        const names = [
            "welcome", "location", "keyboard", "partition",
            "users", "summary", "install", "finish"
        ]
        const name = stepIndex < names.length ? names[stepIndex] : "summary"
        return "icons/" + name + ".svg"
    }

    function firstStepLabel(translatedLabel) {
        const normalized = String(translatedLabel).trim().toLowerCase()
        if (normalized === "welcome") {
            return "Start"
        }
        if (normalized === "bem-vindo" || normalized === "bem-vinda"
                || normalized === "boas-vindas") {
            return "Início"
        }
        return translatedLabel
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    // Stacked outlines stand in for a drop shadow: the live session renders
    // QML in software, where shader based effects are unavailable.
    Repeater {
        model: [
            { inset: -4, alpha: 0.020, radius: 26 },
            { inset: -3, alpha: 0.028, radius: 25 },
            { inset: -2, alpha: 0.038, radius: 24 },
            { inset: -1, alpha: 0.050, radius: 23 }
        ]

        Rectangle {
            anchors.fill: panel
            anchors.margins: modelData.inset
            anchors.topMargin: modelData.inset + 1
            radius: modelData.radius
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(0, 0, 0, modelData.alpha)
        }
    }

    Rectangle {
        id: panel

        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 6
        anchors.topMargin: 14
        anchors.bottomMargin: 14
        radius: 22
        color: root.panelBackground
        border.width: 1
        border.color: root.panelBorder

        // Rounded corners cannot mask an image without shader effects, so the
        // artwork stays inside the corner radius and its shapes fade out
        // before reaching the edges.
        Image {
            id: panelArtwork

            anchors.fill: parent
            anchors.margins: panel.radius / 2
            source: "visuals/sidebar-pattern.svg"
            fillMode: Image.Stretch
            // Rasterize the gradients at their final size: scaling a smaller
            // pixmap leaves visible seams in the software renderer.
            sourceSize.width: Math.max(1, width)
            sourceSize.height: Math.max(1, height)
            smooth: true
        }

        // A one pixel inner highlight reads as a lit edge on a raised surface.
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 1
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 2 * parent.radius
            height: 1
            color: Qt.rgba(1, 1, 1, 0.10)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.topMargin: 18
            anchors.bottomMargin: 14
            spacing: 0

            // The product logo slides in once the welcome page hands over,
            // where the brand no longer occupies the content area.
            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 72
                Layout.preferredHeight: Math.round(70 * root.logoReveal)

                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    width: 68
                    height: 68
                    opacity: root.logoReveal
                    y: parent.height - height - 8 - (1 - root.logoReveal) * 14
                    scale: 0.88 + 0.12 * root.logoReveal
                    source: Branding.imagePath(Branding.ProductLogo)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: true

                    Accessible.role: Accessible.Graphic
                    Accessible.name:
                        qsTr("%1 logo").arg(Branding.shortProductName())
                }
            }

            ListView {
                id: stepList

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.topMargin: 12
                Layout.leftMargin: 4
                Layout.rightMargin: 4

                model: ViewManager
                clip: true
                spacing: 0
                interactive: contentHeight > height
                boundsBehavior: Flickable.StopAtBounds
                currentIndex: root.currentStep

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                delegate: Item {
                    id: stepDelegate

                    readonly property bool isCurrent: index === root.currentStep
                    readonly property bool isCompleted: index < root.currentStep

                    width: ListView.view ? ListView.view.width : 0
                    height: root.stepHeight

                    Accessible.role: Accessible.ListItem
                    Accessible.name: stepLabel.text
                    Accessible.description: {
                        if (isCurrent) {
                            return qsTr("Current installation step")
                        }
                        if (isCompleted) {
                            return qsTr("Completed installation step")
                        }
                        return qsTr("Pending installation step")
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.topMargin: 3
                        anchors.bottomMargin: 3
                        radius: 13
                        visible: stepDelegate.isCurrent
                        color: root.currentTint
                        border.width: 1
                        border.color: root.currentOutline
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        spacing: 7

                        Item {
                            Layout.preferredWidth: root.markerColumnWidth
                            Layout.fillHeight: true

                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.top: parent.top
                                height: (parent.height - root.markerSize) / 2
                                width: 2
                                visible: index > 0
                                color: stepDelegate.isCompleted
                                    || stepDelegate.isCurrent
                                    ? root.trackDone
                                    : root.hairline
                            }

                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                height: (parent.height - root.markerSize) / 2
                                width: 2
                                visible: index < stepList.count - 1
                                color: stepDelegate.isCompleted
                                    ? root.trackDone
                                    : root.hairline
                            }

                            Rectangle {
                                anchors.centerIn: parent
                                width: root.markerSize
                                height: root.markerSize
                                radius: width / 2
                                color: stepDelegate.isCurrent
                                    ? palette.highlight
                                    : stepDelegate.isCompleted
                                        ? Qt.rgba(
                                            palette.highlight.r,
                                            palette.highlight.g,
                                            palette.highlight.b,
                                            0.85
                                        )
                                        : Qt.rgba(1, 1, 1, 0.06)
                                border.width: stepDelegate.isCurrent
                                    || stepDelegate.isCompleted ? 0 : 1
                                border.color: root.hairline

                                // An SVG check instead of a "✓" glyph: the
                                // glyph comes from whatever fallback font the
                                // live session picks and sits off-center.
                                Image {
                                    anchors.centerIn: parent
                                    width: 15
                                    height: 15
                                    visible: stepDelegate.isCompleted
                                    source: "icons/check.svg"
                                    sourceSize.width: width
                                    sourceSize.height: height
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                }

                                Image {
                                    anchors.centerIn: parent
                                    width: 17
                                    height: 17
                                    visible: !stepDelegate.isCompleted
                                    opacity: stepDelegate.isCurrent ? 1.0 : 0.7
                                    source: root.stepIcon(index)
                                    sourceSize.width: width
                                    sourceSize.height: height
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 1

                            Label {
                                id: stepLabel

                                Layout.fillWidth: true
                                text: index === 0
                                    ? root.firstStepLabel(display)
                                    : display
                                color: stepDelegate.isCurrent
                                    ? root.primaryText
                                    : root.secondaryText
                                font.pixelSize: 14
                                font.letterSpacing: 0.15
                                font.weight: stepDelegate.isCurrent
                                    ? Font.DemiBold
                                    : Font.Normal
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.topMargin: 12
                Layout.preferredHeight: 1
                color: root.hairline
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 12
                text: "www.biglinux.com.br"
                color: root.trackDone
                font.pixelSize: 12
            }
        }
    }

}
