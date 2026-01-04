import QtQuick 2.15

Item {
    property int row
    property int column
    property bool isMine
    property bool isOpened
    property bool isFlagged
    property int neighborMines
    signal leftClick
    signal rightClick

    Rectangle {
        width: parent.width
        height: parent.height
        border.color: "black"
        color: isOpened ? "lightgrey" : (isFlagged ? "white" : "grey")

        MouseArea {
                acceptedButtons: Qt.LeftButton | Qt.RightButton
            anchors.fill: parent
            onClicked: {
                if (mouse.button === Qt.LeftButton && !isFlagged) {
                    leftClick()
                } 
                if (mouse.button === Qt.RightButton) {
                    rightClick()
                }
            }

        }

        Text {
            anchors.centerIn: parent
            text: isOpened ? (isMine ? "💣" : (neighborMines > 0 ? neighborMines : "")) : (isFlagged ? "🚩" : "")
            font.pointSize: 20
            color: isMine ? "red" : "black"
        }
    }
}
