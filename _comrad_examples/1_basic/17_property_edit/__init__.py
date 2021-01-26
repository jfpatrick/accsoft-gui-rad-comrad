title = 'Basic CPropertyEdit example'
description = 'This example shows how to create a display that allows you to control the whole property with ' \
              'multiple fields via a single <code>CPropertyEdit</code> widget. This widget lets you read and write ' \
              'values of multiple fields of the same property at once. In this example, the left widget contains both ' \
              '"Get" and "Set" buttons to give user full control of when to send and retrieve values from the ' \
              'control system. The right widget does not have "Get" button, and thus will <strong>automatically ' \
              'subscribe</strong> to updates in the control system. The bottom label shows a rough representation ' \
              'of the value stored in the device property.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
