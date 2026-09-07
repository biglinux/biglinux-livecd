import QtQuick 2.15
import QtQuick.Controls 2.15
import "i18n.js" as I18n

Item {
    id: root

    property bool slideshowActive: false

    readonly property string localeKey:
        Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")

    function tr(source) { return I18n.translate(source, localeKey) }

    focus: slideshowActive

    Accessible.role: Accessible.Pane
    Accessible.name: root.tr("Pong game")
    Accessible.description:
        root.tr("Move the left paddle with the mouse or the up and down arrow keys. Press Space to pause or resume.")

    Component.onCompleted: gameArea.pause()

    function onActivate() {
        slideshowActive = true
        gameArea.resetGame()
        gameArea.resume()
    }

    function onLeave() {
        slideshowActive = false
        gameArea.pause()
    }

    onActiveFocusChanged: {
        if (!activeFocus) {
            gameArea.clearKeyboardInput()
        }
    }

    Keys.onPressed: function(event) {
        if (!slideshowActive) {
            return
        }

        const isUp = event.key === Qt.Key_Up || event.key === Qt.Key_W
        const isDown = event.key === Qt.Key_Down || event.key === Qt.Key_S

        if (isUp || isDown) {
            event.accepted = true
            if (!event.isAutoRepeat) {
                gameArea.setKeyboardDirection(isUp, isDown, true)
            }
            return
        }

        if (event.key === Qt.Key_Space) {
            event.accepted = true
            if (!event.isAutoRepeat) {
                gameArea.togglePause()
            }
        }
    }

    Keys.onReleased: function(event) {
        const isUp = event.key === Qt.Key_Up || event.key === Qt.Key_W
        const isDown = event.key === Qt.Key_Down || event.key === Qt.Key_S

        if (isUp || isDown) {
            event.accepted = true
            if (!event.isAutoRepeat) {
                gameArea.setKeyboardDirection(isUp, isDown, false)
            }
        }
    }

    Rectangle {
        id: gameArea

        anchors.fill: parent
        // The panel next to it starts 11 pixels down, and the two should line
        // up. The strip left above shows the window background, exactly as it
        // does above the sidebar, so no band of another colour appears.
        anchors.topMargin: 11
        radius: 12
        clip: true

        gradient: Gradient {
            GradientStop { position: 0.0; color: "#10243D" }
            GradientStop { position: 1.0; color: "#071321" }
        }

        property int leftScore: 0
        property int rightScore: 0
        property bool isPaused: false
        property bool upPressed: false
        property bool downPressed: false
        property real keyboardSpeed: Math.max(360, height * 0.90)
        property real baseBallSpeed: Math.max(6.0, width / 150)
        property real maxBallSpeed: Math.max(13.0, width / 62)
        property real aiSpeed: Math.max(5.2, height / 85)
        property double lastTick: 0

        function clamp(value, minimum, maximum) {
            return Math.max(minimum, Math.min(value, maximum))
        }

        function clearKeyboardInput() {
            upPressed = false
            downPressed = false
            paddleAnimation.stop()
        }

        function setKeyboardDirection(isUp, isDown, pressed) {
            if (isUp) {
                upPressed = pressed
            }
            if (isDown) {
                downPressed = pressed
            }
            updatePaddleAnimation()
        }

        function updatePaddleAnimation() {
            paddleAnimation.stop()

            if (!root.slideshowActive || isPaused) {
                return
            }

            const direction = (downPressed ? 1 : 0) - (upPressed ? 1 : 0)
            if (direction === 0) {
                return
            }

            const targetY = direction < 0 ? 0 : height - leftPaddle.height
            const distance = Math.abs(targetY - leftPaddle.y)
            if (distance < 0.5) {
                leftPaddle.y = targetY
                return
            }

            paddleAnimation.from = leftPaddle.y
            paddleAnimation.to = targetY
            paddleAnimation.duration = Math.max(
                1,
                Math.round(distance / keyboardSpeed * 1000)
            )
            paddleAnimation.start()
        }

        function resetBall() {
            ball.x = width / 2 - ball.width / 2
            ball.y = height / 2 - ball.height / 2

            const direction = Math.random() < 0.5 ? -1 : 1
            const angle = (Math.random() - 0.5) * 0.90
            ball.dx = direction * baseBallSpeed * Math.cos(angle)
            ball.dy = baseBallSpeed * Math.sin(angle)

            trailOne.x = ball.x
            trailOne.y = ball.y
            trailTwo.x = ball.x
            trailTwo.y = ball.y
            lastTick = Date.now()
        }

        function resetGame() {
            leftScore = 0
            rightScore = 0
            leftPaddle.y = height / 2 - leftPaddle.height / 2
            rightPaddle.y = height / 2 - rightPaddle.height / 2
            resetBall()
        }

        function bounceFromPaddle(paddle, direction) {
            const ballCenter = ball.y + ball.height / 2
            const paddleCenter = paddle.y + paddle.height / 2
            const relativeHit = clamp(
                (ballCenter - paddleCenter) / (paddle.height / 2),
                -0.92,
                0.92
            )
            const currentSpeed = Math.sqrt(ball.dx * ball.dx + ball.dy * ball.dy)
            const speed = Math.min(maxBallSpeed, currentSpeed * 1.09)
            const angle = relativeHit * 0.92

            ball.dx = direction * speed * Math.cos(angle)
            ball.dy = speed * Math.sin(angle)
        }

        function updateComputerPaddle(frameScale) {
            let targetY

            // Follow the ball only when it is approaching. Otherwise drift
            // toward the center, which keeps the opponent fair and natural.
            if (ball.dx > 0) {
                targetY = ball.y + ball.height / 2 - rightPaddle.height / 2
            } else {
                targetY = height / 2 - rightPaddle.height / 2
            }

            const difference = targetY - rightPaddle.y
            const movement = clamp(
                difference,
                -aiSpeed * frameScale,
                aiSpeed * frameScale
            )
            rightPaddle.y = clamp(
                rightPaddle.y + movement,
                0,
                height - rightPaddle.height
            )
        }

        function tick() {
            const now = Date.now()
            const elapsed = lastTick > 0 ? now - lastTick : 16
            lastTick = now

            // Compensate for small scheduling variations without allowing one
            // delayed frame to make the ball skip across a paddle.
            const frameScale = clamp(elapsed / 16.6667, 0.55, 1.45)

            trailTwo.x = trailOne.x
            trailTwo.y = trailOne.y
            trailOne.x = ball.x
            trailOne.y = ball.y

            ball.x += ball.dx * frameScale
            ball.y += ball.dy * frameScale

            if (ball.y <= 0) {
                ball.y = 0
                ball.dy = Math.abs(ball.dy)
            } else if (ball.y >= height - ball.height) {
                ball.y = height - ball.height
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
                bounceFromPaddle(leftPaddle, 1)
            }

            const hitsRightPaddle =
                ball.dx > 0
                && ball.x + ball.width >= rightPaddle.x
                && ball.x <= rightPaddle.x + rightPaddle.width
                && ball.y + ball.height >= rightPaddle.y
                && ball.y <= rightPaddle.y + rightPaddle.height

            if (hitsRightPaddle) {
                ball.x = rightPaddle.x - ball.width
                bounceFromPaddle(rightPaddle, -1)
            }

            if (ball.x + ball.width < 0) {
                rightScore += 1
                resetBall()
            } else if (ball.x > width) {
                leftScore += 1
                resetBall()
            }

            updateComputerPaddle(frameScale)
        }

        function pause() {
            isPaused = true
            clearKeyboardInput()
        }

        function resume() {
            root.slideshowActive = true
            isPaused = false
            lastTick = Date.now()
            root.forceActiveFocus()
            updatePaddleAnimation()
        }

        function togglePause() {
            if (isPaused) {
                resume()
            } else {
                pause()
            }
        }

        onHeightChanged: {
            paddleAnimation.stop()
            leftPaddle.y = clamp(leftPaddle.y, 0, height - leftPaddle.height)
            rightPaddle.y = clamp(rightPaddle.y, 0, height - rightPaddle.height)
            updatePaddleAnimation()
        }

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(0.30, 0.66, 0.91, 0.20)
        }

        Repeater {
            model: 12

            Rectangle {
                width: 3
                height: 3
                radius: 1.5
                x: gameArea.width * 0.08 + (index % 6) * 25
                y: gameArea.height * 0.16 + Math.floor(index / 6) * 25
                color: Qt.rgba(0.30, 0.66, 0.91, 0.18)
            }
        }

Text {
            anchors.top: parent.top
            anchors.topMargin: 14
            anchors.horizontalCenter: parent.horizontalCenter
            z: 4

            text: "%1 — %2"
                .arg(gameArea.leftScore)
                .arg(gameArea.rightScore)
            color: "#F5FAFF"
            font.pixelSize: 21
            font.bold: true
        }

Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 10

            Repeater {
                model: Math.max(1, Math.floor(gameArea.height / 24))

                Rectangle {
                    width: 3
                    height: 12
                    radius: 1
                    color: Qt.rgba(1, 1, 1, 0.16)
                }
            }
        }

        Rectangle {
            id: leftPaddle

            width: Math.max(14, gameArea.width * 0.018)
            height: Math.max(76, gameArea.height * 0.19)
            x: 18
            y: gameArea.height / 2 - height / 2
            radius: width / 2
            color: "#55B5F1"
            border.width: 1
            border.color: "#A6DEFF"
            z: 2
        }

        NumberAnimation {
            id: paddleAnimation

            target: leftPaddle
            property: "y"
            easing.type: Easing.Linear

            onStopped: {
                leftPaddle.y = gameArea.clamp(
                    leftPaddle.y,
                    0,
                    gameArea.height - leftPaddle.height
                )
            }
        }

        Rectangle {
            id: rightPaddle

            width: leftPaddle.width
            height: leftPaddle.height
            x: gameArea.width - width - 18
            y: gameArea.height / 2 - height / 2
            radius: width / 2
            color: "#F4F9FD"
            border.width: 1
            border.color: "#FFFFFF"
            z: 2
        }

        Rectangle {
            id: trailTwo

            width: ball.width * 0.72
            height: width
            radius: width / 2
            color: Qt.rgba(0.18, 0.55, 0.85, 0.12)
            z: 1
        }

        Rectangle {
            id: trailOne

            width: ball.width * 0.84
            height: width
            radius: width / 2
            color: Qt.rgba(0.35, 0.75, 0.98, 0.20)
            z: 1
        }

        Rectangle {
            id: ball

            property real dx: 4.0
            property real dy: 0.0

            width: Math.max(14, gameArea.width * 0.018)
            height: width
            x: gameArea.width / 2 - width / 2
            y: gameArea.height / 2 - height / 2
            radius: width / 2
            color: "#2E8DDA"
            border.width: 2
            border.color: "#A6DEFF"
            z: 2
        }

        Timer {
            id: movementTimer

            interval: 16
            repeat: true
            running: root.visible && root.slideshowActive && !gameArea.isPaused

            onRunningChanged: {
                if (running) {
                    gameArea.lastTick = Date.now()
                }
            }

            onTriggered: gameArea.tick()
        }

        MouseArea {
            anchors.fill: parent
            z: 1
            hoverEnabled: true

            onPressed: root.forceActiveFocus()

            onPositionChanged: function(mouse) {
                if (!root.slideshowActive || gameArea.isPaused) {
                    return
                }

                paddleAnimation.stop()
                leftPaddle.y = gameArea.clamp(
                    mouse.y - leftPaddle.height / 2,
                    0,
                    gameArea.height - leftPaddle.height
                )

                if (gameArea.upPressed || gameArea.downPressed) {
                    gameArea.updatePaddleAnimation()
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: 14
            anchors.bottomMargin: 12
            width: instructionText.implicitWidth + 18
            height: 28
            radius: 6
            color: Qt.rgba(0.10, 0.23, 0.38, 0.88)
            border.width: 1
            border.color: Qt.rgba(0.33, 0.71, 0.95, 0.25)
            z: 4

            Text {
                id: instructionText

                anchors.centerIn: parent
                text: root.tr("Mouse or ↑ ↓ / W S to move • Space to pause")
                color: Qt.rgba(0.94, 0.98, 1, 0.78)
                font.pixelSize: 10
            }
        }

        Rectangle {
            anchors.fill: parent
            visible: gameArea.isPaused
            color: Qt.rgba(0.02, 0.07, 0.12, 0.76)
            z: 3

            MouseArea {
                anchors.fill: parent
                onClicked: gameArea.resume()
            }

            Column {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.tr("Paused")
                    color: "#FFFFFF"
                    font.pixelSize: 30
                    font.bold: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.tr("Press Space or use the button below to continue")
                    color: Qt.rgba(0.92, 0.97, 1, 0.72)
                    font.pixelSize: 12
                }
            }
        }

        Button {
            id: pauseButton

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 12
            implicitWidth: 108
            implicitHeight: 38
            z: 5

            text: gameArea.isPaused ? root.tr("Resume") : root.tr("Pause")
            focusPolicy: Qt.NoFocus
            onClicked: gameArea.togglePause()

            contentItem: Text {
                text: pauseButton.text
                color: "#FFFFFF"
                font.pixelSize: 14
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: 8
                color: pauseButton.down
                    ? "#1268A8"
                    : pauseButton.hovered ? "#2289D3" : "#1976C9"
                border.width: 1
                border.color: "#8FD4FF"
            }

            Accessible.name: text
            Accessible.description:
                root.tr("Pause or resume the Pong game")
        }
    }
}
