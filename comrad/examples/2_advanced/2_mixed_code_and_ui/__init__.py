title = 'Basic CLabel example combining code and Qt Designer'
description = 'This example shows how to create a display with Qt Designer, while still modify certain parts in code.' \
              'For instance, in this example the UI is laid out in Qt Desinger, while JAPC connection is specified ' \
              'in code. Device named "DemoDevice" has a single property "Acquisition" with a single string field ' \
              '"Demo", which toggles Tick-Tock labels once a second. In order to access widgets as instance ' \
              'variables in code, you have to use the same variable name, as the identifier in the "Object ' \
              'Inspector" of Qt Designer.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'