title = 'Basic PPM example'
description = 'This example shows how to access PPM device/properties that have either cycle-bound acquisition ' \
              'properties or multiplexed settings. The cycle selector is specified as a part of address, therefore ' \
              'take a look at the "channel" property of the label. The simulated device produces 2 different values ' \
              'on the same property and field, tagged with different cycle identifiers. The UI contains 2 labels ' \
              'that each read a certain cycle, therefore displaying different information.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
