title = 'Basic CPropertyEdit example'
description = 'This example shows how to create a display that allows you to control the whole property with ' \
              'multiple fields via a single CPropertyEdit widget. This widget lets you read and write values of ' \
              'multiple fields of the same property at once. In this example, the top widget contains both ' \
              '"Get" and "Set" buttons to give user full control of when to send and retrieve values from the ' \
              'control system. The bottom widget does not have "Get" button, and thus will automatically subscribe ' \
              'for any updates in the control system. The middle label, shows rough representation of the value ' \
              'stored in the device property.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
