import QtQuick 2.15

ListModel {
    id: minesModel

    property int rows: 15
    property int columns: 20
    signal gameOver()

    function initialize() {
        clearModel()
        generateMines()
        calculateNeighborMines()
    }

    function clearModel() {
        clear()
        for (var row = 0; row < rows; ++row) {
            for (var col = 0; col < columns; ++col) {
                append({
                    row: row,
                    column: col,
                    isMine: false,
                    isOpened: false,
                    isFlagged: false,
                    neighborMines: 0
                })
            }
        }
    }

    function generateMines() {
        var mineCount = 40 // Número de minas
        while (mineCount > 0) {
            var row = Math.floor(Math.random() * rows)
            var col = Math.floor(Math.random() * columns)
            var index = row * columns + col
            if (!get(index).isMine) {
                get(index).isMine = true
                --mineCount
            }
        }
    }

    function calculateNeighborMines() {
        for (var row = 0; row < rows; ++row) {
            for (var col = 0; col < columns; ++col) {
                var index = row * columns + col
                if (!get(index).isMine) {
                    var count = 0
                    for (var i = -1; i <= 1; ++i) {
                        for (var j = -1; j <= 1; ++j) {
                            var r = row + i
                            var c = col + j
                            if (r >= 0 && r < rows && c >= 0 && c < columns) {
                                var neighborIndex = r * columns + c
                                if (get(neighborIndex).isMine) {
                                    ++count
                                }
                            }
                        }
                    }
                    get(index).neighborMines = count
                }
            }
        }
    }

    function openCell(row, column) {
        var index = row * columns + column
        var cell = get(index)
        if (cell.isOpened || cell.isFlagged) {
            return
        }

        var stack = []
        stack.push(cell)

        while (stack.length > 0) {
            var currentCell = stack.pop()
            currentCell.isOpened = true

            if (currentCell.isMine) {
                gameOver()
                return
            }

            if (currentCell.neighborMines === 0) {
                for (var i = -1; i <= 1; ++i) {
                    for (var j = -1; j <= 1; ++j) {
                        var r = currentCell.row + i
                        var c = currentCell.column + j
                        if (r >= 0 && r < rows && c >= 0 && c < columns) {
                            var neighborIndex = r * columns + c
                            var neighborCell = get(neighborIndex)
                            if (!neighborCell.isOpened && !neighborCell.isMine) {
                                stack.push(neighborCell)
                            }
                        }
                    }
                }
            }
        }
    }

    function toggleFlag(row, column) {
        var index = row * columns + column
        var cell = get(index)
        if (!cell.isOpened) {
            cell.isFlagged = !cell.isFlagged
            // Emitir uma mudança no modelo para atualizar a exibição
            set(index, cell)
        }
    }

    Component.onCompleted: initialize()
}
