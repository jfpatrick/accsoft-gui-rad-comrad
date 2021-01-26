title = 'Menu action plugin'
description = 'Menu plugin lets you add a new menu item, or modify an existing menu item. It contains an associated ' \
              'action that is triggered. This example contains 4 plugins in a single file:' \
              '<ul>' \
              '<li>"Click me!" item added to the existing "File" menu</li>' \
              '<li>"Click me!" button added to a newly created "Demo" submenu inside existing "File" menu</li>' \
              '<li>"Click me!" button added to a newly created "Demo" submenu</li>' \
              '<li>"Click me!" button added to a newly created "Submenu" sub-menu inside newly created "Demo" menu</li>' \
              '</ul><br/>' \
              'All of these plugins do exactly the same thing - produce a console message "Plugin triggered!".'

entrypoint = 'app.ui'

launch_arguments = ['--menu-plugin-path', '~example']
