import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Item {
    id: root
    visible: true
    antialiasing: false

    Rectangle {
        id: gameArea
        anchors.fill: parent
        color: "black"

        property int leftScore: 0
        property int rightScore: 0
        property real speedFactor: 1.0
        property bool isPaused: false

        function resetBall() {
            ball.x = gameArea.width / 2 - ball.width / 2;
            ball.y = gameArea.height / 2 - ball.height / 2;
            ball.dx = 8; // Double the initial speed
            ball.dy = 8; // Double the initial speed
            gameArea.speedFactor = 1.0;
        }

        function togglePause() {
            gameArea.isPaused = !gameArea.isPaused;
            ballTimer.running = !gameArea.isPaused;
        }

        Text {
            id: scoreDisplay
            text: "Player: " + gameArea.leftScore + " - Computer: " + gameArea.rightScore
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            color: "white"
            font.pixelSize: 24
        }

        // Button pause
        Rectangle {
            id: pauseButton
            width: 40
            height: 40
            color: "transparent"
            z: 1
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.margins: 10
            border.color: "transparent"

            MouseArea {
                id: pauseMouseArea
                anchors.fill: parent
                onClicked: {
                    gameArea.togglePause();
                }
                onEntered: {
                    leftPauseLine.color = "lightgrey";
                    rightPauseLine.color = "lightgrey";
                }
                onExited: {
                    leftPauseLine.color = "white";
                    rightPauseLine.color = "white";
                }
            }

            Rectangle {
                id: leftPauseLine
                width: 8
                height: 20
                color: "white"
                anchors.centerIn: parent
                anchors.horizontalCenterOffset: -6
            }

            Rectangle {
                id: rightPauseLine
                width: 8
                height: 20
                color: "white"
                anchors.centerIn: parent
                anchors.horizontalCenterOffset: 6
            }
        }

        // Player paddle
        Rectangle {
            id: leftPaddle
            width: 20
            height: 100
            color: "white"
            x: 10
            y: gameArea.height / 2 - height / 2
        }

        // Computer paddle
        Rectangle {
            id: rightPaddle
            width: 20
            height: 100
            color: "white"
            x: gameArea.width - width - 10
            y: gameArea.height / 2 - height / 2
        }

        // Ball
        Rectangle {
            id: ball
            width: 20
            height: 20
            color: "white"
            x: gameArea.width / 2 - width / 2
            y: gameArea.height / 2 - height / 2

            property int dx: 8 // Double the initial speed
            property int dy: 8 // Double the initial speed

            Timer {
                id: ballTimer
                interval: 30 // Adjust as needed
                running: true
                repeat: true
                onTriggered: {
                    if (!gameArea.isPaused) {
                        // Move ball
                        ball.x += ball.dx * gameArea.speedFactor;
                        ball.y += ball.dy * gameArea.speedFactor;

                        // Ball collision with top and bottom
                        if (ball.y <= 0 || ball.y >= gameArea.height - ball.height) {
                            ball.dy *= -1;
                        }

                        // Ball collision with paddles
                        if (ball.x <= leftPaddle.x + leftPaddle.width && ball.y + ball.height >= leftPaddle.y && ball.y <= leftPaddle.y + leftPaddle.height) {
                            ball.dx *= -1;
                            gameArea.speedFactor *= 1.1; // Increase speed by 10%
                        }
                        if (ball.x + ball.width >= rightPaddle.x && ball.y + ball.height >= rightPaddle.y && ball.y <= rightPaddle.y + rightPaddle.height) {
                            ball.dx *= -1;
                            gameArea.speedFactor *= 1.1; // Increase speed by 10%
                        }

                        // Ball out of bounds
                        if (ball.x <= 0) {
                            gameArea.rightScore += 1;
                            gameArea.resetBall();
                        } else if (ball.x >= gameArea.width - ball.width) {
                            gameArea.leftScore += 1;
                            gameArea.resetBall();
                        }

                        // AI for right paddle
                        // Increase the movement speed and improve logic
                        if (ball.y < rightPaddle.y + rightPaddle.height / 2) {
                            rightPaddle.y -= Math.min(12, rightPaddle.y - ball.y + rightPaddle.height / 2); // Faster and smarter reaction
                        } else if (ball.y > rightPaddle.y + rightPaddle.height / 2) {
                            rightPaddle.y += Math.min(12, ball.y - rightPaddle.y - rightPaddle.height / 2); // Faster and smarter reaction
                        }
                    }
                }
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            onPositionChanged: {
                if (!gameArea.isPaused) {
                    leftPaddle.y = Math.max(0, Math.min(mouse.y - leftPaddle.height / 2, gameArea.height - leftPaddle.height));
                }
            }
        }
    }
}
