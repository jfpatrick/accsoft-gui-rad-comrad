Code-centric development
========================

This section explains how to develop ComRAD applications using only Python, without any \*.ui files.
Here you will also find more details about :class:`~comrad.CDisplay` capabilities. Python files can be launched
similarly to \*.ui files:

.. code-block:: bash

   comrad run /path/to/my/app.py

- `Subclass CDisplay`_
- `Add widgets manually`_
- `Handing command line arguments`_
- `Handling macros`_
- `Building UI Dynamically`_



Subclass CDisplay
-----------------

Your Python application must define a single :class:`~comrad.CDisplay` sublcass. This is the panel that gets embedded
by ComRAD window and displayed to the user. :class:`~comrad.CDisplay` instances are PyQt widgets with a few extra
features on top. You can layout both ComRAD widgets as well as regular PyQt widgets in them. To get familiar with PyQt
widgets API, it is suggested to refer to official
`Qt Documentation <https://doc.qt.io/qt-5/qtwidgets-index.html>`__. While it is designed for C++, Python APIs
are often 1-to-1 reflections.

To start developing a Python-only ComRAD application, create a new Python file, say ``app.py`` and make a
:class:`~comrad.CDisplay` subclass there.

.. code-block:: python
   :linenos:

   from comrad import CDisplay

   class MyDisplay(CDisplay):
       pass

This display does not rely on a \*.ui file, and therefore does not need ``ui_filename`` method overridden.
You will add widgets manually in code, or :ref:`include them from generated code <basic/mix:Generating UI code>`.



Add widgets manually
--------------------

One of the ways of populating your display, is to manually add widgets in code, e.g. during display
initialization:

.. code-block:: python
   :linenos:

   from qtpy.QtWidgets import QVBoxLayout
   from comrad import CLabel, CDisplay

   class MyDisplay(CDisplay):

       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)

           layout = QVBoxLayout()
           self.setLayout(layout)

           label = CLabel()
           label.channel = 'myDevice/myProperty#myField'

           self.layout().addWidget(label)
           layout.addWidget(label)

Here, we add a :class:`~comrad.CLabel` and connect it to the control system by providing the channel address.




Handing command line arguments
------------------------------

Displays can accept command line arguments supplied at launch. Your display’s initializer has a
named argument called ``args``:

.. code-block:: python

   def __init__(self, parent: Optional[QWidget] = None, args: Optional[List[str]] = None, macros: Optional[Dict[str, str]] = None):

It is recommended to use Python’s :mod:`argparse` module to parse your arguments. For example, you could
write a method like this in your display:

.. code-block:: python
   :linenos:

   import argparse

   ...

   def parse_args(self, args: Optional[List[str]]):
       parser = argparse.ArgumentParser()
       parser.add_argument('--list', dest='magnet_list', help='File containing a list of magnet names to use.')
       parsed_args, _ = parser.parse_known_args(args)
       return parsed_args

Command line arguments can be a good way to make displays that generate themselves dynamically: you could
accept a filename argument, and read the contents of that file to add widgets to your display.



Handling macros
---------------

You can also use macros system as a way to get user data into your display. All macros are available as
a dictionary in the initializer via ``macros`` argument. In addition, macro substitution will always be
performed on the \*.ui file for your display.



Building UI Dynamically
-----------------------

A common reason to build a Python-based display is to generate UI dynamically, from some other source of
data, like a file or database. As mentioned above, you can read in command line arguments to help get data
into your display. Once you have a source of data, you can use PyQt to make new widgets, and add them to
your display. For example, if you get a list of devices from somewhere, you can make widgets for each
device, and add them to a layout:

.. code-block:: python
   :linenos:

   ...
   for dev in devices:
       device_label = CLabel(parent=self, init_channel=dev)
       self.layout.addWidget(device_label)
   ...
