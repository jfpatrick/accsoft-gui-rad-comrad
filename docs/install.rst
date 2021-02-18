Installation
============

- `Prerequisites`_
- `Install`_

  * `Using "pip" from Acc-Py package index (preferred)`_
  * `Using "pip" from Gitlab repository`_
  * `Using "pip" from source`_
  * `Installing outside of "Accelerating Python" environment`_

- `Setup auto-completion (optional)`_


Prerequisites
-------------

.. note:: All operations should be performed in a terminal, running "bash". While alternative shells, such as "zsh"
          or "fish", may work, stability is not guaranteed.

Make sure that you have `Acc-Py Base activated <https://wikis.cern.ch/display/ACCPY/Acc-Py+base>`__ for new
installations (preferred) or
`PyQt activated <https://wikis.cern.ch/display/ACCPY/PyQt+distribution>`__ for legacy installations,
so you have a proper "pip" version and access to Acc-Py Python package index.


Install
-------


Using "pip" from Acc-Py package index (preferred)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install comrad


Using "pip" from Gitlab repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install git+https://gitlab.cern.ch/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad.git

Or if you need specific branch

.. code-block:: bash

   pip install git+https://gitlab.cern.ch/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad.git@branch-name


Using "pip" from source
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone https://gitlab.cern.ch/acc-co/accsoft/gui/rad/accsoft-gui-rad-comrad.git
   cd accsoft-gui-rad-comrad
   pip install .


Installing outside of "Accelerating Python" environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All of the above commands are true without "Accelerating Python" environment, however you need to make
sure that packages can be installed correctly.

1. Make sure you have an updated version of "pip" (standard CC7 pip3 v9.* does not handle installs from git):

   .. code-block:: bash

      python -m pip install -U pip

2. Ensure that you have access to Acc-Py Nexus repository, as described in
   `Python package index / repository <https://wikis.cern.ch/pages/viewpage.action?pageId=145493385>`__.


.. note:: When using ComRAD outside of "Accelerating Python" environment, you will not have
          "ComRAD Designer" mode, and will only be able to work with standard Qt Designer.


Setup auto-completion (optional)
--------------------------------

ComRAD takes advantage of `argcomplete <https://github.com/kislyuk/argcomplete>`__ - an auto-completion assistant.
To have auto-completion enabled for ``comrad`` commands, you need to activate it.

#. If you are using virtual environments, `argcomplete <https://github.com/kislyuk/argcomplete>`__ will be installed
   as part of ComRAD dependencies. Now you need to enable auto-completion that is specific to your virtual environment.
   One of the ways to achieve it is by augmenting virtual environment's ``activate`` script:

   .. code-block:: bash

      echo 'eval "$(register-python-argcomplete comrad)"' >> /path/to/venv/bin/activate

#. If you are **not** using virtual environments and have installed ComRAD globally (not advised), you can use global
   activation - in this case the auto-completion will be available in every terminal session
   (`More info <https://github.com/kislyuk/argcomplete#activating-global-completion>`__):

   .. code-block:: bash

      activate-global-python-argcomplete

   Such activation can be added to your ``~/.bashrc`` script to be executed for every terminal session.