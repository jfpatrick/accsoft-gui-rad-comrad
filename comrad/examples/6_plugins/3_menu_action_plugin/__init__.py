title = 'Menu action plugin'
description = 'Menu plugin lets you add a new menu item, or modify an existing menu item. It contains an associated ' \
              'action that is triggered. This example contains 4 plugins in a single file: "Click me!" item added to ' \
              'the existing "File" menu; "Click me!" button added to a newly created "Demo" submenu inside existing ' \
              '"File" menu; "Click me!" button added to a newly created "Demo" submenu; "Click me!" button added to ' \
              'a newly created "Submenu" sub-menu inside newly created "Demo" menu. All of these plugins do exactly ' \
              'the same thing - produce a console message "Plugin triggered!".'

entrypoint = 'app.ui'

launch_arguments = ['--menu-plugin-path', '~example']
