title = 'Widget plugin configuration'
description = 'Widget plugins (both toolbar and status bar) can be configured by the user via launch arguments. ' \
              'Such arguments are assembled into a dictionary and passed at widget creation time to the plugin. For ' \
              'instance, having a launch argument "<code>--window-plugin-config com.example.key1=val1 ' \
              'com.example.key2.subkey1=val2</code>" will produce a dictionary<br/>' \
              '<code>{<br/>' \
              '&nbsp;&nbsp;"key1": "val1",<br/>' \
              '&nbsp;&nbsp;"key2.subkey1": "val2"<br/>' \
              '}</code><br/>' \
              'that is passed to the plugin with ID "com.example".<br/>' \
              '<br/>' \
              'In this example, we accept an arbitrary string' \
              '"name", which is passed to a plugin with ID "com.example.demo", and which will influence the label ' \
              'displayed in the toolbar.'

entrypoint = 'app.ui'

launch_arguments = ['--nav-plugin-path', '~example', '--window-plugin-config', 'com.example.demo.name=Sam', '--']
