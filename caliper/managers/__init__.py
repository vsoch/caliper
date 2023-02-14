__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"


import re

from .conda import CondaManager
from .dataverse import DataverseManager
from .git import GitManager
from .github import GitHubManager
from .pypi import PypiManager

assert GitManager


def get_named_manager(name, uri=None, config=None):
    """get a named manager"""
    manager = None
    if re.search("^pypi", name, re.IGNORECASE):
        manager = PypiManager(uri)
    elif re.search("^conda", name, re.IGNORECASE):
        manager = CondaManager(uri)
    elif re.search("^github", name, re.IGNORECASE):
        manager = GitHubManager(uri)
    elif re.search("^dataverse", name, re.IGNORECASE):
        manager = DataverseManager(uri)
    if not manager:
        raise NotImplementedError(f"There is no matching manager for {name}")

    return manager
