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
    function tr(source) { return I18n.translate(source, localeKey) }

    function summaryIcon(index) {
        if (index === 0) return "icons/location-content.svg"
        if (index === 1) return "icons/keyboard-content.svg"
        if (index === 2) return "icons/partition-content.svg"
        return "icons/summary-content.svg"
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

    padding: 24
    background: Rectangle { color: root.palette.window }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        PageHeader {
            Layout.fillWidth: true
            title: root.tr("Review")
            description: root.tr("Check the choices below. The disks will not be changed until you confirm the installation.")
        }

        NativeFrame {
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                spacing: 12

                Image {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    source: "visuals/review-shield.svg"
                    fillMode: Image.PreserveAspectFit
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

            delegate: NativeFrame {
                required property int index
                required property string title
                required property string message
                width: ListView.view.width

                RowLayout {
                    anchors.fill: parent
                    spacing: 12

                    Image {
                        Layout.preferredWidth: 38
                        Layout.preferredHeight: 38
                        Layout.alignment: Qt.AlignTop
                        source: root.summaryIcon(index)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
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
