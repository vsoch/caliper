__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

__version__ = "0.0.18"
AUTHOR = "Vanessa Sochat"
AUTHOR_EMAIL = "vsochat@stanford.edu"
NAME = "caliper"
PACKAGE_URL = "https://github.com/vsoch/caliper"
KEYWORDS = "dependency and change analysis, dependencies"
DESCRIPTION = "Caliper is a tool for measuring and assessing change in packages."
LICENSE = "LICENSE"

################################################################################
# Global requirements


INSTALL_REQUIRES = (
    ("requests", {"min_version": "2.23.0"}),
    ("GitPython", {"min_version": "3.1.7"}),
    ("pyaml", {"min_version": "20.4.0"}),
    ("Jinja2", {"min_version": "2.11.2"}),
)
TESTS_REQUIRES = (("pytest", {"min_version": "4.6.2"}),)


ALL_REQUIRES = INSTALL_REQUIRES
