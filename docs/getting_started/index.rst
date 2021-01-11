.. _getting-started:

===============
Getting Started
===============

Caliper is a tool for measuring and assessing change in packages. This means
that we can extract metrics across releases of packages, and then test any number
of scripts against those releases. Caliper can help you to answer questions like:

- **How informative is a semantic version change?** For example, we could measure changes in code (lines, imports, etc.) between different releases, and we would expect major version changes to be larger than minor.
- **When will it break?** If we have a scientific script without a requirements.txt file (for Python) we can test running it across versions of a major dependency to assess which will work.
- **How correct are the versions we specify?** If we are creating entire solvers around trying to resolve a list of dependency versions, it better be the case that our specifications are accurate! By comparing changes between versions and then measuring when a script breaks, we can better understand how flexible these versions really are.

If you have any questions or issues, please `let us know <https://github.com/vsoch/caliper/issues>`_

.. toctree::
   :maxdepth: 2

   installation
   user-guide
   use-cases
