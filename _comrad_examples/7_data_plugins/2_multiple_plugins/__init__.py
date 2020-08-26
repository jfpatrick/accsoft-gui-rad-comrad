title = 'Multiple data plugins with the same connection'
description = 'Custom data plugin requires 2 classes to be ' \
              'declared: connection and plugin. Connection does the actual data handling and can serve multiple ' \
              'plugins. Plugin simply links a protocol to a concrete connection class.' \
              'This example defines the 2 different plugins that work through the same connection. Similar to ' \
              'basic example, it will produce random integers. This time, our protocol will encode multiplier ' \
              'for the produced value. It does not mean that it is meant for it, but we simply implement recognition ' \
              'of different protocols. E.g. "random2://[1,3]" will tell plugin to produce random integers between 1 ' \
              'and 3 that are multiplied by 2. Likewise, "random3://[1,3]" will produce random integers multiplied ' \
              'by 3. Resulting values are pushed to a simple scrolling plot.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
