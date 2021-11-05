title = 'Dynamic toolbar action plugin'
description = 'This example shows how to create an action plugin that can dynamically change properties of the ' \
              'action, for instance its title. This is achieved by extending declarative approach of ' \
              '<strong>6.1. Toolbar action plugin</strong>, with a custom logic inside <code>create_action()</code> ' \
              'method, where we can actually get hands on the created action object and later reset its title ' \
              "directly. In the given example, the action opens a color dialog and action's title is set to the " \
              'selected color.'

entrypoint = 'app.ui'

launch_arguments = ['--nav-plugin-path', '~example']
