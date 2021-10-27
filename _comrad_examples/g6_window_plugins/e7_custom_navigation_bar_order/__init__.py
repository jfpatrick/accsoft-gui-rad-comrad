title = 'Custom navigation bar order'
description = 'When you create custom navigation bar plugins, you may decide to position them in place of ' \
              'standard navigation buttons. Custom ordering allows you to rearrange existing and new toolbar items, ' \
              'as well as hide standard buttons.<br/>' \
              '<br/>' \
              'The following example removes "Back" and "Forward" buttons and ' \
              'places a new plugin on the left of the "Home" button. To manipulate the existing items, they have ' \
              'predefined identifiers:' \
              '<ul>' \
              '<li>"comrad.sep" for navigation bar separator</li>' \
              '<li>"comrad.back" for "Back" button</li>' \
              '<li>"comrad.fwd" for "Forward" button</li>' \
              '<li>"comrad.home" for "Home" button</li>' \
              '<li>"comrad.spacer" for flexible spacer to fill in the empty space in between, similarly to ' \
              '<code>QSpacerItem</code></li>' \
              '</ul>'

entrypoint = 'app.ui'

launch_arguments = [
    '--nav-plugin-path', '~example',
    '--nav-bar-order', 'com.example.demo', 'comrad.sep', 'comrad.home',
]
