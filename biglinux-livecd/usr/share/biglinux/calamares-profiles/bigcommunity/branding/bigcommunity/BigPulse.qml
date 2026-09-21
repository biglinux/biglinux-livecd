pragma ComponentBehavior: Bound
pragma FunctionSignatureBehavior: Enforced

import QtQuick
import QtQuick.Shapes
import QtCore

// BigPulse — optimized single-file QML port of the Pulse game.
// Keeps the original visual style, aligns the hit boundary to the visible
// target, and avoids per-frame heap churn, hidden work and linear scans.
// Shape.CurveRenderer makes Qt 6.6 or newer the effective minimum version.

Rectangle {
    id: root

    implicitWidth: 700
    implicitHeight: 700
    width: Math.max(root.implicitWidth,
                    root.parent ? root.parent.width : root.implicitWidth)
    height: Math.max(root.implicitHeight,
                     root.parent ? root.parent.height : root.implicitHeight)
    focus: true

    gradient: Gradient {
        GradientStop { position: 0.0; color: root.colBg1 }
        GradientStop { position: 0.55; color: root.colBg2 }
        GradientStop { position: 1.0; color: root.colBg1 }
    }

    // ---- Gameplay constants and shared visual geometry ----
    readonly property int shapeCount: 5
    readonly property int shapeChangeEvery: 8
    readonly property int hitsPerPhase: 40
    readonly property real startLaps: 0.5
    readonly property real maxLaps: 1.0 / 0.6
    readonly property real lapsGrowth: 1.015
    readonly property real phaseSpeedStep: 1.15
    readonly property real phaseZoneStepDeg: 3.0
    readonly property real zoneStartDeg: 32.0
    readonly property real zoneMinDeg: 13.0
    readonly property real zoneShrinkPerHit: 0.18
    readonly property real perfectFraction: 0.28
    readonly property int specialAfter: 8
    readonly property real ghostVisibleSec: 0.6
    readonly property real zoneGlowStrokeWidth: 34
    readonly property real zoneCoreStrokeWidth: 16
    readonly property real pointerBarThickness: 8
    readonly property real pointerDotSize: 14
    readonly property int partPool: 48
    readonly property int feedbackCapacity: 4

    readonly property color colBg1: "#070a18"
    readonly property color colBg2: "#131a33"
    readonly property color colRing: "#e6edf3"
    readonly property color colAccent: "#00e5ff"
    readonly property color colGold: "#ffc857"
    readonly property color colDouble: "#4ade80"
    readonly property color colGhost: "#b57bff"
    readonly property color colShield: "#7dd3fc"
    readonly property color colMiss: "#ff5570"
    readonly property color colDim: "#8a93a6"

    // ---- State ----
    property int score: 0
    property int phase: 1
    property int best: 0
    property int bestPhase: 1
    property real laps: startLaps
    property real direction: 1
    property real pointerS: 0
    property real zoneHalfS: 0
    property bool shield: false
    property int perfectStreak: 0
    property int shapeIdx: 0
    property bool playing: false
    property bool gameOver: false
    property real readyT: 0
    property real overSinceMs: 0
    property real flash: 0
    property real shake: 0
    property bool initialized: false

    // A maximum of two targets is required by the rules. Scalars avoid the
    // short-lived JS arrays and object literals previously created each hit.
    property int targetCount: 0
    property int targetIndex: 0
    property int targetType: 0
    property real target0Center: 0
    property real target1Center: 0
    property real ghostRemaining: 0

    readonly property real currentTargetCenter: targetIndex === 0
                                                        ? target0Center
                                                        : target1Center
    // pointerS denotes the marker center. RoundCap extends the bright target
    // by half its stroke width, so this boundary matches the visible core and
    // never grows with speed. The translucent outer glow is decorative only.
    readonly property real hitHalfS: root.zoneHalfS
                                     + root.zoneCoreStrokeWidth * 0.5
    readonly property bool zoneAVisible: !gameOver
                                             && zoneAPoints.length > 0
                                             && (targetType !== 3 || ghostRemaining > 0)
    readonly property bool zoneBVisible: !gameOver && zoneBPoints.length > 0
    readonly property bool needsFrames: initialized && (!gameOver
                                            || activeParticleCount > 0
                                            || feedbackCount > 0
                                            || flash > 0
                                            || shake > 0)

    Settings {
        category: "BigPulse"
        property alias savedBest: root.best
        property alias savedBestPhase: root.bestPhase
    }

    // ---- Regular-polygon path ----
    // All sides of a regular polygon have equal length. Segment lookup is O(1)
    // instead of scanning up to 96 cumulative lengths on every rendered frame.
    property int sideCount: 0
    property real segmentLength: 1
    property real inverseSegmentLength: 1
    property real perimeter: 1
    property var vertexX: []
    property var vertexY: []
    property var segmentAngles: []
    property var outlinePoints: []
    property var echo1Points: []
    property var echo2Points: []
    property var zoneAPoints: []
    property var zoneBPoints: []
    property string starPath: ""

    property color zoneAColor: colAccent
    readonly property color zoneBColor: colDouble
    property real zoneAAlpha: 1

    readonly property real centerX: root.width * 0.5
    readonly property real centerY: root.height * 0.5 + 10
    readonly property real gameRadius: Math.min(root.width, root.height) * 0.30

    function positiveModulo(value: real, modulus: real): real {
        return ((value % modulus) + modulus) % modulus;
    }

    function sidesForShape(index: int): int {
        switch (index) {
        case 0: return 96;
        case 1: return 6;
        case 2: return 5;
        case 3: return 4;
        default: return 3;
        }
    }

    function colorForTarget(type: int): color {
        switch (type) {
        case 1: return root.colGold;
        case 2: return root.colDouble;
        case 3: return root.colGhost;
        case 4: return root.colShield;
        default: return root.colAccent;
        }
    }

    function buildShape(index: int): void {
        const sides = root.sidesForShape(index);
        const xs = [];
        const ys = [];
        const angles = [];
        const outline = [];
        const echo1 = [];
        const echo2 = [];
        const centerX = root.centerX;
        const centerY = root.centerY;
        const radius = root.gameRadius;

        for (let i = 0; i < sides; ++i) {
            const angle = -Math.PI * 0.5 + i / sides * Math.PI * 2;
            xs.push(centerX + Math.cos(angle) * radius);
            ys.push(centerY + Math.sin(angle) * radius);
        }

        const dx = xs[1] - xs[0];
        const dy = ys[1] - ys[0];
        const length = Math.hypot(dx, dy);

        for (let i = 0; i < sides; ++i) {
            const next = (i + 1) % sides;
            angles.push(Math.atan2(ys[next] - ys[i], xs[next] - xs[i])
                        * 180 / Math.PI + 90);
            outline.push(Qt.point(xs[i], ys[i]));
            echo1.push(Qt.point(centerX + (xs[i] - centerX) * 1.18,
                                centerY + (ys[i] - centerY) * 1.18));
            echo2.push(Qt.point(centerX + (xs[i] - centerX) * 1.38,
                                centerY + (ys[i] - centerY) * 1.38));
        }
        outline.push(outline[0]);
        echo1.push(echo1[0]);
        echo2.push(echo2[0]);

        root.vertexX = xs;
        root.vertexY = ys;
        root.segmentAngles = angles;
        root.outlinePoints = outline;
        root.echo1Points = echo1;
        root.echo2Points = echo2;
        root.sideCount = sides;
        root.segmentLength = length;
        root.inverseSegmentLength = 1 / length;
        root.perimeter = sides * length;
        root.shapeIdx = index;
    }

    function pointAt(position: real): point {
        const perimeterValue = root.perimeter;
        const inverseLength = root.inverseSegmentLength;
        const length = root.segmentLength;
        const sides = root.sideCount;
        const xs = root.vertexX;
        const ys = root.vertexY;
        const wrapped = root.positiveModulo(position, perimeterValue);
        let segment = Math.floor(wrapped * inverseLength);
        if (segment >= sides)
            segment = sides - 1;
        segment = Math.max(segment, 0);
        const next = (segment + 1) % sides;
        const local = (wrapped - segment * length) * inverseLength;
        return Qt.point(xs[segment] + (xs[next] - xs[segment]) * local,
                        ys[segment] + (ys[next] - ys[segment]) * local);
    }

    function distanceOnPath(a: real, b: real): real {
        const perimeterValue = root.perimeter;
        const distance = root.positiveModulo(a - b, perimeterValue);
        return Math.min(distance, perimeterValue - distance);
    }

    // Use true polygon vertices in the tube path. This needs fewer points than
    // 21 uniform samples and does not cut polygon corners.
    function buildZoneSegment(center: real): var {
        if (!(root.segmentLength > 0) || root.sideCount < 3)
            return [];

        const length = root.segmentLength;
        const start = center - root.zoneHalfS;
        const end = center + root.zoneHalfS;
        const points = [root.pointAt(start)];
        const epsilon = length * 0.0000001;
        let boundary = (Math.floor(start / length) + 1) * length;

        while (boundary < end - epsilon) {
            points.push(root.pointAt(boundary));
            boundary += length;
        }

        const endpoint = root.pointAt(end);
        const last = points[points.length - 1];
        if (Math.abs(endpoint.x - last.x) > 0.0001
                || Math.abs(endpoint.y - last.y) > 0.0001)
            points.push(endpoint);
        return points;
    }

    function updateZoneGeometry(): void {
        if (root.sideCount < 3 || root.targetCount < 1) {
            root.zoneAPoints = [];
            root.zoneBPoints = [];
            return;
        }

        root.zoneAPoints = root.buildZoneSegment(root.target0Center);
        root.zoneBPoints = root.targetCount > 1
                ? root.buildZoneSegment(root.target1Center) : [];
        root.zoneAColor = root.colorForTarget(root.targetType);
        root.zoneAAlpha = root.targetIndex > 0 ? 0.25 : 1;
    }

    function updateZoneSize(): void {
        const hitsInPhase = root.score % root.hitsPerPhase;
        const start = root.zoneStartDeg
                      - root.phaseZoneStepDeg * (root.phase - 1);
        const fraction = Math.max(root.zoneMinDeg,
                                  start - hitsInPhase * root.zoneShrinkPerHit) / 360;
        root.zoneHalfS = root.perimeter * fraction * 0.5;
    }

    function rebuildStars(): void {
        const commands = [];
        const widthValue = root.width;
        const heightValue = root.height;
        for (let i = 0; i < 60; ++i) {
            const size = i % 3 === 0 ? 2 : 1;
            const x = root.positiveModulo(Math.sin(i * 127.1) * 43758.5, 1)
                      * widthValue;
            const y = root.positiveModulo(Math.sin(i * 311.7) * 12543.8, 1)
                      * heightValue;
            commands.push("M " + x + " " + y
                          + " h " + size + " v " + size
                          + " h -" + size + " Z");
        }
        root.starPath = commands.join(" ");
    }

    function rebuildForSize(): void {
        const oldPerimeter = root.perimeter;
        const pointerRatio = oldPerimeter > 0 ? root.pointerS / oldPerimeter : 0;
        const target0Ratio = oldPerimeter > 0 ? root.target0Center / oldPerimeter : 0;
        const target1Ratio = oldPerimeter > 0 ? root.target1Center / oldPerimeter : 0;

        root.buildShape(root.shapeIdx);
        root.pointerS = pointerRatio * root.perimeter;
        root.target0Center = target0Ratio * root.perimeter;
        root.target1Center = target1Ratio * root.perimeter;
        root.updateZoneSize();
        root.updateZoneGeometry();
        root.rebuildStars();
        root.updatePointerVisual();
    }

    Timer {
        id: geometryUpdateTimer
        interval: 0
        repeat: false
        onTriggered: root.rebuildForSize()
    }

    onWidthChanged: {
        if (root.initialized)
            geometryUpdateTimer.restart();
    }
    onHeightChanged: {
        if (root.initialized)
            geometryUpdateTimer.restart();
    }
    onVisibleChanged: {
        if (root.visible)
            root.updatePointerVisual();
    }

    // ---- Targets and rules ----
    function spawnTargets(): void {
        root.targetIndex = 0;
        let kind = 0;
        if (root.score >= root.specialAfter) {
            const random = Math.random();
            if (random < 0.12)
                kind = 1;
            else if (random < 0.20 && root.score >= 14)
                kind = 2;
            else if (random < 0.28 && root.score >= 22)
                kind = 3;
            else if (random < 0.34 && !root.shield && root.score >= 10)
                kind = 4;
        }

        const perimeterValue = root.perimeter;
        const directionValue = root.direction;
        root.targetType = kind;
        root.target0Center = root.positiveModulo(
                    root.pointerS + directionValue
                    * (0.35 + Math.random() * 0.30) * perimeterValue,
                    perimeterValue);
        root.targetCount = kind === 2 ? 2 : 1;
        if (root.targetCount === 2) {
            root.target1Center = root.positiveModulo(
                        root.target0Center + directionValue
                        * (0.20 + Math.random() * 0.15) * perimeterValue,
                        perimeterValue);
        }
        root.ghostRemaining = kind === 3 ? root.ghostVisibleSec : 0;
        root.updateZoneGeometry();
    }

    // ---- Fixed particle pool; only active particles are visited per frame ----
    // Long-lived flat arrays avoid per-emission object literals. The active
    // index buffer is preallocated and compacted in place, and delegate
    // references are cached so animation frames do not call Repeater.itemAt().
    property var activeParticleIndices: []
    property var particleItems: []
    property var particleVelocityX: []
    property var particleVelocityY: []
    property var particleLife: []
    property var particleTotalLife: []
    property int activeParticleCount: 0
    property int partNext: 0

    function initializeParticleState(): void {
        const active = new Array(root.partPool);
        const items = new Array(root.partPool);
        const velocityX = new Array(root.partPool);
        const velocityY = new Array(root.partPool);
        const life = new Array(root.partPool);
        const totalLife = new Array(root.partPool);
        for (let i = 0; i < root.partPool; ++i) {
            active[i] = 0;
            items[i] = particleRepeater.itemAt(i);
            velocityX[i] = 0;
            velocityY[i] = 0;
            life[i] = 0;
            totalLife[i] = 1;
        }
        root.activeParticleIndices = active;
        root.particleItems = items;
        root.particleVelocityX = velocityX;
        root.particleVelocityY = velocityY;
        root.particleLife = life;
        root.particleTotalLife = totalLife;
    }

    function emitParticles(x: real, y: real, particleColor: color,
                           count: int, minimumSpeed: real, maximumSpeed: real,
                           lifetime: real): void {
        const active = root.activeParticleIndices;
        const items = root.particleItems;
        const velocityX = root.particleVelocityX;
        const velocityY = root.particleVelocityY;
        const life = root.particleLife;
        const totalLife = root.particleTotalLife;
        let activeCount = root.activeParticleCount;

        for (let k = 0; k < count; ++k) {
            const index = root.partNext;
            root.partNext = (root.partNext + 1) % root.partPool;
            let particle = items[index];
            if (!particle) {
                particle = particleRepeater.itemAt(index);
                items[index] = particle;
            }
            if (!particle)
                continue;

            const angle = Math.random() * Math.PI * 2;
            const speed = minimumSpeed + Math.random()
                          * (maximumSpeed - minimumSpeed);
            if (life[index] <= 0)
                active[activeCount++] = index;
            velocityX[index] = Math.cos(angle) * speed;
            velocityY[index] = Math.sin(angle) * speed;
            life[index] = lifetime;
            totalLife[index] = lifetime;
            const halfSize = (3 + index % 4) * 0.5;
            particle.x = x - halfSize;
            particle.y = y - halfSize;
            particle.color = particleColor;
            particle.opacity = 1;
            particle.visible = true;
        }
        if (activeCount !== root.activeParticleCount)
            root.activeParticleCount = activeCount;
    }

    function burstAtPointer(particleColor: color, count: int,
                            minimumSpeed: real, maximumSpeed: real,
                            lifetime: real): void {
        const position = root.pointAt(root.pointerS);
        root.emitParticles(position.x, position.y, particleColor, count,
                           minimumSpeed, maximumSpeed, lifetime);
    }

    function updateParticles(delta: real): void {
        let writeIndex = 0;
        const active = root.activeParticleIndices;
        const items = root.particleItems;
        const velocityX = root.particleVelocityX;
        const velocityY = root.particleVelocityY;
        const life = root.particleLife;
        const totalLife = root.particleTotalLife;
        const activeCount = root.activeParticleCount;

        for (let i = 0; i < activeCount; ++i) {
            const index = active[i];
            let particle = items[index];
            if (!particle) {
                particle = particleRepeater.itemAt(index);
                items[index] = particle;
            }
            life[index] -= delta;
            if (life[index] <= 0 || !particle) {
                life[index] = 0;
                if (particle) {
                    particle.opacity = 0;
                    particle.visible = false;
                }
                continue;
            }

            particle.x += velocityX[index] * delta;
            particle.y += velocityY[index] * delta;
            particle.opacity = life[index] / totalLife[index];
            active[writeIndex++] = index;
        }
        if (writeIndex !== activeCount)
            root.activeParticleCount = writeIndex;
    }

    function clearParticles(): void {
        const active = root.activeParticleIndices;
        const items = root.particleItems;
        const activeCount = root.activeParticleCount;
        for (let i = 0; i < activeCount; ++i) {
            const index = active[i];
            let particle = items[index];
            if (!particle) {
                particle = particleRepeater.itemAt(index);
                items[index] = particle;
            }
            root.particleLife[index] = 0;
            if (particle) {
                particle.opacity = 0;
                particle.visible = false;
            }
        }
        if (activeCount > 0)
            root.activeParticleCount = 0;
        root.partNext = 0;
    }

    // ---- Fixed feedback pool; no Repeater model replacement per frame ----
    property var feedbackItems: []
    property int feedbackCount: 0

    function initializeFeedbackState(): void {
        const items = new Array(root.feedbackCapacity);
        for (let i = 0; i < root.feedbackCapacity; ++i)
            items[i] = feedbackRepeater.itemAt(i);
        root.feedbackItems = items;
    }

    function feedbackItem(index: int): var {
        const items = root.feedbackItems;
        let item = items[index];
        if (!item) {
            item = feedbackRepeater.itemAt(index);
            items[index] = item;
        }
        return item;
    }

    function copyFeedback(destination: var, source: var): void {
        destination.message = source.message;
        destination.messageColor = source.messageColor;
        destination.remaining = source.remaining;
    }

    function addFeedback(message: string, messageColor: color): void {
        let writeIndex = 0;
        for (let i = 0; i < root.feedbackCapacity; ++i) {
            const source = root.feedbackItem(i);
            if (!source || source.remaining <= 0)
                continue;
            const destination = root.feedbackItem(writeIndex);
            if (destination !== source) {
                root.copyFeedback(destination, source);
                source.remaining = 0;
            }
            ++writeIndex;
        }

        if (writeIndex >= root.feedbackCapacity) {
            for (let i = 1; i < root.feedbackCapacity; ++i)
                root.copyFeedback(root.feedbackItem(i - 1),
                                  root.feedbackItem(i));
            writeIndex = root.feedbackCapacity - 1;
        }

        const slot = root.feedbackItem(writeIndex);
        if (!slot)
            return;
        slot.message = message;
        slot.messageColor = messageColor;
        slot.remaining = 1;
        root.feedbackCount = Math.min(writeIndex + 1, root.feedbackCapacity);
    }

    function updateFeedbacks(delta: real): void {
        let count = 0;
        for (let i = 0; i < root.feedbackCapacity; ++i) {
            const feedback = root.feedbackItem(i);
            if (!feedback || feedback.remaining <= 0)
                continue;
            feedback.remaining = Math.max(feedback.remaining - delta * 1.1, 0);
            if (feedback.remaining > 0)
                ++count;
        }
        if (count !== root.feedbackCount)
            root.feedbackCount = count;
    }

    function clearFeedbacks(): void {
        for (let i = 0; i < root.feedbackCapacity; ++i) {
            const feedback = root.feedbackItem(i);
            if (feedback)
                feedback.remaining = 0;
        }
        root.feedbackCount = 0;
    }

    // ---- Run lifecycle ----
    function resetRun(startPlaying: bool): void {
        root.clearParticles();
        root.clearFeedbacks();
        root.score = 0;
        root.phase = 1;
        root.laps = root.startLaps;
        root.direction = 1;
        root.pointerS = 0;
        root.perfectStreak = 0;
        root.flash = 0;
        root.shake = 0;
        root.shield = false;
        root.gameOver = false;
        root.playing = startPlaying;
        root.readyT = startPlaying ? 1.2 : 0;
        scene.x = 0;
        scene.y = 0;
        root.buildShape(0);
        root.updateZoneSize();
        root.spawnTargets();
        root.updatePointerVisual();
        if (startPlaying)
            root.addFeedback("READY...", root.colGold);
    }

    function tap(): void {
        if (root.gameOver) {
            if (Date.now() - root.overSinceMs > 700)
                root.resetRun(true);
            return;
        }
        if (!root.playing) {
            root.resetRun(true);
            return;
        }
        if (root.readyT > 0)
            return;
        root.performTap();
    }

    function performTap(): void {
        const distance = root.distanceOnPath(root.pointerS,
                                             root.currentTargetCenter);
        if (distance > root.hitHalfS) {
            root.loseOrUseShield();
            return;
        }

        if (root.targetIndex < root.targetCount - 1) {
            ++root.targetIndex;
            root.addFeedback("1/2", root.colDouble);
            root.burstAtPointer(root.colDouble, 14, 120, 320, 0.5);
            root.updateZoneGeometry();
            return;
        }
        root.finalizeHit(distance, root.targetType);
    }

    function finalizeHit(distance: real, type: int): void {
        ++root.score;
        const perfect = distance <= root.zoneHalfS * root.perfectFraction;
        if (perfect) {
            ++root.perfectStreak;
            root.addFeedback("PERFECT ×" + Math.min(root.perfectStreak + 1, 9),
                             root.colGold);
            root.burstAtPointer(root.colGold, 48, 180, 460, 0.7);
            root.shake = 7;
        } else {
            root.perfectStreak = 0;
            root.burstAtPointer(type === 1 ? root.colGold : root.colAccent,
                                24, 120, 320, 0.5);
        }

        if (type === 1)
            root.addFeedback("GOLD!", root.colGold);
        if (type === 4 && !root.shield) {
            root.shield = true;
            root.addFeedback("SHIELD!", root.colShield);
        }

        root.laps = Math.min(root.laps * root.lapsGrowth, root.maxLaps);
        root.direction *= -1;
        root.flash = 1;

        if (root.score % root.hitsPerPhase === 0) {
            ++root.phase;
            root.laps = Math.min(root.startLaps
                                 * Math.pow(root.phaseSpeedStep, root.phase - 1),
                                 root.maxLaps);
            root.addFeedback("PHASE " + root.phase + " !", root.colAccent);
            root.burstAtPointer(root.colAccent, 48, 180, 460, 0.7);
            root.shake = 12;
        }

        const nextShape = Math.floor(root.score / root.shapeChangeEvery)
                          % root.shapeCount;
        if (nextShape !== root.shapeIdx) {
            const pointerRatio = root.pointerS / root.perimeter;
            root.buildShape(nextShape);
            root.pointerS = pointerRatio * root.perimeter;
        }
        root.updateZoneSize();
        root.spawnTargets();
    }

    function loseOrUseShield(): void {
        if (root.playing && root.shield) {
            root.shield = false;
            root.addFeedback("SHIELD!", root.colShield);
            root.spawnTargets();
            return;
        }
        root.die();
    }

    function die(): void {
        if (!root.playing) {
            root.spawnTargets();
            return;
        }
        root.burstAtPointer(root.colMiss, 32, 150, 400, 0.6);
        root.playing = false;
        root.gameOver = true;
        root.overSinceMs = Date.now();
        root.shake = 14;
        if (root.score > root.best)
            root.best = root.score;
        if (root.phase > root.bestPhase)
            root.bestPhase = root.phase;
    }

    // ---- Vsync-driven loop ----
    function simulate(delta: real): void {
        if (root.gameOver)
            return;

        if (root.readyT > 0) {
            root.readyT = Math.max(root.readyT - delta, 0);
            if (root.readyT === 0) {
                root.addFeedback("GO!", root.colAccent);
                root.flash = 1;
            }
            return;
        }

        const perimeterValue = root.perimeter;
        const travel = perimeterValue * root.laps * delta;
        const previousPointer = root.pointerS;
        const targetExit = root.currentTargetCenter
                           + root.direction * root.hitHalfS;
        const distanceToExit = root.positiveModulo(
                    (targetExit - previousPointer) * root.direction,
                    perimeterValue);
        // Swept detection catches the exit even if a slow frame jumps across
        // the complete target. It fires at the visible core trailing edge.
        const passedTarget = distanceToExit <= travel + 0.0001;

        root.pointerS = root.positiveModulo(
                    previousPointer + travel * root.direction,
                    perimeterValue);
        const distance = root.distanceOnPath(root.pointerS,
                                             root.currentTargetCenter);
        const inside = distance <= root.hitHalfS;

        if (!root.playing) {
            if (inside
                    && distance < root.zoneHalfS * 0.6
                    && Math.random() < 0.35) {
                root.performTap();
                return;
            }
            if (passedTarget)
                root.spawnTargets();
        } else if (passedTarget) {
            root.loseOrUseShield();
        }
    }

    function updateEffects(delta: real): void {
        if (root.flash > 0)
            root.flash = Math.max(root.flash - delta * 4, 0);
        if (root.ghostRemaining > 0)
            root.ghostRemaining = Math.max(root.ghostRemaining - delta, 0);

        if (root.shake > 0) {
            const nextShake = root.shake
                    * (1 - Math.min(delta * 10, 1));
            if (nextShake < 0.05) {
                root.shake = 0;
                scene.x = 0;
                scene.y = 0;
            } else {
                root.shake = nextShake;
            }
        }

        if (root.feedbackCount > 0)
            root.updateFeedbacks(delta);
        if (root.activeParticleCount > 0)
            root.updateParticles(delta);
    }

    function updatePointerVisual(): void {
        const sides = root.sideCount;
        if (sides < 3 || root.gameOver)
            return;

        const perimeterValue = root.perimeter;
        const inverseLength = root.inverseSegmentLength;
        const length = root.segmentLength;
        const xs = root.vertexX;
        const ys = root.vertexY;
        const wrapped = root.positiveModulo(root.pointerS, perimeterValue);
        let segment = Math.floor(wrapped * inverseLength);
        if (segment >= sides)
            segment = sides - 1;
        segment = Math.max(segment, 0);
        const next = (segment + 1) % sides;
        const local = (wrapped - segment * length) * inverseLength;
        pointerItem.x = xs[segment] + (xs[next] - xs[segment]) * local;
        pointerItem.y = ys[segment] + (ys[next] - ys[segment]) * local;
        pointerItem.rotation = root.segmentAngles[segment];
    }

    function updateSceneTransform(): void {
        const shakeValue = root.shake;
        if (shakeValue > 0) {
            scene.x = (Math.random() * 2 - 1) * shakeValue;
            scene.y = (Math.random() * 2 - 1) * shakeValue;
        }
        if (!root.gameOver)
            root.updatePointerVisual();
    }

    function processFrame(frameDelta: real): void {
        const delta = Math.min(Math.max(frameDelta, 0), 0.05);
        root.simulate(delta);
        root.updateEffects(delta);
        root.updateSceneTransform();
    }

    FrameAnimation {
        id: frameLoop
        running: root.visible && root.needsFrames
        onTriggered: root.processFrame(frameLoop.frameTime)
    }

    Component.onCompleted: {
        root.initializeParticleState();
        root.initializeFeedbackState();
        root.rebuildStars();
        root.resetRun(false);
        root.initialized = true;
        root.forceActiveFocus();
    }

    // Space or T both count as a tap, so the game is playable from the
    // keyboard even when the mouse is busy with the installer.
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_T) {
            root.tap();
            event.accepted = true;
        }
    }

    // Calamares slideshow API 2 calls this when the slideshow becomes
    // visible. Re-taking focus keeps Space and T working after another
    // installer page has been on screen.
    function onActivate(): void {
        root.forceActiveFocus();
    }

    TapHandler {
        id: tapHandler
        gesturePolicy: TapHandler.WithinBounds
        onPressedChanged: {
            if (tapHandler.pressed)
                root.tap();
        }
    }

    // ---- Static stars in one scene-graph path instead of 60 QML Items ----
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: -1
            fillRule: ShapePath.WindingFill
            fillColor: Qt.rgba(0.9, 0.93, 0.95, 0.20)
            PathSvg { path: root.starPath }
        }
    }

    // ---- Game scene ----
    Item {
        id: scene
        width: parent.width
        height: parent.height

        // One Shape with multiple ShapePaths avoids four independent renderer
        // objects and their separate preprocessing/synchronization overhead.
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                strokeColor: Qt.rgba(0, 0.9, 1, 0.07)
                strokeWidth: 3
                fillColor: "transparent"
                joinStyle: ShapePath.RoundJoin
                PathPolyline { path: root.echo1Points }
            }
            ShapePath {
                strokeColor: Qt.rgba(0, 0.9, 1, 0.04)
                strokeWidth: 2
                fillColor: "transparent"
                joinStyle: ShapePath.RoundJoin
                PathPolyline { path: root.echo2Points }
            }
            ShapePath {
                strokeColor: root.shield
                    ? Qt.rgba(0.70, 0.88, 0.97, 0.45 + root.flash * 0.55)
                    : Qt.rgba(0.90, 0.93, 0.95, 0.35 + root.flash * 0.65)
                strokeWidth: 8
                fillColor: "transparent"
                joinStyle: ShapePath.RoundJoin
                PathPolyline { path: root.outlinePoints }
            }
            ShapePath {
                strokeColor: Qt.rgba(root.zoneAColor.r, root.zoneAColor.g,
                                     root.zoneAColor.b,
                                     0.28 * root.zoneAAlpha)
                strokeWidth: root.zoneAVisible ? root.zoneGlowStrokeWidth : -1
                capStyle: ShapePath.RoundCap
                fillColor: "transparent"
                PathPolyline { path: root.zoneAPoints }
            }
            ShapePath {
                strokeColor: Qt.rgba(root.zoneAColor.r, root.zoneAColor.g,
                                     root.zoneAColor.b, root.zoneAAlpha)
                strokeWidth: root.zoneAVisible ? root.zoneCoreStrokeWidth : -1
                capStyle: ShapePath.RoundCap
                fillColor: "transparent"
                PathPolyline { path: root.zoneAPoints }
            }
            ShapePath {
                strokeColor: Qt.rgba(root.zoneBColor.r, root.zoneBColor.g,
                                     root.zoneBColor.b, 0.28)
                strokeWidth: root.zoneBVisible ? root.zoneGlowStrokeWidth : -1
                capStyle: ShapePath.RoundCap
                fillColor: "transparent"
                PathPolyline { path: root.zoneBPoints }
            }
            ShapePath {
                strokeColor: root.zoneBColor
                strokeWidth: root.zoneBVisible ? root.zoneCoreStrokeWidth : -1
                capStyle: ShapePath.RoundCap
                fillColor: "transparent"
                PathPolyline { path: root.zoneBPoints }
            }
        }

        Repeater {
            id: particleRepeater
            model: root.partPool
            delegate: Rectangle {
                required property int index

                width: 3 + (index % 4)
                height: width
                radius: width * 0.5
                visible: false
                opacity: 0
            }
        }

        Item {
            id: pointerItem
            visible: !root.gameOver
            Rectangle {
                anchors.centerIn: parent
                width: 52
                height: root.pointerBarThickness
                radius: height * 0.5
                color: root.colRing
            }
            Rectangle {
                anchors.centerIn: parent
                width: root.pointerDotSize
                height: width
                radius: width * 0.5
                color: root.colRing
            }
        }
    }

    // ---- HUD ----
    Text {
        x: 24
        y: 18
        text: "PULSE"
        textFormat: Text.PlainText
        color: root.colAccent
        font.pixelSize: 26
        font.bold: true
        font.letterSpacing: 6
    }
    Text {
        x: 24
        y: 50
        text: "best " + root.best
        textFormat: Text.PlainText
        color: root.colDim
        font.pixelSize: 15
        visible: root.best > 0
    }
    Text {
        x: 24
        y: 72
        text: "⬡ SHIELD"
        textFormat: Text.PlainText
        color: root.colShield
        font.pixelSize: 14
        font.bold: true
        visible: root.shield
    }

    Column {
        visible: !root.gameOver
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.centerY - 46
        spacing: 0
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.score
            textFormat: Text.PlainText
            color: Qt.rgba(0.9, 0.93, 0.95, 0.95)
            font.pixelSize: 64
            font.bold: true
            style: Text.Outline
            styleColor: "#0a0e20"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "PHASE " + root.phase
            textFormat: Text.PlainText
            color: root.phase > 1 ? root.colGold : root.colDim
            font.pixelSize: 17
            font.letterSpacing: 3
        }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.centerY - root.gameRadius - 74
        spacing: 2
        Repeater {
            id: feedbackRepeater
            model: root.feedbackCapacity
            delegate: Text {
                required property int index
                property string message: ""
                property color messageColor: root.colAccent
                property real remaining: 0

                anchors.horizontalCenter: parent.horizontalCenter
                visible: remaining > 0
                text: message
                textFormat: Text.PlainText
                color: messageColor
                opacity: Math.min(remaining, 1)
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
            }
        }
    }

    // Demo-only objects are destroyed once a person starts playing.
    Loader {
        active: !root.playing && !root.gameOver
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.centerY + root.gameRadius + 40
        sourceComponent: Component {
            Rectangle {
                id: demoButton
                width: demoText.implicitWidth + 44
                height: 44
                radius: 22
                color: Qt.rgba(0, 0.9, 1, 0.10)
                border.color: Qt.rgba(0, 0.9, 1, 0.45)
                border.width: 1

                SequentialAnimation {
                    running: root.visible
                    loops: Animation.Infinite
                    OpacityAnimator {
                        target: demoButton
                        from: 0.55
                        to: 1
                        duration: 900
                        easing.type: Easing.InOutSine
                    }
                    OpacityAnimator {
                        target: demoButton
                        from: 1
                        to: 0.55
                        duration: 900
                        easing.type: Easing.InOutSine
                    }
                }
                Text {
                    id: demoText
                    anchors.centerIn: parent
                    text: "Click, or press T or Space, to play while installing!"
                    textFormat: Text.PlainText
                    color: "#dff8ff"
                    font.pixelSize: 17
                    font.bold: true
                }
            }
        }
    }

    // Game-over objects exist only while needed, reducing normal-play memory.
    Loader {
        active: root.gameOver
        anchors.fill: parent
        sourceComponent: Component {
            Rectangle {
                color: Qt.rgba(0.03, 0.04, 0.10, 0.82)
                Column {
                    anchors.centerIn: parent
                    spacing: 10
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "GAME OVER"
                        textFormat: Text.PlainText
                        color: root.colMiss
                        font.pixelSize: 34
                        font.bold: true
                        font.letterSpacing: 6
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.score
                        textFormat: Text.PlainText
                        color: root.colRing
                        font.pixelSize: 72
                        font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "phase " + root.phase + "  ·  best " + root.best
                        textFormat: Text.PlainText
                        color: root.colDim
                        font.pixelSize: 17
                    }
                    Item { width: 1; height: 10 }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: gameLinkColumn.implicitWidth + 56
                        height: gameLinkColumn.implicitHeight + 30
                        radius: 14
                        color: Qt.rgba(1, 0.78, 0.34, 0.10)
                        border.color: Qt.rgba(1, 0.78, 0.34, 0.55)
                        border.width: 1
                        Column {
                            id: gameLinkColumn
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "Take Pulse on your Android"
                                textFormat: Text.PlainText
                                color: root.colGold
                                font.pixelSize: 17
                                font.bold: true
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "pulse.talesam.org"
                                textFormat: Text.PlainText
                                color: "#ffe2a8"
                                font.pixelSize: 21
                                font.bold: true
                                font.letterSpacing: 1
                            }
                        }
                    }
                    Item { width: 1; height: 6 }
                    Text {
                        id: replayText
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "click, or press T or Space, to play again"
                        textFormat: Text.PlainText
                        color: root.colDim
                        font.pixelSize: 15
                        SequentialAnimation {
                            running: root.visible
                            loops: Animation.Infinite
                            OpacityAnimator {
                                target: replayText
                                from: 0.4
                                to: 1
                                duration: 800
                            }
                            OpacityAnimator {
                                target: replayText
                                from: 1
                                to: 0.4
                                duration: 800
                            }
                        }
                    }
                }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        visible: !root.gameOver
        text: "Full game on Android · pulse.talesam.org"
        textFormat: Text.PlainText
        color: Qt.rgba(0.54, 0.58, 0.65, 0.8)
        font.pixelSize: 14
    }
}
