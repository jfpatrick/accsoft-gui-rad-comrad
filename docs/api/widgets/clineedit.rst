.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>


.. _clineedit:


CLineEdit
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

.. image:: ../../img/widget_clineedit.png

:class:`~comrad.CLineEdit` is a single-line string editor that allows propagating a string or numeric value into
the control system. The changes are submitted when the user presses “Enter”.

You can connect it to the control system by setting its :attr:`~comrad.CLineEdit.channel` value to the address of
your device-property's field.

.. seealso:: :ref:`What is a channel? <basic/controls:Channels>`

:class:`~comrad.CLineEdit` is capable of representing numeric values in different notations, controlled by
:attr:`~comrad.CLineEdit.displayFormat`, such as decimal, exponential, binary, and hexadecimal. For decimal values it is
also important to note the :attr:`~comrad.CLineEdit.precision` property that limits the amount of digits after decimal
point. Note that by default it's set to 0, thus hiding fractional part of the number. :class:`~comrad.CLineEdit` even
can work with numeric arrays that are displayed in format ``[1.2 3.4 22.214]``.

:class:`~comrad.CLineEdit` supports client-side data transformations via
:attr:`~comrad.CLineEdit.valueTransformation` that lets you modify displayed value with a piece of Python code.

.. seealso:: :doc:`What is client-side data transformations? <../../basic/transform>`

:class:`~comrad.CLineEdit` can be assigned custom background color via widget rules. In this case, font color is
switched to either black or white to provide best contrast based on background color's brightness (HSV value component).

.. seealso:: :doc:`What is widget rules? <../../basic/rules>`

Supported data types
^^^^^^^^^^^^^^^^^^^^

============  ============  ============  ============  ============  ============  ============  ============  =========  ============  ============  ============  ============  ============  ===========  ============  ============  ============  ============  =============  =============  ==============
short         int           long          float         double        string        boolean       enum          enumSet    shortArray    intArray      longArray     floatArray    doubleArray   stringArray  booleanArray  intArray2D    longArray2D   floatArray2D  doubleArray2D  stringArray2D  booleanArray2D
------------  ------------  ------------  ------------  ------------  ------------  ------------  ------------  ---------  ------------  ------------  ------------  ------------  ------------  -----------  ------------  ------------  ------------  ------------  -------------  -------------  --------------
:green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :red:`No`     :red:`No`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :red:`No`    :red:`No`     :red:`No`     :red:`No`     :red:`No`     :red:`No`      :red:`No`      :red:`No`
============  ============  ============  ============  ============  ============  ============  ============  =========  ============  ============  ============  ============  ============  ===========  ============  ============  ============  ============  =============  =============  ==============


Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CLineEdit
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QLineEdit


API reference
-------------

.. autoclass:: comrad.CLineEdit
   :members:
   :inherited-members:
