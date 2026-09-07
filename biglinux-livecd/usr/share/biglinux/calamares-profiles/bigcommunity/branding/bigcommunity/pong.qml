import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property bool slideshowActive: false

    focus: slideshowActive

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Pong game")
    Accessible.description:
        qsTr("Move the left paddle with the mouse or the up and down arrow keys. Press Space to pause or resume.")

    function onActivate() {
        slideshowActive = true
        gameArea.isPaused = false
        gameArea.resetBall()
        forceActiveFocus()
    }

    function onLeave() {
        slideshowActive = false
        gameArea.isPaused = true
    }

    Keys.onPressed: function(event) {
        if (!slideshowActive) {
            return
        }

        if (event.key === Qt.Key_Up || event.key === Qt.Key_W) {
            gameArea.movePlayerPaddle(-gameArea.keyboardStep)
            event.accepted = true
        } else if (event.key === Qt.Key_Down || event.key === Qt.Key_S) {
            gameArea.movePlayerPaddle(gameArea.keyboardStep)
            event.accepted = true
        } else if (event.key === Qt.Key_Space) {
            gameArea.togglePause()
            event.accepted = true
        }
    }

    Rectangle {
        id: gameArea

        anchors.fill: parent
        color: "#090B10"
        clip: true

        property int leftScore: 0
        property int rightScore: 0
        property real speedFactor: 1.0
        property bool isPaused: false
        property real keyboardStep: 28
        property real aiStep: 10

        function clamp(value, minimum, maximum) {
            return Math.max(minimum, Math.min(value, maximum))
        }

        function movePlayerPaddle(delta) {
            leftPaddle.y = clamp(
                leftPaddle.y + delta,
                0,
                height - leftPaddle.height
            )
        }

        function resetBall() {
            ball.x = width / 2 - ball.width / 2
            ball.y = height / 2 - ball.height / 2
            ball.dx = Math.random() < 0.5 ? -7 : 7
            ball.dy = Math.random() < 0.5 ? -6 : 6
            speedFactor = 1.0
        }

        function togglePause() {
            if (!root.slideshowActive) {
                return
            }
            isPaused = !isPaused
        }

        onHeightChanged: {
            leftPaddle.y = clamp(leftPaddle.y, 0, height - leftPaddle.height)
            rightPaddle.y = clamp(rightPaddle.y, 0, height - rightPaddle.height)
        }

        Text {
            id: scoreDisplay

            anchors.top: parent.top
            anchors.topMargin: 16
            anchors.horizontalCenter: parent.horizontalCenter
            z: 4

            text: "%1 — %2"
                .arg(gameArea.leftScore)
                .arg(gameArea.rightScore)
            color: "white"
            font.pixelSize: 22
            font.bold: true
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 3
            color: Qt.rgba(1, 1, 1, 0.22)
        }

        Rectangle {
            id: leftPaddle

            width: Math.max(14, gameArea.width * 0.018)
            height: Math.max(76, gameArea.height * 0.19)
            x: 16
            y: gameArea.height / 2 - height / 2
            radius: width / 3
            color: "white"
            z: 2
        }

        Rectangle {
            id: rightPaddle

            width: leftPaddle.width
            height: leftPaddle.height
            x: gameArea.width - width - 16
            y: gameArea.height / 2 - height / 2
            radius: width / 3
            color: "white"
            z: 2
        }

        Rectangle {
            id: ball

            property real dx: 7
            property real dy: 6

            width: Math.max(14, gameArea.width * 0.018)
            height: width
            x: gameArea.width / 2 - width / 2
            y: gameArea.height / 2 - height / 2
            radius: width / 2
            color: "white"
            z: 2

            Timer {
                id: movementTimer

                interval: 33
                repeat: true
                running: root.slideshowActive && !gameArea.isPaused

                onTriggered: {
                    ball.x += ball.dx * gameArea.speedFactor
                    ball.y += ball.dy * gameArea.speedFactor

                    if (ball.y <= 0) {
                        ball.y = 0
                        ball.dy = Math.abs(ball.dy)
                    } else if (ball.y >= gameArea.height - ball.height) {
                        ball.y = gameArea.height - ball.height
                        ball.dy = -Math.abs(ball.dy)
                    }

                    const hitsLeftPaddle =
                        ball.dx < 0
                        && ball.x <= leftPaddle.x + leftPaddle.width
                        && ball.x + ball.width >= leftPaddle.x
                        && ball.y + ball.height >= leftPaddle.y
                        && ball.y <= leftPaddle.y + leftPaddle.height

                    if (hitsLeftPaddle) {
                        ball.x = leftPaddle.x + leftPaddle.width
                        ball.dx = Math.abs(ball.dx)
                        gameArea.speedFactor = Math.min(
                            2.2,
                            gameArea.speedFactor * 1.06
                        )
                    }

                    const hitsRightPaddle =
                        ball.dx > 0
                        && ball.x + ball.width >= rightPaddle.x
                        && ball.x <= rightPaddle.x + rightPaddle.width
                        && ball.y + ball.height >= rightPaddle.y
                        && ball.y <= rightPaddle.y + rightPaddle.height

                    if (hitsRightPaddle) {
                        ball.x = rightPaddle.x - ball.width
                        ball.dx = -Math.abs(ball.dx)
                        gameArea.speedFactor = Math.min(
                            2.2,
                            gameArea.speedFactor * 1.06
                        )
                    }

                    if (ball.x + ball.width < 0) {
                        gameArea.rightScore += 1
                        gameArea.resetBall()
                    } else if (ball.x > gameArea.width) {
                        gameArea.leftScore += 1
                        gameArea.resetBall()
                    }

                    const targetY = ball.y + ball.height / 2
                        - rightPaddle.height / 2
                    const difference = targetY - rightPaddle.y
                    const movement = gameArea.clamp(
                        difference,
                        -gameArea.aiStep,
                        gameArea.aiStep
                    )
                    rightPaddle.y = gameArea.clamp(
                        rightPaddle.y + movement,
                        0,
                        gameArea.height - rightPaddle.height
                    )
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            z: 1
            hoverEnabled: true

            onPositionChanged: function(mouse) {
                if (!root.slideshowActive || gameArea.isPaused) {
                    return
                }
                leftPaddle.y = gameArea.clamp(
                    mouse.y - leftPaddle.height / 2,
                    0,
                    gameArea.height - leftPaddle.height
                )
            }
        }

        Rectangle {
            anchors.fill: parent
            visible: gameArea.isPaused
            color: Qt.rgba(0, 0, 0, 0.58)
            z: 3

            Text {
                anchors.centerIn: parent
                text: qsTr("Paused")
                color: "white"
                font.pixelSize: 30
                font.bold: true
            }
        }

        Button {
            id: pauseButton

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 12
            z: 5

            text: gameArea.isPaused ? qsTr("Resume") : qsTr("Pause")
            onClicked: gameArea.togglePause()

            Accessible.name: text
            Accessible.description:
                qsTr("Pause or resume the Pong game")
        }
    }
}
