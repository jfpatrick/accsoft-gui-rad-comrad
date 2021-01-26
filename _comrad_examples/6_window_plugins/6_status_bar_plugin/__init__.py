title = 'Status bar plugin'
description = 'Status bar plugins allow you to place custom widgets inside status bar. A status bar item can be ' \
              'permanent or not. A permanent plugin does not get overlapped by status messages. Status bar plugins ' \
              'can be configured via launch arguments in the same way as toolbar plugins. The following ' \
              'example creates two plugins: temporary and permanent, which are simple labels. To observe the ' \
              'difference, try to trigger a status message (e.g. "File"➔"Reload Display" menu will produce a ' \
              'temporary status message "Reloading <filename>", which will overlap and cover the temporary plugin, ' \
              'but will be hidden behind the permanent one.'

entrypoint = 'app.ui'

launch_arguments = ['--status-plugin-path', '~example']
