title = 'Simple color rules example'
description = 'This example shows how to apply color to a <code>CLabel</code> and a <code>CLed</code> based on the ' \
              'value displayed. Device named "DemoDevice" has a single property "Acquisition" with a single string ' \
              'field "Demo", which produces a float value between <code>0</code> and <code>1</code>. If the value is ' \
              'above <code>0.5</code>, the color will become red.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
