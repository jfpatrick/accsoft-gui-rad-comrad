
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
