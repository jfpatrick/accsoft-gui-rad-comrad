title = 'Basic data plugin'
description = 'Data plugins allow you to define custom data sources, augmenting standard channels, such as ' \
              '<i>japc://</i>. Plugin classes are defined in files ending with "_plugin.py". These files should be ' \
              'kept in directories that are passed via either <code>$COMRAD_DATA_PLUGIN_PATH</code> environment ' \
              'variable, or "<code>--extra-data-plugin-path</code>" command line argument. One can verify that ' \
              'plugins have been correctly loaded by inspecting "About" dialog, "Data Plugins" tab.<br/>' \
              '<br/>' \
              'This example defines the most basic plugin that emulates random integer generated once a second, ' \
              'constrained within a range specified in the address. E.g. "<code>random://[5,10]</code>" will tell ' \
              'plugin to produce random integers between <code>5</code> and <code>10</code>. Produced values are ' \
              'pushed to a simple <code>CScrollingPlot</code>. Custom data plugin requires 2 classes to be ' \
              'declared: connection and plugin. Connection does the actual data handling and can serve multiple ' \
              'plugins. Plugin simply links a protocol to a concrete connection class.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
