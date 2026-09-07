import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    readonly property int firstVisibleStep: 1
    readonly property int headerHeight: 92
    readonly property int stepHeight: 56
    readonly property int indicatorColumnWidth: 36
    readonly property int indicatorSize: 22
    readonly property int horizontalPadding: 14

    readonly property color sidebarBackground:
        Branding.styleString(Branding.SidebarBackground)
    readonly property color sidebarText:
        Branding.styleString(Branding.SidebarText)
    readonly property color currentBackground:
        Branding.styleString(Branding.SidebarBackgroundCurrent)
    readonly property color currentText:
        Branding.styleString(Branding.SidebarTextCurrent)
    readonly property color pendingIndicator: Qt.rgba(1, 1, 1, 0.35)

    color: sidebarBackground

    LayoutMirroring.enabled:
        Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    Rectangle {
        id: header

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root.headerHeight
        color: root.sidebarBackground

        Image {
            id: productLogo

            anchors.centerIn: parent
            width: 68
            height: 68
            source: Branding.imagePath(Branding.ProductLogo)
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true

            Accessible.role: Accessible.Graphic
            Accessible.name: qsTr("%1 logo").arg(Branding.shortProductName())
        }
    }

    ListView {
        id: stepList

        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.horizontalPadding
        anchors.rightMargin: root.horizontalPadding
        anchors.bottomMargin: 12

        model: ViewManager
        clip: true
        spacing: 4
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        delegate: Item {
            id: stepDelegate

            readonly property int currentVisibleStep:
                Math.max(ViewManager.currentStepIndex, root.firstVisibleStep)
            readonly property bool isCurrent:
                index === stepDelegate.currentVisibleStep
            readonly property bool isCompleted:
                index < ViewManager.currentStepIndex
            readonly property bool isVisibleStep:
                index >= root.firstVisibleStep

            width: ListView.view ? ListView.view.width : 0
            height: isVisibleStep ? root.stepHeight : 0
            visible: isVisibleStep

            Accessible.role: Accessible.ListItem
            Accessible.name: stepLabel.text
            Accessible.description: {
                if (isCurrent) {
                    return qsTr("Current installation step")
                }
                if (isCompleted) {
                    return qsTr("Completed installation step")
                }
                return qsTr("Pending installation step")
            }

            Rectangle {
                anchors.fill: parent
                radius: 7
                color: stepDelegate.isCurrent
                    ? root.currentBackground
                    : "transparent"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                Item {
                    Layout.preferredWidth: root.indicatorColumnWidth
                    Layout.fillHeight: true

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        height: root.stepHeight / 2
                        width: 3
                        visible: index > root.firstVisibleStep
                        color: stepDelegate.isCompleted || stepDelegate.isCurrent
                            ? root.currentBackground
                            : root.pendingIndicator
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        height: root.stepHeight / 2
                        width: 3
                        visible: index < stepList.count - 1
                        color: stepDelegate.isCompleted
                            ? root.currentBackground
                            : root.pendingIndicator
                    }

                    Rectangle {
                        id: stepIndicator

                        anchors.centerIn: parent
                        width: root.indicatorSize
                        height: root.indicatorSize
                        radius: width / 2
                        color: {
                            if (stepDelegate.isCurrent) {
                                return root.currentText
                            }
                            if (stepDelegate.isCompleted) {
                                return root.currentBackground
                            }
                            return "transparent"
                        }
                        border.width: 2
                        border.color: stepDelegate.isCurrent
                            ? root.currentText
                            : stepDelegate.isCompleted
                                ? root.currentBackground
                                : root.pendingIndicator

                        Text {
                            anchors.centerIn: parent
                            visible: stepDelegate.isCompleted
                            text: "✓"
                            color: root.currentText
                            font.bold: true
                            font.pixelSize: 14
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            visible: stepDelegate.isCurrent
                            width: 8
                            height: 8
                            radius: 4
                            color: root.currentBackground
                        }
                    }
                }

                Label {
                    id: stepLabel

                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    text: display
                    color: stepDelegate.isCurrent
                        ? root.currentText
                        : root.sidebarText
                    font.bold: stepDelegate.isCurrent
                    font.pointSize: 11
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
