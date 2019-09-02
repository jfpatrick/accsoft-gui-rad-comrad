title = 'CLabel example integrating Python code generated from Qt Designer file using multiple inheritance'
description = 'This example shows how to create a display with Qt Designer, while still modify certain parts in code.' \
              'For users that want to have auto-complete and other assistance in their IDE, UI has to be converted ' \
              'into code at the development stage. pyuic is a tool that generates Python snippet from the *.ui file ' \
              'User then includes this file in his code and can leverage full power of IDE. The downside of this ' \
              'approach is an additional step, where he has to run the generation procedure everytime Qt Designer ' \
              'file is altered. In this example the UI is laid out in Qt Desinger, while JAPC connection is specified ' \
              'in code. Qt Designer file is converted into code using "pyuic app.ui > generated.py" command. ' \
              'Device named "DemoDevice" has a single property "Acquisition" with a single string field ' \
              '"Demo", which toggles Tick-Tock labels once a second. In order to access widgets as instance ' \
              'variables in code, you have to use the same variable name, as the identifier in the "Object ' \
              'Inspector" of Qt Designer.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
