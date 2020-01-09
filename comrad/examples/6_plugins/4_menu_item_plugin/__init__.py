title = 'Menu item plugin'
description = 'Menu plugins allow you not only define QAction, but instead bring the whole QMenu. This is ' \
              'particularly useful when you have a plugin that contains more than a single action. You can also ' \
              'arrange submenu in your preferred order and add menu separators. The following example, adds a new ' \
              'item "Plugin bundle" under "Demo" menu defining two separate actions. Each action produces a console ' \
              'message.'

entrypoint = 'app.ui'

launch_arguments = ['--menu-plugin-path', '~example']
