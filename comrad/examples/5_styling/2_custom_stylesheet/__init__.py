title = 'Custom stylesheet example'
description = 'User can pass a stylesheet to change the visual style of the entire application. This is based on ' \
              'Qt\'s QSS engine, that resembles web\'s cascading style sheets (CSS) with some minor customizations ' \
              'for Qt. More info on how to use them is available in ' \
              '<a href="https://doc.qt.io/qt-5/stylesheet-examples.html#customizing-a-qpushbutton-using-the-box-model">Qt ' \
              'documentation</a>.'
entrypoint = 'app.ui'
launch_arguments = ['--stylesheet', '~example/custom_stylesheet.qss']