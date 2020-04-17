.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>

Widget rules
============

Most of ComRAD widgets have a capability to define "rules". Rules system lets you modify common widget properties,
such as opacity or visibility based on the incoming channel value. One common use-case for widget rules is applying
custom colors to the labels.

- `Overview`_

  * `Numeric Range Rules`_

- `Setting rules in ComRAD Designer`_
- `Setting rules in code`_


Overview
--------

Rule is a special construct that can be executed whenever a new value arrives from the channel. It acts on a single
property of the widget (e.g. *Opacity*, *Visibility*, *Enabled* or *Color* in some cases) and can set this property
to a value that depends on the channel value. Rules can have different, however at this time only one type is
implemented - `Numeric Range Rules`_. Rules get evaluated in a separate thread to not block the UI on heavy
calculations. Recalculation is triggered every 33ms.

Numeric Range Rules
^^^^^^^^^^^^^^^^^^^

This kind of rules compare whether the incoming channel value falls into a defined numeric range and can set the
property to a predefined value, corresponding to the range.

For instance, you can define a rule that works with the :ref:`CLabel <clabel>` receiving a `float`, to adjust its
color:

- Values 0.5-1.0 → :green:`Green`
- Values 0.0-0.5 → :red:`Red`

All the values outside of these ranges will fallback to the default text color of the :ref:`CLabel <clabel>`, which
can also be altered via custom :ref:`stylesheets <intro:Using alternative color schemes>`.

The result will be visible at runtime:

.. table::

   =======  =======
   |red|    |green|
   =======  =======

.. |red| image:: ../img/rule_red.png
.. |green| image:: ../img/rule_green.png


Setting rules in ComRAD Designer
--------------------------------

To edit rules of a widget, right click on the widget in ComRAD Designer to bring up its context menu. Then select
"Edit Rules..." menu. This will open a rules dialog. Start by creating anew rules, and the configure it.

.. figure:: ../img/rule_editor.png
   :align: center
   :alt: Rules editor

   Rules editor

If you leave "Use default channel" checkbox marked, it will use the standard channel of the widget to evaluate the
rules (e.g. the one defined through channel property of :ref:`CLabel <clabel>`). Alternatively, you can unmark the
checkbox and enter any arbitrary channel address.

For `Numeric Range Rules`_, the evaluation UI consists of

- "Declarative view", where you can define the ranges using "+", "-" buttons
- "Source view", which gives you representation of ranges in JSON format. This is helpful, when you want to duplicate
  the ranges between the widgets, simply copy it from one "Source view" and paste into another one.

Setting rules in code
---------------------

In code, you assign rules on the rules property of the widget. Here, you should use special rule classes to construct
the rule definition, e.g.:

.. code-block:: python
   :linenos:

   from comrad import CLabel
   from comrad.rules import CNumRangeRule
   ...
   my_label = CLabel()
   my_label.rules = [
       CNumRangeRule(name='My rule',
                     prop=CNumRangeRule.Property.COLOR,
                     ranges=[
                         CNumRangeRule.Range(min_val=0.0, max_val=0.5, prop_val='#FF0000'),
                         CNumRangeRule.Range(min_val=0.5, max_val=1.0, prop_val='#00FF00'),
                     ]),
   ]
   ...