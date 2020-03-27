title = 'Basic macros example'
description = 'This example shows how to use macros when referencing external files or code. It can be applied to ' \
              'all widgets that work with external files: CRelatedDisplayButton, CEmbeddedDisplay, CTemplateRepeater' \
              ' . It can be also used in conjunction with Python snippets representing client-side logic. In this ' \
              'example we define an embedded display with an inner display, that has a wildcard variable replaced ' \
              'by a macro. We also create template repeater which does not have explicit "macros" property but ' \
              'collects them and processes from the "dataSource" file. Referenced template will have a label that ' \
              'uses a macro in 2 ways: connect to a device dynamically, and run a client-side transformation using ' \
              'information from a macro.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
