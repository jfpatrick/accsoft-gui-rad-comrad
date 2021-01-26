title = 'Multiple data plugins with the same connection'
description = 'Custom data plugin requires 2 classes to be ' \
              'declared: connection and plugin. Connection does the actual data handling and can serve multiple ' \
              'plugins. Plugin simply links a protocol to a concrete connection class.<br/>' \
              '<br/>' \
              'This example defines the 2 different plugins that work through the same connection. Similar to ' \
              '<strong>7.1. Basic Plugin</strong> example, it will produce random integers. This time, our protocol ' \
              'will encode a multiplier for the produced value. Not that it is meant for it, but we simply ' \
              'showcase the recognition of different protocols. E.g. "<code>random2://[1,3]</code>" will tell ' \
              'plugin to produce random integers between <code>1</code> and <code>3</code> that are multiplied by ' \
              '<code>2</code>. Likewise, "<code>random3://[1,3]</code>" will produce random integers multiplied ' \
              'by <code>3</code>. Resulting values are pushed to a simple <code>CScrollingPlot</code>.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
