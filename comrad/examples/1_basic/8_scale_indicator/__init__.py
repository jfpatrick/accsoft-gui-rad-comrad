title = 'Basic CScaleIndicator example'
description = 'This example shows how to create a display with a single ComRAD scale indicator edit and connect it ' \
              'to a field of a device. Device named "DemoDevice" has a single property "Acquisition" with a single ' \
              'numeric field "Demo", which bounces in range 0.0-1.0 with a 0.01 step 30 times per second.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'