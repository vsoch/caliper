.. _getting_started-installation:

============
Installation
============

Caliper can be installed from pypi, or from source. For either, it's
recommended that you create a virtual environment, if you have not already
done so.


Virtual Environment
===================

First, clone the repository code.

.. code:: console

    $ git clone git@github.com:vsoch/caliper.git
    $ cd caliper


Then you'll want to create a new virtual environment, and install dependencies.

.. code:: console

    $ python -m venv env
    $ source env/bin/activate
    $ pip install -r requirements.txt


And install Caliper (from the repository directly)

.. code:: console
 
    $ pip install -e .


Install via pip
===============

Caliper can also be installed with pip.

.. code:: console

    $ pip install caliper


Once it's installed, you should be able to inspect the client!


.. code:: console

    $ caliper --help
    usage: caliper [-h] [--version] [--quiet] [--verbose] [--log-disable-color] [--log-use-threads]
                   {version,metrics,analyze,extract,view} ...

    Caliper is a tool for measuring and assessing changes in packages.

    optional arguments:
      -h, --help            show this help message and exit
      --version             suppress additional output.

    actions:
      actions

      {version,metrics,analyze,extract,view}
                            actions
        version             show software version
        metrics             see metrics available
        analyze             analyze functionality of a package.
        extract             extract one or more metrics for a software package.
        view                extract a metric and view a plot.

    LOGGING:
      --quiet               suppress logging.
      --verbose             verbose output for logging.
      --log-disable-color   Disable color for caliper logging.
      --log-use-threads     Force threads rather than processes.
