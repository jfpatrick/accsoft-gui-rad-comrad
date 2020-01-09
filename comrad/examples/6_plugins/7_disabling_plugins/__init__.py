title = 'Disabling plugins'
description = 'While many plugins can be defined in the same path, or even a file, not every application needs all ' \
              'of them activated. Therefore, you can specify which plugins need to appear in the application. Every ' \
              'plugin can be enabled or disabled by default, and this flag gets overridden by the command line ' \
              'argument from the user. This way, you can pick only useful plugins for you, and disable plugins ' \
              'shipped with ComRAD by default.'

entrypoint = 'app.ui'

launch_arguments = [
    '--nav-plugin-path', '~example',
    '--status-plugin-path', '~example',
    '--menu-plugin-path', '~example',
    '--disable-plugins', 'com.example.new-submenu,com.example.existing-menu,com.example.existing-submenu,com.example.status-temp',
    '--enable-plugins', 'com.example.disabled',
]
