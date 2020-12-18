__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"


from .git import GitManager
from .pypi import PypiManager
import re


def matches(Manager, uri):
    """Given a unique resource identifier, determine if it matches a manager"""
    return not re.search(Manager.name, uri) == None


def get_manager(uri):
    """get a manager based on the name"""
    manager = None
    if matches(GitManager, uri):
        manager = GitManager(uri)
    elif matches(PypiManager, uri):
        manager = PypiManager(uri)

    if not manager:
        raise NotImplementedError(f"There is no matching manager for {uri}")
    return manager


def get_named_manager(name, uri=None, config=None):
    """get a named manager"""
    manager = None
    if re.search("pypi", name, re.IGNORECASE):
        manager = PypiManager()
    elif re.search("git", name, re.IGNORECASE):
        manager = GitManager(uri)

    if not manager:
        raise NotImplementedError(f"There is no matching manager for {name}")

    return manager
