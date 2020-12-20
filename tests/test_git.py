__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import sys
import pytest


def test_git_manager_new(tmp_path):
    """test git manager"""
    print("Testing Git Manager")
    from caliper.managers import GitManager

    git_dir = os.path.join(str(tmp_path), "git-dir")

    # Create empty respository
    git = GitManager(git_dir)
    git.init()

    # Add some content
    content_file = os.path.join(git_dir, "file.txt")
    with open(content_file, "w") as fd:
        fd.writelines("pancakes!")
    git.add("file.txt")

    # Check status, commit, and tag
    git.status()
    git.commit("Adding content!")
    git.tag("content-tag")

    # Now test starting with empty existing repository
    git = GitManager()
    git.init(git_dir)
    git.status(git_dir)
