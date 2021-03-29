Configuring JVM
===============

Whenever you use custom Java-based libraries and require specific JVM setup for them to work properly, or you
just simply want existing Java libraries to work differently, by flipping flags, you can access underlying JVM
configuration, by passing flags to the ComRAD CLI.

.. code-block:: bash

   comrad run \
     --java-env my.java.env.Name=value \
                my.java.another.Env=value2 \
     /path/to/my/app.ui

.. note:: Take caution when using this low-level feature, as you may override some standard flags that ComRAD
          relies on. For instance, to configure authentication or directory service, consider reading :doc:`cmw`.

.. note:: You should not set RBAC-related configuration via JVM flags. Instead, environment variables are recommended.
          This approach ensures consistency between different implementations of RBAC, residing inside Java and Python
          libraries. Environment variable names correspond to JVM flag names, where dots are replaced with underscores
          and letters are capitalized, e.g. JVM flag ``rbac.env=DEV`` should be set via

          .. code-block:: bash

             export RBAC_ENV=DEV

.. note:: These flags are passed into `PyJAPC <https://acc-py.web.cern.ch/gitlab/scripting-tools/pyjapc/docs/stable/>`__
   and underlying `cmmnbuild_dep_manager` (Currently these are the only Java-based items that ComRAD depends on). It
   means that if your application does not contain any channels that would resolve to PyJAPC data handler, PyJAPC
   will never be instantiated, and flags will not be used.