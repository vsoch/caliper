__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"


from .git import GitManager
from .github import GitHubManager
from .pypi import PypiManager
import re

assert GitManager


def get_named_manager(name, uri=None, config=None):
    """get a named manager"""
    manager = None
    if re.search("pypi", name, re.IGNORECASE):
        manager = PypiManager(uri)
    if re.search("github", name, re.IGNORECASE):
        manager = GitHubManager(uri)

    if not manager:
        raise NotImplementedError(f"There is no matching manager for {name}")

    return manager
