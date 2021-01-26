title = 'CLabel example implemented fully in code'
description = 'This example shows how to create a display without Qt Designer files. The display features a ' \
              'single ComRAD label and connects it to a field of a device. Device named "DemoDevice" has a ' \
              'single property "Acquisition" with a single string field "Demo", which toggles Tick-Tock ' \
              'labels once a second.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
