import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "i18n.js" as I18n

Page {
    id: root

    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    readonly property string localeKey: Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")
    // The shared dictionary is written for BigLinux, and every translation in
    // it carries that product name literally, so swapping the name in keeps a
    // single catalog serving this profile too.
    function tr(source) {
        return I18n.translate(source, localeKey)
            .replace(/BigLinux/g, Branding.string(Branding.ProductName))
    }

    // One badge per step of the summary, in that step's own colour. The order
    // is the show sequence of settings.conf, which is what fills the model.
    function badgeIcon(index) {
        if (index === 0) return "visuals/badge-location.svg"
        if (index === 1) return "visuals/badge-keyboard.svg"
        if (index === 2) return "visuals/badge-partition.svg"
        if (index === 3) return "visuals/badge-users.svg"
        return "visuals/badge-summary.svg"
    }

    function badgeTint(index) {
        if (index === 1) return Qt.rgba(0.55, 0.36, 0.96, 0.16)
        if (index === 2) return Qt.rgba(0.13, 0.63, 0.42, 0.16)
        if (index === 3) return Qt.rgba(0.91, 0.51, 0.23, 0.16)
        return Qt.rgba(0.13, 0.52, 0.82, 0.16)
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
    }

    function messageLines(message) {
        return String(message).split(/<br\s*\/?>/i).filter(function(line) {
            return line.trim() !== ""
        })
    }

    function timeZoneCode() {
        var region = Global.value("locationRegion")
        var zone = Global.value("locationZone")
        if (region === undefined || zone === undefined || region === "" || zone === "") return ""
        return String(region) + "/" + String(zone)
    }

    function cleanSummary(index, message) {
        var lines = messageLines(message)

        if (index === 0) {
            var timezone = timeZoneCode()
            if (timezone !== "") {
                var first = root.tr("Time zone: %1").replace("%1", escapeHtml(timezone))
                return [first].concat(lines.slice(1)).join("<br/>")
            }
        }

        if (index === 1 && lines.length > 1) {
            // The keyboard model status in the bundled translation renders
            // the %1 placeholder as a literal 1. The layout line is the
            // useful choice for the installation review.
            return lines.slice(1).join("<br/>")
        }

        return String(message)
    }


    // Pulled from the installer's translation of the confirmation dialog it
    // replaces; see the frame that uses it below.
    readonly property string undoWarning: {
        const source = "The %1 installer is about to make changes to your disk "
            + "in order to install %2.<br/><strong>You will not be able to "
            + "undo these changes.</strong>"
        const translated = qsTranslate(
            "Calamares::ViewManager",
            source,
            "%1 is short product name, %2 is short product name with version")
        // qsTranslate hands back the source when a language has no
        // translation for it, which is exactly what the dialog itself showed
        // in that case, so the warning is never dropped for want of one.
        const bold = /<strong>(.*?)<\/strong>/.exec(translated)
        return bold ? bold[1] : translated
    }

    padding: 24
    background: Rectangle { color: root.palette.window }

    // Every colour below is the accent at a low alpha over whatever the page
    // background is, so one set of values reads on the light and on the dark
    // palette; a solid panel would have to be maintained twice.
    readonly property color infoTint: Qt.rgba(0.13, 0.52, 0.82, 0.12)
    readonly property color infoLine: Qt.rgba(0.13, 0.52, 0.82, 0.38)
    readonly property color infoMark: "#2185D0"
    readonly property color warnTint: Qt.rgba(0.91, 0.51, 0.13, 0.13)
    readonly property color warnLine: Qt.rgba(0.91, 0.51, 0.13, 0.42)
    readonly property color warnMark: "#E8833A"

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // Only the title. The sentence that used to sit under it repeated
        // what the panel below already says, and every line the heading takes
        // is a line the choices lose - they were losing enough of them to
        // need a scroll bar.
        PageHeader {
            Layout.fillWidth: true
            title: root.tr("Review")
        }

        // Side by side: what is still safe, and what will not be undone. They
        // used to be stacked, which pushed the choices themselves off screen.
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            // Both panels take the taller one's height, so they line up.
            // Layout.fillHeight would do it, except that in a row inside a
            // column it also makes the row itself claim the space the list
            // below needs, and the list ends up with none.
            readonly property real panelHeight:
                Math.max(safePanel.implicitHeight, undoPanel.implicitHeight)

            TintedFrame {
                id: safePanel
                Layout.fillWidth: true
                Layout.preferredHeight: parent.panelHeight
                tint: root.infoTint
                line: root.infoLine

                RowLayout {
                    anchors.fill: parent
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        Layout.alignment: Qt.AlignTop
                        radius: 17
                        color: Qt.rgba(0.13, 0.52, 0.82, 0.22)

                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: "visuals/review-shield.svg"
                            sourceSize.width: width
                            sourceSize.height: height
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Label {
                            Layout.fillWidth: true
                            text: root.tr("Nothing will be changed until you review and confirm.")
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                        }
                        Label {
                            Layout.fillWidth: true
                            text: root.tr("You can still go back and adjust any choice before starting the installation.")
                            color: root.palette.placeholderText
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // The warning that used to sit in the "Continue with Installation?"
            // dialog. That dialog said what this page already says, so it is
            // switched off in settings.conf and the one sentence worth keeping
            // moved here, above the list that scrolls: below it, the warning
            // could be scrolled out of sight.
            //
            // The sentence is borrowed from the installer's own catalogue
            // rather than translated again: it is the bold half of the
            // dialog's question, so the translation already exists in every
            // language Calamares ships.
            TintedFrame {
                id: undoPanel
                Layout.fillWidth: true
                Layout.preferredHeight: parent.panelHeight
                tint: root.warnTint
                line: root.warnLine

                RowLayout {
                    anchors.fill: parent
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        Layout.alignment: Qt.AlignTop
                        radius: 17
                        color: Qt.rgba(0.91, 0.51, 0.13, 0.22)

                        Image {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            source: "visuals/status-alert.svg"
                            sourceSize.width: width
                            sourceSize.height: height
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        text: root.undoWarning
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: config.message !== ""
            text: config.message
            color: root.palette.placeholderText
            wrapMode: Text.WordWrap
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: config.summaryModel
            clip: true
            spacing: 8
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: TintedFrame {
                required property int index
                required property string title
                required property string message

                width: ListView.view.width
                padding: 12

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        Layout.alignment: Qt.AlignTop
                        radius: 20
                        color: root.badgeTint(index)

                        Image {
                            anchors.centerIn: parent
                            width: 22
                            height: 22
                            source: root.badgeIcon(index)
                            sourceSize.width: width
                            sourceSize.height: height
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            Layout.fillWidth: true
                            text: title
                            font.pixelSize: Math.max(16, Math.round(Qt.application.font.pointSize * 1.45))
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                        }
                        Label {
                            Layout.fillWidth: true
                            text: root.cleanSummary(index, message)
                            textFormat: Text.RichText
                            wrapMode: Text.WordWrap
                            onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                        }
                    }
                }
            }
        }
    }
}
