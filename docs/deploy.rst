Deployment
==========

Deploying ComRAD applications is done in a similar fashion to other PyQt applications.

.. warning:: Currently, the deployment is merely an educated guess, a suggestion, and may change in the future
             to be compatible with acc-py-deploy.

To deploy a ComRAD application on an operational machine, such as found in CCC, the application has to be
installed on NFS inside a dedicated virtual environment, e.g. ``/nfs/user/somegroup/comrad``.

Installation comprises of 3 steps:

#. `Creating and activating environment at the given path <https://wikis.cern.ch/display/ACCPY/PyQt+distribution#PyQtdistribution-WorkingwithVirtualEnvironments>`__
#. Installing ComRAD and its dependencies into the virtual environment
#. Copying ComRAD-based applications close to the virtual environment

Then, in CCM the following script can be created to launch an application:

.. code-block:: bash

   source /acc/local/share/python/acc-py/base/2020.11/setup.sh \
     && source /nfs/user/somegroup/comrad/bin/activate \
     && comrad run /path/to/my/app.ui

.. todo:: Create a sample video how it's done