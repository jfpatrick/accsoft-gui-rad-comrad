title = 'Rules example implemented fully in code'
description = 'This example shows how to use rules engine to attach dynamic behavior to widgets depending on the ' \
              'values coming from the control system. Device named "DemoDevice" has a ' \
              'single property "Acquisition" with a single string field "Demo", which produces a floating point value ' \
              'between <code>0</code> and <code>1</code>. If the value is above <code>0.5</code>, the color of the ' \
              '<code>CLabel</code> and the <code>CLed</code> will become red.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
