.. _manual-main:

=======
Caliper
=======

.. image:: https://img.shields.io/github/stars/vsoch/caliper?style=social
    :alt: GitHub stars
    :target: https://github.com/vsoch/caliper/stargazers


Caliper is a tool for measuring and assessing change in packages. To see the code, 
head over to the `repository <https://github.com/vsoch/caliper/>`_

.. _main-getting-started:

----------------------------
Getting started with Caliper
----------------------------

Caliper can be installed from pypi or directly from the repository. See :ref:`getting_started-installation` for
installation, and then the :ref:`getting-started` section for using caliper.

.. _main-support:

-------
Support
-------

* For **bugs and feature requests**, please use the `issue tracker <https://github.com/vsoch/caliper/issues>`_.
* For **contributions**, visit Caliper on `Github <https://github.com/vsoch/caliper>`_.

---------
Resources
---------

`Caliper Analysis <https://github.com/vsoch/caliper-analysis>`_
    An example analysis of tensorflow using Caliper.

`Caliper Metrics <https://github.com/vsoch/caliper-metrics>`_
    A small flat file (json) database of metrics extracted for pypi and GitHub packages

.. toctree::
   :caption: Getting started
   :name: getting_started
   :hidden:
   :maxdepth: 2

   getting_started/index

.. toctree::
    :caption: API Reference
    :name: api-reference
    :hidden:
    :maxdepth: 1

    api_reference/caliper
    api_reference/internal/modules
