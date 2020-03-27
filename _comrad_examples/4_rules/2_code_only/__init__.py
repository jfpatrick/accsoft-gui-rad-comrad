title = 'Rules example implemented fully in code'
description = 'This example shows how to use rules engine to attach dynamic behavior to widgets depending on the' \
              'values coming from the control system. Device named "DemoDevice" has a ' \
              'single property "Acquisition" with a single string field "Demo", which produces a float value between ' \
              '0 and 1. If the value is above 0.5, the color of the label and the LED will become red.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
