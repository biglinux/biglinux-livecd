import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15

Window {
    visible: true
    width: 800
    height: 600
    title: "Mines"

    MinesModel {
        id: minesModel
        rows: 15
        columns: 20
        onGameOver: {
            overlay.visible = true
            restartButton.visible = true
        }
    }

    GridView {
        id: gridView
        anchors.fill: parent
        model: minesModel
        cellWidth: width / minesModel.columns
        cellHeight: height / minesModel.rows
        anchors.margins: 5

        delegate: Cell {
            width: gridView.cellWidth
            height: gridView.cellHeight
            row: model.row
            column: model.column
            isMine: model.isMine
            isOpened: model.isOpened
            isFlagged: model.isFlagged
            neighborMines: model.neighborMines
            onLeftClick: minesModel.openCell(row, column)
            onRightClick: minesModel.toggleFlag(row, column)
        }
    }

    Rectangle {
        id: overlay
        anchors.fill: parent
        color: "black"
        opacity: 0.7
        visible: false
    }

    Button {
        id: restartButton
        text: "Restart"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        visible: false
        onClicked: {
            minesModel.initialize()
            overlay.visible = false
            restartButton.visible = false
        }
    }
}
