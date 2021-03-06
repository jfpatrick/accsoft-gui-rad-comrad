title = 'Toolbar action plugin'
description = 'This example shows how to create a plugin that adds a new toolbar button with the custom action.' \
              'Here, "Click me!" button will be created with the android icon. Clicking it should produce a log ' \
              'output message "Action triggered!". Notice, that whenever you create action-based plugins, ' \
              'a new menu "Plugins"➔"Toolbar" appears, containing an alternative way of accessing the plugin. Besides ' \
              'features found in the sample code, you can also control whether the button snaps to the left or right ' \
              'by altering its <code>position</code> property. In addition, <code>gravity</code> property will ' \
              'order all plugins with the same <code>position</code> value by weight, where greater ' \
              '<code>gravity</code> value means - closer to the edge. Plugins are searched for in the given path, ' \
              'assuming that its filename should have suffix "_plugin.py".'

entrypoint = 'app.ui'

launch_arguments = ['--nav-plugin-path', '~example']
