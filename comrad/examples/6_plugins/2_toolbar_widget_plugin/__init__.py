title = 'Toolbar widget plugin'
description = 'Toolbar widget plugin lets you embed a custom widget inside a toolbar, as opposed to having a ' \
              'standard toolbar buttons produced by action plugins. Widget plugins do not have action associated and ' \
              'will not appear in the "Plugins" menu. In fact, it does not necessarily need to have any triggers, as ' \
              'it can be display-only widget.'

entrypoint = 'app.ui'

launch_arguments = ['--nav-plugin-path', '~example']
