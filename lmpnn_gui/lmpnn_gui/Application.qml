import QtQuick 2.15

Text {
  required property QtObject app

  width: 200
  height: 200
  text: app.text
}
