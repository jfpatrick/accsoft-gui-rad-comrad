title = 'CLabel example integrating Python code generated from Qt Designer file using composition'
description = 'This example is very similar to <strong>2.3. Generated Ui Code</strong>, with an exception that it ' \
              'takes the approach of composition over multiple inheritance. Multiple inheritance can be hard and ' \
              'confusing at times, so it is possible to use the generated UI via composition, with only difference, ' \
              'that all your widgets will be scoped inside a variable. While the former example accesses the label ' \
              'by <code>self.label</code>, this example has an additional scope variable and access is done as ' \
              '<code>self.ui.label</code>.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
