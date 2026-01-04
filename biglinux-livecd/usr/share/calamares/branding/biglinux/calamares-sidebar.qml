import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Rectangle {
  id: sideBar;
  
  SystemPalette {
    id: systemPalette
  }
  
  color: systemPalette.window;
  
  antialiasing: true
  
  Rectangle {
    anchors.fill: parent
    anchors.rightMargin: 35/2
    color: Branding.styleString(Branding.SidebarBackground)
  }
  
  ListView {
    id: list
    anchors.leftMargin: 12
    anchors.fill: parent
    model: ViewManager
    interactive: false
    spacing: 0
    delegate: RowLayout {
      visible: index!=0
      height: index==0?0:50
      width: parent.width
      
      Text {
        Layout.fillWidth: true
        fontSizeMode: Text.Fit
        color: Branding.styleString(Branding.SidebarText)
        text: display;
        font.pointSize : 12
        minimumPointSize: 5
        Layout.alignment: Qt.AlignLeft|Qt.AlignVCenter
        clip: true
      }
      Item {
        Layout.fillHeight: true
        Layout.preferredWidth: 35
        
        Rectangle {
          anchors.centerIn: parent
          id: image
          height: parent.width*0.65
          width: height
          radius: height/2
          color: {
            if (index>ViewManager.currentStepIndex) {
              return systemPalette.mid;
            }
            return systemPalette.highlight
          }
          z: 10
        }
        Rectangle {
          color: {
            if (index>ViewManager.currentStepIndex && index!=1) {
              return systemPalette.mid;
            }
            return systemPalette.highlight;
            
          }
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.bottom: image.verticalCenter
          height: parent.height/2
          width: 5
          z: 0
        }
        Rectangle {
          color: {
            if (index<ViewManager.currentStepIndex || ViewManager.currentStepIndex==list.count-1) {
              return systemPalette.highlight;
            }
            return systemPalette.mid;
          }
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.top: image.verticalCenter
          height: parent.height/2
          width: 5
          //visible: (index !== (list.count - 1))
          z: 0
        }
        Shape {
          visible: index == ViewManager.currentStepIndex
          id: shape
          anchors.fill: parent
          smooth: true
          layer.enabled: true
          layer.samples: 8
          
          ShapePath {
            fillColor: "transparent"
            strokeColor: systemPalette.highlight
            strokeWidth: 3
            capStyle: ShapePath.FlatCap
            
            PathAngleArc {
              centerX: shape.width/2; centerY: shape.height/2
              radiusX: 15; radiusY: 15
              startAngle: 0
              sweepAngle: 360
            }
          }
        }
      }
    }
    header: RowLayout {
      height: 85
      anchors.right: parent.right
      anchors.left: parent.left
      Item {
        Layout.fillWidth: true
      }
      
      Item {
        width: 70
        height: 70
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -15
        
        Image {
          anchors.fill: parent
          source: "logo.svg"
          smooth: true
          fillMode: Image.PreserveAspectFit
        }
      }
      
      // Label {
      //     text: "BigLinux"
      //     font.pointSize: 16
      //     font.family: "Comfortaa"
      //     color: Branding.styleString(Branding.SidebarText)
      //     Layout.fillWidth: true
      // }
      Item {
        Layout.fillHeight: true
        Layout.preferredWidth: 35
        
        Rectangle {
          color: systemPalette.highlight
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.top: parent.top
          height: parent.height
          width: 5
          z: 0
        }
      }
    }
  }
  Item {
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    height: list.height - list.contentHeight
    width: 35
    Rectangle {
      color: {
        if (ViewManager.currentStepIndex==list.count-1) {
          return systemPalette.highlight;
        }
        return systemPalette.mid;
      }
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      height: parent.height
      width: 5
      z: 0
    }
  }
}
