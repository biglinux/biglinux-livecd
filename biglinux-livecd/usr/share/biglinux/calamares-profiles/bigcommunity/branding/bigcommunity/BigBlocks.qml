import QtQuick 6.5
import QtQuick.Controls 6.5
import QtQuick.Shapes 6.5
import Qt.labs.settings 1.0

Item {
    id: root
    width: Math.max(700, parent ? parent.width : 700)
    height: Math.max(700, parent ? parent.height : 700)
    focus: true
    
    // Game constants
    readonly property string gameVersion: "1.0.0"
    readonly property string gameName: "Big Blocks"
    readonly property int gridWidth: 10
    readonly property int gridHeight: 20
    readonly property int cellSize: Math.max(25, Math.min((height - 100) / gridHeight, 35))
    readonly property int boardWidth: gridWidth * cellSize
    readonly property int boardHeight: gridHeight * cellSize
    readonly property int previewSize: 4
    
    // Game state
    property int score: 0
    property var topScores: [0, 0, 0, 0, 0]  // Top 5 scores
    property int level: 1
    property int linesCleared: 0
    property int combo: 0
    property int dropSpeed: 1000
    property bool gameRunning: false
    property bool gamePaused: false
    property bool gameOver: false
    property bool slideshowActive: false
    property real gameSpeed: 1.0
    
    // Special powers
    property int bigLinuxPower: 0
    property int maxBigLinuxPower: 100
    property bool superModeActive: false
    property int superModeTime: 0
    
    // Grid data (0 = empty, 1-7 = different distro blocks)
    property var grid: []
    property var gridColors: []
    
    // Current piece
    property var currentPiece: null
    property int currentPieceType: 0
    property int currentX: 4
    property int currentY: 0
    property int currentRotation: 0
    property int ghostY: 0
    
    // Next pieces queue
    property var nextPieces: []
    property int holdPiece: -1
    property bool holdUsed: false
    
    // Statistics
    property var stats: ({
        pieces: 0,
        perfect: 0,
        combos: 0,
        maxCombo: 0,
        superUses: 0
    })

    // Session stats - persist during game
    property var sessionStats: ({
        pieces: 0,
        perfect: 0,
        combos: 0,
        maxCombo: 0,
        superUses: 0
    })
    
    // Distro themes for pieces
    readonly property var distroThemes: [
        {name: "Ubuntu", color: "#E95420", symbol: "U", ability: "orange_cascade"},
        {name: "Debian", color: "#D70A53", symbol: "D", ability: "stable_foundation"},
        {name: "Fedora", color: "#294172", symbol: "F", ability: "blue_wave"},
        {name: "Arch", color: "#1793D1", symbol: "A", ability: "precision_drop"},
        {name: "Mint", color: "#87CF3E", symbol: "M", ability: "fresh_clear"},
        {name: "openSUSE", color: "#73BA25", symbol: "S", ability: "chameleon_shift"},
        {name: "BigLinux", color: "#FFD700", symbol: "B", ability: "SUPER_POWER"}
    ]
    
    // Piece shapes (different from traditional to avoid copyright)
    readonly property var pieceShapes: [
        // Ubuntu - Orange L
        [[1,0,0],[1,1,1],[0,0,0]],
        // Debian - Red Z
        [[1,1,0],[0,1,1],[0,0,0]],
        // Fedora - Blue T
        [[0,1,0],[1,1,1],[0,0,0]],
        // Arch - Cyan Line
        [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],
        // Mint - Green S
        [[0,1,1],[1,1,0],[0,0,0]],
        // openSUSE - Square
        [[1,1],[1,1]],
        // BigLinux - Special Cross (POWER PIECE!)
        [[0,1,0],[1,1,1],[0,1,0]]
    ]
    
    // Visual effects
    property var particles: []
    property var explosions: []
    property var floatingTexts: []
    property bool hasActiveAnimations: particles.length > 0 || floatingTexts.length > 0

    // Settings for persistence
    Settings {
        id: gameSettings
        property alias savedTopScores: root.topScores
    }

    function loadTopScores() {
        if (gameSettings.savedTopScores && gameSettings.savedTopScores.length === 5) {
            topScores = gameSettings.savedTopScores;
        }
    }

    function saveTopScores() {
        gameSettings.savedTopScores = topScores;
    }

    function updateTopScores(newScore) {
        var newTopScores = topScores.slice();
        
        // Find position to insert new score
        for (var i = 0; i < 5; i++) {
            if (newScore > newTopScores[i]) {
                // Insert new score and shift others down
                newTopScores.splice(i, 0, newScore);
                newTopScores = newTopScores.slice(0, 5); // Keep only top 5
                break;
            }
        }
        
        topScores = newTopScores;
        saveTopScores();
        return i < 5; // Return true if score made it to top 5
    }
    
    // Background
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a0e27" }
            GradientStop { position: 0.5; color: "#151933" }
            GradientStop { position: 1.0; color: "#0a0e27" }
        }
        
        // Animated background particles (reduced count, slower animations)
        Repeater {
            model: 8
            Rectangle {
                width: 2
                height: 2
                radius: 1
                color: Qt.rgba(0.5, 0.7, 1, 0.25)
                x: Math.random() * root.width
                y: Math.random() * root.height
                
                SequentialAnimation on y {
                    loops: Animation.Infinite
                    NumberAnimation {
                        from: root.height + 10
                        to: -10
                        duration: 20000 + Math.random() * 30000
                    }
                }
            }
        }
    }
    
    // Game container to center both panels
    Item {
        id: gameContainer
        width: boardWidth + 30 + 250
        height: Math.min(boardHeight, root.height - 80)
        anchors.centerIn: parent
    
        // Main game board
        Item {
            id: gameBoard
            width: boardWidth
            height: boardHeight
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            
            // Board background
            Rectangle {
                anchors.fill: parent
                color: Qt.rgba(0, 0, 0, 0.7)
                border.color: "#333"
                border.width: 2
            }
            
            // Grid lines (static — painted once)
            Canvas {
                id: gridCanvas
                anchors.fill: parent
                opacity: 0.1
                renderStrategy: Canvas.Cooperative
                
                onPaint: {
                    var ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    ctx.strokeStyle = "white";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    
                    for (var x = 0; x <= gridWidth; x++) {
                        ctx.moveTo(x * cellSize, 0);
                        ctx.lineTo(x * cellSize, height);
                    }
                    for (var y = 0; y <= gridHeight; y++) {
                        ctx.moveTo(0, y * cellSize);
                        ctx.lineTo(width, y * cellSize);
                    }
                    ctx.stroke();
                }
            }
            
            // Placed blocks
            Repeater {
                model: gridHeight * gridWidth
                
                Rectangle {
                    property int row: Math.floor(index / gridWidth)
                    property int col: index % gridWidth
                    property int cellValue: grid[row] ? grid[row][col] : 0
                    
                    x: col * cellSize
                    y: row * cellSize
                    width: cellSize
                    height: cellSize
                    color: cellValue > 0 && cellValue <= distroThemes.length ?
                        distroThemes[cellValue - 1].color : "transparent"
                    border.color: cellValue > 0 ? Qt.lighter(color, 1.5) : "transparent"
                    border.width: cellValue > 0 ? 1 : 0
                    visible: cellValue > 0
                    
                    // Distro symbol
                    Text {
                        anchors.centerIn: parent
                        text: parent.cellValue > 0 && parent.cellValue <= distroThemes.length ?
                            distroThemes[parent.cellValue - 1].symbol : ""
                        color: "white"
                        font.pixelSize: cellSize * 0.5
                        font.bold: true
                        opacity: 0.7
                        visible: parent.cellValue > 0
                    }
                    
                    // Static glow for BigLinux blocks (no animation)
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.color: "gold"
                        border.width: 2
                        opacity: parent.cellValue === 7 ? 0.6 : 0
                        visible: parent.cellValue === 7
                    }
                }
            }
            
            // Ghost piece (preview of where piece will land)
            Repeater {
                model: currentPiece ? currentPiece.length * currentPiece[0].length : 0
                
                Rectangle {
                    property int row: Math.floor(index / currentPiece[0].length)
                    property int col: index % currentPiece[0].length
                    property bool isBlock: currentPiece[row][col] === 1
                    
                    x: (currentX + col) * cellSize
                    y: (ghostY + row) * cellSize
                    width: cellSize
                    height: cellSize
                    color: "white"
                    opacity: isBlock ? 0.2 : 0
                    border.color: "white"
                    border.width: 1
                    visible: isBlock && gameRunning && !gamePaused
                }
            }
            
            // Current falling piece
            Repeater {
                model: currentPiece ? currentPiece.length * currentPiece[0].length : 0
                
                Rectangle {
                    property int row: Math.floor(index / currentPiece[0].length)
                    property int col: index % currentPiece[0].length
                    property bool isBlock: currentPiece[row][col] === 1
                    property int pieceType: currentPieceType
                    
                    x: (currentX + col) * cellSize
                    y: (currentY + row) * cellSize
                    width: cellSize
                    height: cellSize
                    color: isBlock && pieceType >= 0 && pieceType < distroThemes.length ? 
                        distroThemes[pieceType].color : "transparent"
                    border.color: isBlock ? Qt.lighter(color, 1.5) : "transparent"
                    border.width: 1
                    visible: isBlock && gameRunning
                    
                    // Symbol
                    Text {
                        anchors.centerIn: parent
                        text: parent.pieceType >= 0 && parent.pieceType < distroThemes.length ? 
                            distroThemes[parent.pieceType].symbol : ""
                        color: "white"
                        font.pixelSize: cellSize * 0.5
                        font.bold: true
                        opacity: 0.7
                        visible: parent.isBlock
                    }
                    
                    // Static glow for BigLinux piece (no animation)
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.color: "gold"
                        border.width: 2
                        opacity: parent.pieceType === 6 ? 0.7 : 0
                        visible: parent.isBlock && parent.pieceType === 6
                    }
                }
            }
            
            // Line clear animation
            Rectangle {
                id: lineClearEffect
                width: parent.width
                height: cellSize
                color: "white"
                opacity: 0
                
                SequentialAnimation {
                    id: lineClearAnimation
                    
                    PropertyAnimation {
                        target: lineClearEffect
                        property: "opacity"
                        to: 0.8
                        duration: 100
                    }
                    PropertyAnimation {
                        target: lineClearEffect
                        property: "opacity"
                        to: 0
                        duration: 300
                    }
                }
            }
        }
        
        // Side panel
        Rectangle {
            id: sidePanel
            width: 250
            height: boardHeight
            anchors.left: gameBoard.right
            anchors.leftMargin: 30
            anchors.verticalCenter: parent.verticalCenter
            color: Qt.rgba(0, 0, 0, 0.5)
            border.color: "#333"
            border.width: 2
            
            Column {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 20
                
                // Score
                Column {
                    width: parent.width
                    spacing: 5
                    
                    Text {
                        text: "SCORE"
                        color: "#888"
                        font.pixelSize: 14
                        font.family: "monospace"
                    }
                    Text {
                        text: score.toString().padStart(8, '0')
                        color: "white"
                        font.pixelSize: 24
                        font.bold: true
                        font.family: "monospace"
                    }
                }
                
                // Level
                Column {
                    width: parent.width
                    spacing: 5
                    
                    Text {
                        text: "LEVEL"
                        color: "#888"
                        font.pixelSize: 14
                        font.family: "monospace"
                    }
                    Text {
                        text: level
                        color: "yellow"
                        font.pixelSize: 24
                        font.bold: true
                        font.family: "monospace"
                    }
                }
                
                // Lines
                Column {
                    width: parent.width
                    spacing: 5
                    
                    Text {
                        text: "LINES"
                        color: "#888"
                        font.pixelSize: 14
                        font.family: "monospace"
                    }
                    Text {
                        text: linesCleared
                        color: "cyan"
                        font.pixelSize: 24
                        font.bold: true
                        font.family: "monospace"
                    }
                }
                
                // Next and Hold pieces side by side
                Row {
                    width: parent.width
                    spacing: 10

                    // Next piece preview
                    Column {
                        width: (parent.width - 10) / 2
                        spacing: 5
                        
                        Text {
                            text: "NEXT"
                            color: "#888"
                            font.pixelSize: 14
                            font.family: "monospace"
                        }
                        
                        Rectangle {
                            width: previewSize * 15
                            height: previewSize * 15
                            color: Qt.rgba(0, 0, 0, 0.3)
                            border.color: "#333"
                            
                            Grid {
                                anchors.centerIn: parent
                                rows: 4
                                columns: 4
                                
                                Repeater {
                                    model: 16
                                    
                                    Rectangle {
                                        property int row: Math.floor(index / 4)
                                        property int col: index % 4
                                        property bool isBlock: {
                                            if (nextPieces.length > 0) {
                                                var shape = pieceShapes[nextPieces[0]];
                                                if (row < shape.length && col < shape[0].length) {
                                                    return shape[row][col] === 1;
                                                }
                                            }
                                            return false;
                                        }
                                        
                                        width: 12
                                        height: 12
                                        color: {
                                            if (isBlock && nextPieces.length > 0) {
                                                return distroThemes[nextPieces[0]].color;
                                            }
                                            return "transparent";
                                        }
                                        border.color: isBlock ? Qt.lighter(color, 1.5) : "transparent"
                                        border.width: 1
                                    }
                                }
                            }
                        }
                    }

                    // Hold piece
                    Column {
                        width: parent.width
                        spacing: 5
                        
                        Text {
                            text: "HOLD (C key)"
                            color: "#888"
                            font.pixelSize: 14
                            font.family: "monospace"
                        }
                        
                        Rectangle {
                            width: previewSize * 15
                            height: previewSize * 15
                            color: Qt.rgba(0, 0, 0, 0.3)
                            border.color: holdUsed ? "#666" : "#333"
                            
                            Grid {
                                anchors.centerIn: parent
                                rows: 4
                                columns: 4
                                opacity: holdUsed ? 0.5 : 1.0
                                
                                Repeater {
                                    model: 16
                                    
                                    Rectangle {
                                        property int row: Math.floor(index / 4)
                                        property int col: index % 4
                                        property bool isBlock: {
                                            if (holdPiece >= 0) {
                                                var shape = pieceShapes[holdPiece];
                                                if (row < shape.length && col < shape[0].length) {
                                                    return shape[row][col] === 1;
                                                }
                                            }
                                            return false;
                                        }
                                        
                                        width: 12
                                        height: 12
                                        color: {
                                            if (isBlock && holdPiece >= 0) {
                                                return distroThemes[holdPiece].color;
                                            }
                                            return "transparent";
                                        }
                                        border.color: isBlock ? Qt.lighter(color, 1.5) : "transparent"
                                        border.width: 1
                                    }
                                }
                            }
                        }
                    }
                }
                
                // BigLinux Power Meter
                Column {
                    width: parent.width
                    spacing: 5
                    
                    Text {
                        text: "BIGLINUX POWER"
                        color: "#FFD700"
                        font.pixelSize: 14
                        font.bold: true
                        font.family: "monospace"
                    }
                    
                    Rectangle {
                        width: parent.width - 20
                        height: 30
                        color: "transparent"
                        border.color: "#FFD700"
                        border.width: 2
                        radius: 5
                        
                        Rectangle {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 3
                            width: (parent.width - 6) * (bigLinuxPower / maxBigLinuxPower)
                            height: parent.height - 6
                            radius: 3
                            
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "#FFD700" }
                                GradientStop { position: 1.0; color: "#FFA500" }
                            }
                            
                            Behavior on width {
                                NumberAnimation { duration: 200 }
                            }
                        }
                        
                        Text {
                            anchors.centerIn: parent
                            text: bigLinuxPower + "%"
                            color: "white"
                            font.pixelSize: 14
                            font.bold: true
                            font.family: "monospace"
                        }
                    }
                    
                    Text {
                        text: bigLinuxPower >= maxBigLinuxPower ? "Press SPACE!" : "Clear lines to charge"
                        color: bigLinuxPower >= maxBigLinuxPower ? "lime" : "#888"
                        font.pixelSize: 10
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                        
                        SequentialAnimation on opacity {
                            running: bigLinuxPower >= maxBigLinuxPower
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.3; duration: 1000 }
                            NumberAnimation { to: 1.0; duration: 1000 }
                        }
                    }
                }
            }
        }
    }
    
    // Top HUD
    Rectangle {
        id: topHud
        width: parent.width
        height: 40
        color: Qt.rgba(0, 0, 0, 0.7)
        
        Row {
            anchors.centerIn: parent
            spacing: 50
            
            // Best Score
            Row {
                spacing: 10
                Text {
                    text: "BEST:"
                    color: "#888"
                    font.pixelSize: 16
                    font.family: "monospace"
                }
                Text {
                    text: topScores[0].toString().padStart(8, '0')
                    color: "#FFD700"
                    font.pixelSize: 16
                    font.bold: true
                    font.family: "monospace"
                }
            }
            
            // Combo
            Row {
                spacing: 10
                visible: combo > 0
                
                Text {
                    text: "COMBO:"
                    color: "#888"
                    font.pixelSize: 16
                    font.family: "monospace"
                }
                Text {
                    text: "x" + combo
                    color: "orange"
                    font.pixelSize: 16
                    font.bold: true
                    font.family: "monospace"
                    
                    SequentialAnimation on scale {
                        running: combo > 0
                        NumberAnimation { to: 1.3; duration: 100 }
                        NumberAnimation { to: 1.0; duration: 100 }
                    }
                }
            }
        }
    }
    
    // Start screen
    Rectangle {
        id: startScreen
        anchors.fill: parent
        color: "#0a0e27"
        visible: true
        z: 100

        // Click area to start game
        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (startScreen.visible) {
                    resetGame();
                }
            }
            cursorShape: Qt.PointingHandCursor
        }
        
        Column {
            anchors.centerIn: parent
            spacing: 30
            
            // Title
            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 10
                
                Text {
                    text: "BIG BLOCKS"
                    font.pixelSize: 42
                    font.bold: true
                    font.family: "monospace"
                    color: "#FFD700"
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    SequentialAnimation on scale {
                        running: startScreen.visible
                        loops: Animation.Infinite
                        NumberAnimation { to: 1.03; duration: 3000; easing.type: Easing.InOutQuad }
                        NumberAnimation { to: 1.0; duration: 3000; easing.type: Easing.InOutQuad }
                    }
                }
                
                Text {
                    text: "Powered by BigCommunity"
                    font.pixelSize: 16
                    font.family: "monospace"
                    color: "#888"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
            
            // Instructions
            Rectangle {
                width: Math.min(500, root.width - 100)
                height: Math.min(320, root.height * 0.5)
                color: Qt.rgba(0, 0, 0, 0.5)
                border.color: "#333"
                radius: 10
                
                Column {
                    anchors.centerIn: parent
                    spacing: 10
                    
                    Text {
                        text: "CONTROLS"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    
                    Grid {
                        columns: 2
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter
                        
                        Text { text: "Move:"; color: "#888"; font.family: "monospace" }
                        Text { text: "← → Arrow Keys"; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Rotate:"; color: "#888"; font.family: "monospace" }
                        Text { text: "↑ Arrow / Z"; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Soft Drop:"; color: "#888"; font.family: "monospace" }
                        Text { text: "↓ Arrow"; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Hard Drop:"; color: "#888"; font.family: "monospace" }
                        Text { text: "Spacebar (when not powered)"; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Hold:"; color: "#888"; font.family: "monospace" }
                        Text { text: "C Key"; color: "white"; font.family: "monospace" }
                        
                        Text { text: "BigLinux Power:"; color: "#FFD700"; font.family: "monospace" }
                        Text { text: "Spacebar (when charged)"; color: "#FFD700"; font.family: "monospace" }
                        
                        Text { text: "Pause:"; color: "#888"; font.family: "monospace" }
                        Text { text: "P"; color: "white"; font.family: "monospace" }

                        Text { text: "Top Scores:"; color: "#888"; font.family: "monospace" }
                        Text { text: "T Key"; color: "white"; font.family: "monospace" }
                    }
                }
            }
            
            // Distro showcase
            Rectangle {
                width: Math.min(500, root.width - 100)
                height: 80
                color: Qt.rgba(0, 0, 0, 0.5)
                border.color: "#333"
                radius: 10
                
                Row {
                    anchors.centerIn: parent
                    spacing: 15
                    
                    Repeater {
                        model: distroThemes.length
                        
                        Column {
                            spacing: 5
                            
                            Rectangle {
                                width: 40
                                height: 40
                                color: distroThemes[index].color
                                border.color: Qt.lighter(color, 1.5)
                                border.width: 2
                                radius: 5
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: distroThemes[index].symbol
                                    color: "white"
                                    font.pixelSize: 20
                                    font.bold: true
                                }
                            }
                            
                            Text {
                                text: distroThemes[index].name
                                color: "#888"
                                font.pixelSize: 9
                                font.family: "monospace"
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }
                }
            }
            
            // Start button
            Text {
                text: "Click to Start"
                font.pixelSize: 24
                font.family: "monospace"
                color: "lime"
                anchors.horizontalCenter: parent.horizontalCenter
                
                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 800 }
                    NumberAnimation { to: 1.0; duration: 800 }
                }
            }
        }
    }
    
    // Pause screen
    Rectangle {
        id: pauseScreen
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.8)
        visible: gamePaused
        z: 90
        
        Column {
            anchors.centerIn: parent
            spacing: 20
            
            Text {
                text: "PAUSED"
                font.pixelSize: 36
                font.bold: true
                font.family: "monospace"
                color: "white"
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Text {
                text: "Press P to Continue"
                font.pixelSize: 18
                font.family: "monospace"
                color: "#888"
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            // Current stats
            Rectangle {
                width: Math.min(300, root.width - 100)
                height: Math.min(200, root.height * 0.3)
                color: Qt.rgba(0, 0, 0, 0.5)
                border.color: "#333"
                radius: 10
                
                Column {
                    anchors.centerIn: parent
                    spacing: 10
                    
                    Text {
                        text: "Current Session"
                        color: "yellow"
                        font.pixelSize: 16
                        font.bold: true
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    
                    Grid {
                        columns: 2
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter
                        
                        Text { text: "Pieces:"; color: "#888"; font.family: "monospace" }
                        Text { text: sessionStats.pieces; color: "white"; font.family: "monospace" }

                        Text { text: "Perfect Clears:"; color: "#888"; font.family: "monospace" }
                        Text { text: sessionStats.perfect; color: "white"; font.family: "monospace" }

                        Text { text: "Max Combo:"; color: "#888"; font.family: "monospace" }
                        Text { text: sessionStats.maxCombo; color: "white"; font.family: "monospace" }

                        Text { text: "Super Uses:"; color: "#888"; font.family: "monospace" }
                        Text { text: sessionStats.superUses; color: "white"; font.family: "monospace" }
                    }
                }
            }
        }
    }
    
    // Game Over screen
    Rectangle {
        id: gameOverScreen
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.9)
        visible: false
        z: 95
        
        Column {
            anchors.centerIn: parent
            spacing: 30
            
            Text {
                text: "GAME OVER"
                font.pixelSize: 48
                font.bold: true
                font.family: "monospace"
                color: "red"
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            // Final stats
            Rectangle {
                width: Math.min(350, root.width - 100)
                height: Math.min(250, root.height * 0.4)
                color: Qt.rgba(0, 0, 0, 0.5)
                border.color: "#333"
                radius: 10
                
                Column {
                    anchors.centerIn: parent
                    spacing: 15
                    
                    Text {
                        text: "Final Statistics"
                        color: "yellow"
                        font.pixelSize: 18
                        font.bold: true
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    
                    Text {
                        text: "Score: " + score
                        color: "white"
                        font.pixelSize: 24
                        font.bold: true
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    
                    Text {
                        text: {
                            for (var i = 0; i < 5; i++) {
                                if (score === topScores[i]) {
                                    if (i === 0) return "NEW BEST SCORE!";
                                    return "TOP " + (i + 1) + " SCORE!";
                                }
                            }
                            return "";
                        }
                        color: "gold"
                        font.pixelSize: 20
                        font.bold: true
                        font.family: "monospace"
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: text !== ""
                        
                        SequentialAnimation on scale {
                            running: visible
                            loops: Animation.Infinite
                            NumberAnimation { to: 1.2; duration: 500 }
                            NumberAnimation { to: 1.0; duration: 500 }
                        }
                    }
                    
                    Grid {
                        columns: 2
                        spacing: 15
                        anchors.horizontalCenter: parent.horizontalCenter
                        
                        Text { text: "Level:"; color: "#888"; font.family: "monospace" }
                        Text { text: level; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Lines:"; color: "#888"; font.family: "monospace" }
                        Text { text: linesCleared; color: "white"; font.family: "monospace" }
                        
                        Text { text: "Max Combo:"; color: "#888"; font.family: "monospace" }
                        Text { text: sessionStats.maxCombo; color: "white"; font.family: "monospace" }
                    }
                }
            }
            
            Text {
                text: "Press ENTER to Play Again"
                font.pixelSize: 20
                font.family: "monospace"
                color: "lime"
                anchors.horizontalCenter: parent.horizontalCenter
                
                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 800 }
                    NumberAnimation { to: 1.0; duration: 800 }
                }
            }
        }
    }

    // Top 5 Scores screen
    Rectangle {
        id: topScoresScreen
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.9)
        visible: false
        z: 101
        
        Column {
            anchors.centerIn: parent
            spacing: 30
            
            Text {
                text: "TOP 5 SCORES"
                font.pixelSize: 36
                font.bold: true
                font.family: "monospace"
                color: "#FFD700"
                anchors.horizontalCenter: parent.horizontalCenter
            }
            
            Column {
                spacing: 15
                anchors.horizontalCenter: parent.horizontalCenter
                
                Repeater {
                    model: 5
                    
                    Row {
                        spacing: 20
                        anchors.horizontalCenter: parent.horizontalCenter
                        
                        Text {
                            text: "#" + (index + 1)
                            color: index === 0 ? "#FFD700" : index === 1 ? "#C0C0C0" : index === 2 ? "#CD7F32" : "#888"
                            font.pixelSize: 24
                            font.bold: true
                            font.family: "monospace"
                            width: 50
                        }
                        
                        Text {
                            text: topScores[index].toString().padStart(8, '0')
                            color: "white"
                            font.pixelSize: 24
                            font.family: "monospace"
                        }
                    }
                }
            }
            
            Text {
                text: "Press ESC to return"
                font.pixelSize: 16
                font.family: "monospace"
                color: "#888"
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }
    
    // Super mode overlay
    Rectangle {
        id: superModeOverlay
        anchors.fill: parent
        color: "transparent"
        visible: superModeActive
        z: 80
        
        Rectangle {
            anchors.fill: parent
            color: "gold"
            opacity: superModeActive ? 0.1 : 0
        }
        
        Text {
            anchors.centerIn: parent
            text: "BIGLINUX SUPER MODE!"
            font.pixelSize: 48
            font.bold: true
            font.family: "monospace"
            color: "#FFD700"
            opacity: superModeActive ? 1.0 : 0
            visible: superModeActive
        }
    }
    
    // Floating text animations (simplified)
    Repeater {
        model: floatingTexts.length
        
        Text {
            x: floatingTexts[index] ? floatingTexts[index].x : 0
            y: floatingTexts[index] ? floatingTexts[index].y : 0
            text: floatingTexts[index] ? floatingTexts[index].text : ""
            color: floatingTexts[index] ? floatingTexts[index].color : "white"
            font.pixelSize: 24
            font.bold: true
            font.family: "monospace"
            opacity: floatingTexts[index] ? floatingTexts[index].time / 60.0 : 0
        }
    }
    
    // Main game timer
    Timer {
        id: dropTimer
        interval: dropSpeed
        running: gameRunning && !gamePaused
        repeat: true
        onTriggered: moveDownAuto()
    }
    
    // Animation timer (only active when needed)
    Timer {
        id: animationTimer
        interval: 50 // ~20 FPS — sufficient for particle effects
        running: hasActiveAnimations || superModeActive
        repeat: true
        onTriggered: {
            updateAnimations();
            
            if (superModeActive) {
                superModeTime -= 3; // Compensate for lower tick rate
                if (superModeTime <= 0) {
                    endSuperMode();
                }
            }
        }
    }
    
    // Game functions
    function initGame() {
        // Initialize grid
        grid = [];
        for (var y = 0; y < gridHeight; y++) {
            var row = [];
            for (var x = 0; x < gridWidth; x++) {
                row.push(0);
            }
            grid.push(row);
        }
        
        // Reset game state
        score = 0;
        level = 1;
        linesCleared = 0;
        combo = 0;
        dropSpeed = 1000;
        bigLinuxPower = 0;
        superModeActive = false;
        holdPiece = -1;
        holdUsed = false;
        
        // Reset stats
        stats.pieces = 0;
        stats.perfect = 0;
        stats.combos = 0;
        stats.maxCombo = 0;
        stats.superUses = 0;

        // Reset session stats
        sessionStats.pieces = 0;
        sessionStats.perfect = 0;
        sessionStats.combos = 0;
        sessionStats.maxCombo = 0;
        sessionStats.superUses = 0;
        
        // Initialize piece queue
        nextPieces = [];
        for (var i = 0; i < 5; i++) {
            nextPieces.push(generateRandomPiece());
        }
        
        // Spawn first piece
        spawnPiece();
        
        gameRunning = true;
        gameOver = false;
    }
    
    function generateRandomPiece() {
        // Weighted random - BigLinux piece is rarer
        var weights = [15, 15, 15, 15, 15, 15, 5]; // BigLinux has lower weight
        var totalWeight = weights.reduce(function(a, b) { return a + b; }, 0);
        var random = Math.random() * totalWeight;
        
        var accumulated = 0;
        for (var i = 0; i < weights.length; i++) {
            accumulated += weights[i];
            if (random < accumulated) {
                return i;
            }
        }
        return 0;
    }
    
    function spawnPiece() {
        // Store piece type BEFORE shifting (exactly like debug)
        currentPieceType = nextPieces[0];
        currentPiece = pieceShapes[currentPieceType].map(function(row) {
            return row.slice();
        });
        currentX = Math.floor((gridWidth - currentPiece[0].length) / 2);
        currentY = 0;
        currentRotation = 0;
        
        // Check if piece can spawn
        if (!isValidPosition(currentX, currentY, currentPiece)) {
            endGame();
            return;
        }
        
        // Shift queue AFTER storing type - Force QML binding update
        nextPieces.shift();
        nextPieces.push(generateRandomPiece());
        nextPieces = nextPieces.slice(); // Create new array reference
        
        // Update ghost position
        updateGhostPosition();
        
        stats.pieces++;
        sessionStats.pieces++;

        // Force QML binding update for sessionStats
        sessionStats = Object.assign({}, sessionStats);
    }
    
    function moveLeft() {
        if (isValidPosition(currentX - 1, currentY, currentPiece)) {
            currentX--;
            updateGhostPosition();
        }
    }
    
    function moveRight() {
        if (isValidPosition(currentX + 1, currentY, currentPiece)) {
            currentX++;
            updateGhostPosition();
        }
    }
    
    function moveDown() {
        if (isValidPosition(currentX, currentY + 1, currentPiece)) {
            currentY++;
            return true;
        } else {
            placePiece();
            return false;
        }
    }

    // Automatic movement
    function moveDownAuto() {
        if (isValidPosition(currentX, currentY + 1, currentPiece)) {
            currentY++;
            return true;
        } else {
            placePiece();
            return false;
        }
    }
    
    function hardDrop() {
        var dropped = 0;
        while (isValidPosition(currentX, currentY + 1, currentPiece)) {
            currentY++;
            dropped++;
        }
        score += dropped * 2;
        placePiece();
    }
    
    function rotate() {
        var rotated = [];
        var n = currentPiece.length;
        
        // Create rotated matrix
        for (var i = 0; i < n; i++) {
            rotated[i] = [];
            for (var j = 0; j < n; j++) {
                rotated[i][j] = currentPiece[n - 1 - j][i];
            }
        }
        
        // Try rotation with wall kicks
        var kicks = [
            {x: 0, y: 0},
            {x: -1, y: 0},
            {x: 1, y: 0},
            {x: 0, y: -1},
            {x: -1, y: -1},
            {x: 1, y: -1}
        ];
        
        for (var k = 0; k < kicks.length; k++) {
            if (isValidPosition(currentX + kicks[k].x, currentY + kicks[k].y, rotated)) {
                currentPiece = rotated;
                currentX += kicks[k].x;
                currentY += kicks[k].y;
                currentRotation = (currentRotation + 1) % 4;
                updateGhostPosition();
                break;
            }
        }
    }
    
    function holdPieceFunction() {
        if (holdUsed) return;
        
        var temp = holdPiece;
        holdPiece = nextPieces[0];
        
        if (temp === -1) {
            // First hold
            nextPieces.shift();
            nextPieces.push(generateRandomPiece());
        } else {
            // Swap
            nextPieces[0] = temp;
        }
        nextPieces = nextPieces.slice(); // Create new array reference for QML binding
        
        holdUsed = true;
        spawnPiece();
    }
    
    function isValidPosition(x, y, piece) {
        for (var py = 0; py < piece.length; py++) {
            for (var px = 0; px < piece[py].length; px++) {
                if (piece[py][px] === 1) {
                    var boardX = x + px;
                    var boardY = y + py;
                    
                    if (boardX < 0 || boardX >= gridWidth || 
                        boardY >= gridHeight) {
                        return false;
                    }
                    
                    if (boardY >= 0 && grid[boardY][boardX] !== 0) {
                        return false;
                    }
                }
            }
        }
        return true;
    }
    
    function placePiece() {
        var pieceType = currentPieceType;
        
        // Place piece on grid
        for (var py = 0; py < currentPiece.length; py++) {
            for (var px = 0; px < currentPiece[py].length; px++) {
                if (currentPiece[py][px] === 1) {
                    var boardY = currentY + py;
                    var boardX = currentX + px;
                    
                    if (boardY >= 0) {
                        grid[boardY][boardX] = pieceType + 1;
                    }
                }
            }
        }
        
        // Check for lines
        var lines = checkLines();
        
        if (lines.length > 0) {
            clearLines(lines);
            
            // Update score
            var baseScore = [0, 100, 300, 500, 800];
            var lineScore = baseScore[Math.min(lines.length, 4)] * level;
            
            if (combo > 0) {
                lineScore *= (1 + combo * 0.5);
            }
            
            score += Math.floor(lineScore);
            linesCleared += lines.length;
            combo++;
            
            if (combo > stats.maxCombo) {
                stats.maxCombo = combo;
            }
            if (combo > sessionStats.maxCombo) {
                sessionStats.maxCombo = combo;
                // Force QML binding update for sessionStats
                sessionStats = Object.assign({}, sessionStats);
            }
            
            // Charge BigLinux power
            bigLinuxPower = Math.min(bigLinuxPower + lines.length * 15, maxBigLinuxPower);
            
            // Show floating text
            var comboText = combo > 1 ? " COMBO x" + combo : "";
            showFloatingText(gameBoard.x + gameBoard.width / 2, 
                           gameBoard.y + lines[0] * cellSize,
                           lines.length + " LINES!" + comboText,
                           "yellow");
            
            // Check for perfect clear
            if (isGridEmpty()) {
                score += 1000 * level;
                stats.perfect++;
                sessionStats.perfect++;
                // Force QML binding update for sessionStats
                sessionStats = Object.assign({}, sessionStats);
                showFloatingText(gameBoard.x + gameBoard.width / 2,
                               gameBoard.y + gameBoard.height / 2,
                               "PERFECT CLEAR!",
                               "gold");
            }
            
            // Level up
            if (linesCleared >= level * 10) {
                level++;
                dropSpeed = Math.max(100, 1000 - (level - 1) * 100);
                showFloatingText(gameBoard.x + gameBoard.width / 2,
                               gameBoard.y + gameBoard.height / 2,
                               "LEVEL UP!",
                               "lime");
            }
        } else {
            combo = 0;
        }
        
        // Update grid display
        grid = grid.slice();

        // Reset hold usage for next piece
        holdUsed = false;
        
        // Spawn next piece
        spawnPiece();
    }
    
    function checkLines() {
        var lines = [];
        
        for (var y = 0; y < gridHeight; y++) {
            var complete = true;
            for (var x = 0; x < gridWidth; x++) {
                if (grid[y][x] === 0) {
                    complete = false;
                    break;
                }
            }
            if (complete) {
                lines.push(y);
            }
        }
        
        return lines;
    }
    
    function clearLines(lines) {
        // Animate line clear
        for (var i = 0; i < lines.length; i++) {
            lineClearEffect.y = gameBoard.y + lines[i] * cellSize;
            lineClearAnimation.start();
        }
        
        // Remove lines
        for (var i = lines.length - 1; i >= 0; i--) {
            grid.splice(lines[i], 1);
            
            // Add empty line at top
            var emptyLine = [];
            for (var x = 0; x < gridWidth; x++) {
                emptyLine.push(0);
            }
            grid.unshift(emptyLine);
        }
    }
    
    function isGridEmpty() {
        for (var y = 0; y < gridHeight; y++) {
            for (var x = 0; x < gridWidth; x++) {
                if (grid[y][x] !== 0) {
                    return false;
                }
            }
        }
        return true;
    }
    
    function updateGhostPosition() {
        ghostY = currentY;
        while (isValidPosition(currentX, ghostY + 1, currentPiece)) {
            ghostY++;
        }
    }
    
    function activateBigLinuxPower() {
        if (bigLinuxPower < maxBigLinuxPower) return;
        
        bigLinuxPower = 0;
        superModeActive = true;
        superModeTime = 60; // ~3 seconds at ~20 FPS tick rate
        stats.superUses++;
        sessionStats.superUses++;
        // Force QML binding update for sessionStats
        sessionStats = Object.assign({}, sessionStats);
        
        // Clear bottom 3 lines
        for (var i = 0; i < 3; i++) {
            for (var x = 0; x < gridWidth; x++) {
                grid[gridHeight - 1 - i][x] = 0;
            }
        }
        
        // Add explosion effect
        for (var y = gridHeight - 3; y < gridHeight; y++) {
            for (var x = 0; x < gridWidth; x++) {
                createExplosion(gameBoard.x + x * cellSize + cellSize / 2,
                              gameBoard.y + y * cellSize + cellSize / 2);
            }
        }
        
        // Bonus score
        score += 500 * level;
        
        // Update display
        grid = grid.slice();
        
        showFloatingText(gameBoard.x + gameBoard.width / 2,
                       gameBoard.y + gameBoard.height / 2,
                       "BIGLINUX POWER!",
                       "gold");
    }
    
    function endSuperMode() {
        superModeActive = false;
        dropSpeed = Math.max(100, 1000 - (level - 1) * 100);
    }
    
    function showFloatingText(x, y, text, color) {
        floatingTexts.push({
            x: x - text.length * 6,
            y: y,
            text: text,
            color: color,
            time: 60
        });
        
        // Force update
        floatingTexts = floatingTexts.slice();
    }
    
    function createExplosion(x, y) {
        // Create particle explosion effect (reduced count)
        for (var i = 0; i < 3; i++) {
            particles.push({
                x: x,
                y: y,
                vx: (Math.random() - 0.5) * 5,
                vy: (Math.random() - 0.5) * 5,
                color: "#FFD700",
                size: Math.random() * 5 + 2,
                life: 15
            });
        }
    }
    
    function updateAnimations() {
        var particlesChanged = false;
        var textsChanged = false;
        
        // Update particles
        for (var i = particles.length - 1; i >= 0; i--) {
            var p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.life--;
            
            if (p.life <= 0) {
                particles.splice(i, 1);
                particlesChanged = true;
            }
        }
        
        // Update floating texts
        for (var j = floatingTexts.length - 1; j >= 0; j--) {
            floatingTexts[j].time -= 3; // Compensate for lower tick rate
            floatingTexts[j].y -= 2;
            if (floatingTexts[j].time <= 0) {
                floatingTexts.splice(j, 1);
                textsChanged = true;
            }
        }
        
        // Only trigger binding updates when arrays actually changed
        if (particlesChanged) particles = particles.slice();
        if (textsChanged) floatingTexts = floatingTexts.slice();
    }
    
    function endGame() {
        gameRunning = false;
        gameOver = true;
        
        console.log("DEBUG - EndGame - Current score:", score);
        var madeTopFive = updateTopScores(score);
        console.log("DEBUG - Made top 5:", madeTopFive);
        
        gameOverScreen.visible = true;
    }
    
    function resetGame() {
        startScreen.visible = false;
        gameOverScreen.visible = false;
        initGame();
    }
    
    // Input handling
    Keys.onPressed: {
        if (topScoresScreen.visible) {
            if (event.key === Qt.Key_Escape) {
                topScoresScreen.visible = false;
            }
        } else if (startScreen.visible) {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                resetGame();
            } else if (event.key === Qt.Key_T) {
                topScoresScreen.visible = true;
            }
        } else if (gameOverScreen.visible) {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                startScreen.visible = true;
                gameOverScreen.visible = false;
            }
        } else if (gameRunning) {
            if (event.key === Qt.Key_P) {
                gamePaused = !gamePaused;
            } else if (event.key === Qt.Key_T) {
                topScoresScreen.visible = true;
            } else if (!gamePaused) {
                switch (event.key) {
                    case Qt.Key_Left:
                        moveLeft();
                        break;
                    case Qt.Key_Right:
                        moveRight();
                        break;
                    case Qt.Key_Down:
                        if (moveDown()) {
                            score += 1;
                        }
                        break;
                    case Qt.Key_Up:
                    case Qt.Key_Z:
                        rotate();
                        break;
                    case Qt.Key_Space:
                        if (bigLinuxPower >= maxBigLinuxPower) {
                            activateBigLinuxPower();
                        } else {
                            hardDrop();
                        }
                        break;
                    case Qt.Key_C:
                        holdPieceFunction();
                        break;
                }
            }
        }
    }
    
    // Calamares slideshow API 2 calls these when the slideshow becomes
    // visible and when the installer leaves it. Without them the game keeps
    // running, and holding the keyboard, while another page is on screen.
    function onActivate() {
        slideshowActive = true;
        gamePaused = false;
        forceActiveFocus();
    }

    function onLeave() {
        slideshowActive = false;
        gamePaused = true;
    }

    // Load scores on startup
    Component.onCompleted: {
        console.log("Big Blocks v" + gameVersion + " loaded successfully");
        loadTopScores();
        forceActiveFocus();
    }
}