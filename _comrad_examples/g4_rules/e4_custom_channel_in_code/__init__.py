title = 'Simple color rules with custom channels in code example'
description = 'This example is similar to <strong>4.3. Custom Channel</strong> but implemented in code. ' \
              'It applies color to a <code>CLabel</code> and a <code>CLed</code> based on the ' \
              'value from different channels than the one displayed by the widget. Device named "DemoDevice" has ' \
              'a property "Acquisition" to retrieve data, "Color" ' \
              'that is non-PPM and will be connected to a rule of the label, and another called "ColorMultiplexed" ' \
              'that is PPM and will be connected to the <code>CLed</code>. Each of the properties has single float ' \
              'field "Demo", ' \
              'which produces a float value between <code>0</code> and <code>1</code>. If the value is ' \
              'above <code>0.5</code> (for the rule-related channels), the color will become red.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
