import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    property alias title: titleLabel.text
    property alias description: descriptionLabel.text
    property color titleColor: palette.windowText
    property color descriptionColor: palette.placeholderText
    spacing: 3

    SystemPalette { id: palette }

    Label {
        id: titleLabel
        Layout.fillWidth: true
        color: root.titleColor
        font.pixelSize: Math.max(22, Math.round(Qt.application.font.pointSize * 2.15))
        font.weight: Font.DemiBold
        wrapMode: Text.WordWrap
        Accessible.role: Accessible.StaticText
    }

    Label {
        id: descriptionLabel
        Layout.fillWidth: true
        color: root.descriptionColor
        font.pixelSize: Math.max(14, Math.round(Qt.application.font.pointSize * 1.28))
        wrapMode: Text.WordWrap
    }
}
