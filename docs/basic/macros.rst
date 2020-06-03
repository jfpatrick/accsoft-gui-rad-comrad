Macros
======

Macros allows creating variables for nested UIs, which are substituted with real values at runtime. It works for
both \*.ui files and Python files.

Macro system is available for things like :ref:`cembeddeddisplay`,
:ref:`ctemplaterepeater`, :ref:`crelateddisplaybutton`,
:ref:`cvalueaggregator` and :doc:`transform`.

**Page contents:**

- `Inserting macro variables`_
- `Replacing macro variables`_
- `Macros in Python-based displays`_
- `Macros behavior at runtime`_


Inserting macro variables
-------------------------

Anywhere in an included \*.ui or Python file, you can insert a macro of the following form: ``${variable}``. Using
ComRAD Designer, you can only insert variables in string properties.



Replacing macro variables
-------------------------

Widgets designed to work with the macros system usually contain a ``macros`` property, where you define macro
substitutions in a JSON-format, for instance:

.. code-block:: json

   {"variable": "value_eg_device_name", "another_variable": "another_value"}


When launching an application, you can specify values for each variable using the ``-m`` flag of the command
line interface:

.. code-block:: bash

   comrad run \
     -m 'variable1=value, variable2=another_value' \
     /path/to/my/app.ui


Macros in Python-based displays
-------------------------------

If you open a python file and specify macros (via the command line, related display button, or embedded display widget),
the macros will be passed as a dictionary to the :meth:`~comrad.CDisplay.__init__` method of the
:ref:`cdisplay` subclass, where they can be accessed and used to generate the display.

In addition, if the :ref:`cdisplay` subclass specifies a \*.ui file to generate its user interface from
(see :doc:`mix`), macro substitution will occur inside the \*.ui file.


Macros behavior at runtime
--------------------------

ComRAD will remember the macros used to launch a display, and re-use them when navigating with the "Forward", "Back",
and "Home" buttons. Macros defined for the current window are also propagated whenever a new display is opened.
