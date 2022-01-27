title = 'Logbook screenshot plugin'
description = 'This example shows how to activate and configure the bundled e-logbook plugin to enable uploading ' \
              'application screenshots.<br/>' \
              '<br/>' \
              'We are going to enable "comrad.screenshot" plugin, which is bundled but disabled by default. ' \
              'It is mandatory to provide specific activity(-ies) "comrad.screenshot.activities" in order for ' \
              'the plugin to work. The activity corresponds to the logbook title in the e-logbook system. It is ' \
              'also possible to use optional "comrad.screenshot.server" value, which can be either ' \
              '"PRO" or "TEST". Finally, the user could enforce window decorations to be included in the screenshot ' \
              'by specifying "comrad.screenshot.decor=1".'

entrypoint = 'app.ui'

launch_arguments = [
    '--enable-plugins', 'comrad.screenshot', 'comrad.rbac',
    '--window-plugin-config', 'comrad.screenshot.activities="LOGBOOK_TESTS_Long_Name Testing"', 'comrad.screenshot.server=TEST',
]
