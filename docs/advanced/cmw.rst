Configuring CMW
===============

For situations where you want to run the application outside of production environment, you can configure ComRAD
via single CLI flag to refer to an alternative environment, e.g. instead of ``PRO``, connect to ``TEST``, ``INT``,
``DEV`` or their mirrors - ``TEST2``, ``INT2``, etc.

.. code-block:: bash

   comrad run \
     --cmw-env TEST
     /path/to/my/app.ui

This single umbrella flag configures underlying JVM, Java libraries and PyCCDA handler to:

- Use respective directory service
- Use respective RBAC service
- Use respective CCDA endpoint (CCDB instance)

Te environments with suffix ``2`` use the same JVM variables, but connect to alternative CCDA endpoints.

If you need more finegrained control or different variable values, you can :doc:`inject JVM property directly <jvm>`.
