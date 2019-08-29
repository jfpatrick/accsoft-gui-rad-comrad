title = 'CLabel example integrating Python code generated from Qt Designer file using composition'
description = 'This example is very similar to the "Generated Ui Code", with an exception that it takes approach of ' \
              'composition over multiple inheritance. Multiple inheritance can be hard and confusing at times, so ' \
              'it is possible to use the generated UI via composition, with only difference, that all your widgets ' \
              'will be scoped inside a variable. While the above example accesses the label by "self.label", this ' \
              'example has an additional scope variable and access is done by "self.ui.label".'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'