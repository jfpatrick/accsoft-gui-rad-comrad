.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>

.. _cdisplay:


CDisplay
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

:class:`~comrad.CDisplay` is a simple :class:`QWidget` subclass that is meant to be an entry point for shared UI
panels. Thus, you never place it like other widgets inside ComRAD Designer. Instead, your top-level Designer
panels become :class:`~comrad.CDisplay` instances implicitly, when they are loaded. In case when you are using
Python files for your child display definitions, you have to subclass :class:`~comrad.CDisplay`.

.. seealso:: Read more about subclassing in :doc:`../../basic/mix` and :doc:`../../basic/codecentric`.

When the instance of your child display is meant to come along with the Designer file (\*.ui), you have to override
:meth:`~comrad.CDisplay.ui_filename` method. For Python-only displays, leave it unmodified.

.. include:: ../../shared/cdisplay_args.rst

.. include:: ../../shared/cdisplay_macros.rst

Supported data types
^^^^^^^^^^^^^^^^^^^^

.. note:: This widget does not connect to the control system.

Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CDisplay
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QWidget


API reference
-------------

.. autoclass:: comrad.CDisplay
    :members:
    :inherited-members:
    :undoc-members: