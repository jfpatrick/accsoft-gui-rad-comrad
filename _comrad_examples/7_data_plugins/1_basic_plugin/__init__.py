title = 'Basic data plugin'
description = 'Data plugins allow you to define custom data sources, augmenting standard channels, such as japc://.' \
              'Plugin classes are defined in files ending with "_plugin.py". These files should be kept in ' \
              'directories that are passed via either COMRAD_DATA_PLUGIN_PATH environment variable, or ' \
              '--extra-data-plugin-path command line argument. One can verify that plugins have been correctly ' \
              'loaded by inspecting About dialog, "Data Plugins" tab. This example defines the most basic ' \
              'plugin that emulates random integer generated once a second, constrained within a range specified ' \
              'in the address. E.g. "random://[5,10]" will tell plugin to produce random integers between 5 and 10. ' \
              'Produced values are pushed to a simple scrolling plot. Custom data plugin requires 2 classes to be ' \
              'declared: connection and plugin. Connection does the actual data handling and can serve multiple ' \
              'plugins. Plugin simply links a protocol to a concrete connection class.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
