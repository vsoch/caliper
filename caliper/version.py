__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"

__version__ = "0.1.0"
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
    ("rich", {"min_version": None}),
)
PARSER_REQUIRES = (
    ("jedi", {"exact_version": "0.18.0"}),
    ("gast", {"min_version": None}),
    ("beniget", {"min_version": None}),
)
TESTS_REQUIRES = (("pytest", {"min_version": "4.6.2"}),)
DATAVERSE_REQUIRES = (("pyDataverse", {"exact_version": "0.2.1"}),)

ALL_REQUIRES = INSTALL_REQUIRES + PARSER_REQUIRES + DATAVERSE_REQUIRES
