.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>

.. _cled:




CLed
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

.. image:: ../../img/widget_cled.png

:class:`~comrad.CLed` displays a single LED useful for representing binary values or other color-coded values. It is a
non-interactive (read-only) widget.

You can display a value from the control system inside :class:`~comrad.CLed` by setting its :attr:`~comrad.CLed.channel`
value to the address of your device-property's field.

.. seealso:: :ref:`What is a channel? <basic/controls:Channels>`

:class:`~comrad.CLed` is meant to work with booleans, integers and enums. When used with boolean, it will acquire one
of two colors, corresponding to its :attr:`~comrad.CLed.onColor` and :attr:`~comrad.CLed.offColor`. Integer will be
converted to :class:`Led.Status <accwidgets.led.led.Led.Status>`. When fed an enum, it will convert its
"meaning" field, into corresponding :class:`Led.Status <accwidgets.led.led.Led.Status>` value.

When reflecting a :class:`Led.Status <accwidgets.led.led.Led.Status>`, the widget will
receive a predefined color. However, it is capable of representing an arbitrary color (such as those defined in
:attr:`~comrad.CLed.onColor` and :attr:`~comrad.CLed.offColor` or returned from :attr:`~comrad.CLed.valueTransformation`
or rules).

:class:`~comrad.CLed` supports client-side data transformations via :attr:`~comrad.CLed.valueTransformation` that lets
you modify displayed value with a piece of Python code.

.. seealso:: :doc:`What is client-side data transformations? <../../basic/transform>`

:class:`~comrad.CLed` can be assigned custom color via widget rules.

.. seealso:: :doc:`What is widget rules? <../../basic/rules>`

Supported data types
^^^^^^^^^^^^^^^^^^^^

============  ============  ============  =========  =========  =========  ============  ============  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ============  ============  ============  =============  =============  ==============
short         int           long          float      double     string     boolean       enum          enumSet    shortArray  intArray   longArray  floatArray  doubleArray  stringArray  booleanArray  intArray2D    longArray2D   floatArray2D  doubleArray2D  stringArray2D  booleanArray2D
------------  ------------  ------------  ---------  ---------  ---------  ------------  ------------  ---------  ----------  ---------  ---------  ----------  -----------  -----------  ------------  ------------  ------------  ------------  -------------  -------------  --------------
:green:`Yes`  :green:`Yes`  :green:`Yes`  :red:`No`  :red:`No`  :red:`No`  :green:`Yes`  :green:`Yes`  :red:`No`  :red:`No`   :red:`No`  :red:`No`  :red:`No`   :red:`No`    :red:`No`    :red:`No`     :red:`No`     :red:`No`     :red:`No`     :red:`No`      :red:`No`      :red:`No`
============  ============  ============  =========  =========  =========  ============  ============  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ============  ============  ============  =============  =============  ==============


Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CLed
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QWidget


API reference
-------------

.. autoclass:: comrad.CLed
    :members:
    :inherited-members: