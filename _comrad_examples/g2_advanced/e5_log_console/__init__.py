title = 'Basic CLogConsole example'
description = "<code>CLogConsole</code> is a special widget that is capable of intercepting messages from Python's " \
              '<a href="https://docs.python.org/3/library/logging.html?highlight=logging#logging.Logger"><code>' \
              'logging.Logger</code></a> classes and present them to the user. Including this into your application, ' \
              'will allow to monitor all the warnings produced on any level of your application, as long as ' \
              '<a href="https://docs.python.org/3/library/logging.html?highlight=logging#logging.Logger"><code>' \
              'logging.Logger</code></a> is involved and you configure a correct root logger. This example will have ' \
              'messages being posted repeatedly that should be displayed in the widget.<br/>' \
              '<br/>' \
              'By default, <i>Log Console</i> is available in every ComRAD application and is usually visible right ' \
              'away. To make ComRAD examples easier to comprehend, <i>Log Console</i> is hidden in all examples. ' \
              'You still can bring it up via menu "View"➔"Show Log Console". In user applications, this can be ' \
              'controlled by <code>--hide-log-console</code> command line argument.'

entrypoint = 'app.py'
