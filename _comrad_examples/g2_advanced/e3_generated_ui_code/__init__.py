title = 'CLabel example integrating Python code generated from Qt Designer file using multiple inheritance'
description = 'This example shows how to create a display with Qt Designer, while still modifying certain parts in ' \
              'code. For users that want to have auto-complete and other assistance in their IDE, UI has to be ' \
              'converted into code at the development stage. <i>pyuic5</i> is a tool that generates Python snippet ' \
              'from the <code>*.ui</code> files. Generated code is then included by the user and can leverage full ' \
              'power of IDE. The downside of this approach is an additional step, where generation needs to be run ' \
              'every time Qt Designer file is altered.<br/>' \
              '<br/>' \
              'In this example, the UI is laid out in Qt Desinger, while JAPC connection is ' \
              'specified in code. Qt Designer file is converted into code using "<code>pyuic5 app.ui > ' \
              'generated.py</code>" command. Device named "DemoDevice" has a single property "Acquisition" with a ' \
              'single string field "Demo", which toggles Tick-Tock labels once a second. In order to access widgets ' \
              'as instance variables in code, you have to use the same variable name, as the identifier in the ' \
              '"Object Inspector" of Qt Designer.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
