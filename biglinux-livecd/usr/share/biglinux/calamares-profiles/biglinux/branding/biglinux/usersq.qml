import io.calamares.core 1.0
import io.calamares.ui 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "i18n.js" as I18n

Page {
    id: root

    LayoutMirroring.enabled: Qt.application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    readonly property string localeKey: Qt.locale().name + "|" + qsTr("__biglinux_language_marker__")
    property bool showPasswords: false
    readonly property bool animateArtwork: visible

    function tr(source) { return I18n.translate(source, localeKey) }

    function initials(name) {
        var parts = String(name).trim().split(/\s+/)
        if (!parts.length || parts[0] === "") return "?"
        if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
    }

    padding: 20
    background: Rectangle { color: root.palette.window }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        PageHeader {
            Layout.fillWidth: true
            title: root.tr("User account")
            description: root.tr("Create your account and choose the name used by this computer on the network.")
        }

        // Two passwords in a row need explaining, and the disk one carries a
        // restriction the boot prompt cannot state by itself. Whether the user
        // asked for encryption is not knowable here: the partition module only
        // records that once the installation starts, so the text is worded for
        // both cases instead of appearing conditionally.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: diskNotice.implicitHeight + 20
            radius: 8
            color: Qt.rgba(root.palette.highlight.r, root.palette.highlight.g,
                           root.palette.highlight.b, 0.10)
            border.width: 1
            border.color: Qt.rgba(root.palette.highlight.r, root.palette.highlight.g,
                                  root.palette.highlight.b, 0.35)

            Accessible.role: Accessible.StaticText
            Accessible.name: diskNoticeTitle.text + ". " + diskNoticeBody.text

            ColumnLayout {
                id: diskNotice

                anchors.fill: parent
                anchors.margins: 10
                spacing: 2

                Label {
                    id: diskNoticeTitle

                    Layout.fillWidth: true
                    text: root.tr("If you turned on disk encryption")
                    color: root.palette.windowText
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                }

                Label {
                    id: diskNoticeBody

                    Layout.fillWidth: true
                    text: root.tr("The disk password from the previous screen must have no accents and no letter c-cedilla: at boot the keyboard is not configured yet and the disk would not unlock. The password below is a different one, for signing in to your account.")
                    color: root.palette.windowText
                    opacity: 0.85
                    wrapMode: Text.WordWrap
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            NativeFrame {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 590
                padding: 14

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Image {
                            Layout.preferredWidth: 28
                            Layout.preferredHeight: 28
                            source: "visuals/identity.svg"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.tr("Identity")
                            font.weight: Font.DemiBold
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 14
                        rowSpacing: 7

                        Label { text: root.tr("Your name") }
                        TextField {
                            Layout.fillWidth: true
                            enabled: config.isEditable("fullName")
                            placeholderText: root.tr("Full name")
                            text: config.fullName
                            onTextEdited: config.setFullName(text)
                        }

                        Label { text: root.tr("Login name") }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            TextField {
                                Layout.fillWidth: true
                                enabled: config.isEditable("loginName")
                                text: config.loginName
                                onTextEdited: config.setLoginName(text)
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: config.loginNameStatus !== ""
                                text: config.loginNameStatus
                                color: root.palette.placeholderText
                                wrapMode: Text.WordWrap
                            }
                        }

                        Label { text: root.tr("Computer name") }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            TextField {
                                Layout.fillWidth: true
                                text: config.hostname
                                onTextEdited: config.setHostName(text)
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: config.hostnameStatus !== ""
                                text: config.hostnameStatus
                                color: root.palette.placeholderText
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: root.palette.mid
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Image {
                            Layout.preferredWidth: 28
                            Layout.preferredHeight: 28
                            source: "visuals/lock.svg"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.tr("Security")
                            font.weight: Font.DemiBold
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 14
                        rowSpacing: 7

                        Label { text: root.tr("Password") }
                        TextField {
                            id: passwordField
                            Layout.fillWidth: true
                            text: config.userPassword
                            echoMode: root.showPasswords ? TextInput.Normal : TextInput.Password
                            inputMethodHints: Qt.ImhNoAutoUppercase
                            onTextEdited: config.setUserPassword(text)
                        }

                        Label { text: root.tr("Repeat password") }
                        TextField {
                            id: repeatField
                            Layout.fillWidth: true
                            text: config.userPasswordSecondary
                            echoMode: root.showPasswords ? TextInput.Normal : TextInput.Password
                            inputMethodHints: Qt.ImhNoAutoUppercase
                            onTextEdited: config.setUserPasswordSecondary(text)
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: repeatField.text.length > 0

                        Rectangle {
                            Layout.preferredWidth: 8
                            Layout.preferredHeight: 8
                            radius: 4
                            color: repeatField.text === passwordField.text ? "#2E7D32" : "#B00020"
                        }

                        Label {
                            Layout.fillWidth: true
                            text: repeatField.text === passwordField.text
                                  ? root.tr("The passwords match.")
                                  : root.tr("The passwords do not match.")
                            color: repeatField.text === passwordField.text ? "#2E7D32" : "#B00020"
                            wrapMode: Text.WordWrap
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: config.userPasswordMessage !== ""
                                 && config.userPasswordMessage !== "OK!"
                                 && config.userPasswordMessage !== "OK"
                        text: config.userPasswordMessage
                        color: root.palette.placeholderText
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        CheckBox {
                            text: root.tr("Show passwords")
                            checked: root.showPasswords
                            onToggled: root.showPasswords = checked
                        }

                        CheckBox {
                            text: root.tr("Log in automatically")
                            checked: config.doAutoLogin
                            onToggled: config.setAutoLogin(checked)
                        }
                    }

                    CheckBox {
                        id: reusePassword
                        visible: config.writeRootPassword
                        text: root.tr("Use the user password for the administrator account")
                        checked: config.reuseUserPasswordForRoot
                        onToggled: config.setReuseUserPasswordForRoot(checked)
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: config.writeRootPassword && !reusePassword.checked
                        columns: 2
                        columnSpacing: 14
                        rowSpacing: 7

                        Label { text: root.tr("Root password") }
                        TextField {
                            Layout.fillWidth: true
                            text: config.rootPassword
                            echoMode: root.showPasswords ? TextInput.Normal : TextInput.Password
                            onTextEdited: config.setRootPassword(text)
                        }

                        Label { text: root.tr("Repeat root password") }
                        TextField {
                            Layout.fillWidth: true
                            text: config.rootPasswordSecondary
                            echoMode: root.showPasswords ? TextInput.Normal : TextInput.Password
                            onTextEdited: config.setRootPasswordSecondary(text)
                        }
                    }

                    CheckBox {
                        visible: config.permitWeakPasswords
                        text: root.tr("Require a strong password")
                        checked: config.requireStrongPasswords
                        onToggled: config.setRequireStrongPasswords(checked)
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            NativeFrame {
                Layout.preferredWidth: 240
                Layout.fillHeight: true
                visible: root.width >= 720
                padding: 16

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10


                    Label {
                        Layout.fillWidth: true
                        text: root.tr("Account preview")
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 92
                        Layout.preferredHeight: 92
                        radius: 46
                        color: root.palette.highlight

                        Label {
                            anchors.centerIn: parent
                            text: root.initials(config.fullName)
                            color: root.palette.highlightedText
                            font.pixelSize: 30
                            font.weight: Font.DemiBold
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: config.fullName !== "" ? config.fullName : root.tr("Your name")
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.leftMargin: 12
                        Layout.rightMargin: 12
                        Layout.preferredHeight: 1
                        color: root.palette.mid
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 7

                        Image {
                            Layout.preferredWidth: 20
                            Layout.preferredHeight: 20
                            source: "visuals/computer.svg"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }

                        Label {
                            Layout.fillWidth: true
                            text: config.hostname
                            color: root.palette.placeholderText
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideMiddle
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
