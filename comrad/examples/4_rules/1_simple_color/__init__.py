title = 'Simple color rules example'
description = 'This example shows how to apply color to a label based on the value displayed. Device named ' \
              '"DemoDevice" has a single property "Acquisition" with a single string field "Demo", which ' \
              'produces a float value between 0 and 1. If the value is above 0.5, the color of the label will ' \
              'become red.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
