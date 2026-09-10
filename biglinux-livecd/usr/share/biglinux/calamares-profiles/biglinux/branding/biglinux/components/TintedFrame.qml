import QtQuick 2.15
import QtQuick.Controls 2.15

// A panel with rounded corners and a colour of its own. It is a Frame, and
// not a Rectangle holding anchored children, because a Frame takes its size
// from its content: with a Rectangle the content ends up taking its size from
// the panel instead, and the panel grows to whatever space is left.
Frame {
    id: root

    property color tint: palette.base
    property color line: palette.mid
    property int cornerRadius: 10

    padding: 13

    background: Rectangle {
        color: root.tint
        border.width: 1
        border.color: root.line
        radius: root.cornerRadius
    }
}
