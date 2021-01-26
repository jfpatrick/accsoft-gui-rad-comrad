title = 'Basic multiplexed (PPM) devices example'
description = 'This example shows how to access multiplexed device/properties that have either cycle-bound ' \
              'acquisition properties or multiplexed settings. The cycle selector is specified via ' \
              '<code>CContextFrame</code> container that will impose a given selector on all of its child widgets. ' \
              'In this case, there are 2 <code>CContextFrame</code>s, each defining their own selector, and 2 labels ' \
              'are placed within each frame so that they display data from different cycles. You can inspect ' \
              'connections with menu "View"➔"Show Connections...". The simulated device produces 2 different values ' \
              'on the same property and field, tagged with different cycle identifiers.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
