__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
from caliper.utils.command import run_command
from caliper.logger import logger


class GitManager:
    """Interact with a Git repository. This mananger is not intended to extract
    versions (e.g., self.specs) so it does not subclass ManagerBase.
    """

    name = "git"

    def __init__(self, folder=None):
        """initialize a git manager. The folder can be empty if intending to
        init a new repository, or not existing if a clone is intended.
        """
        self.folder = folder or ""

    def clone(self, repo, dest=None):
        """Given a repository, clone it with run_command"""

        # Destination folder can default to present working directory
        dest = dest or self.folder or ""
        self.run_command(["git", "clone", repo, dest])
        return dest

    def init(self, dest=None):
        """init an empty repository in a directory of choice"""
        dest = dest or self.folder or ""
        self.run_command(["git", "init", dest])
        return dest

    def commit(self, message, dest=None):
        """commit to a particular directory"""
        dest = dest or self.folder or ""
        return self.run_command(
            self.init_cmd(dest)
            + [
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-a",
                "-m",
                message,
                "--allow-empty",
            ]
        )

    def add(self, content=None, dest=None):
        """add files/folders to a git repository"""
        dest = dest or self.folder or ""
        content = content or "."
        return self.run_command(self.init_cmd(dest) + ["add", content])

    def tag(self, tag, dest=None):
        """Create a tag for a particular commit"""
        dest = dest or self.folder or ""
        return self.run_command(self.init_cmd(dest) + ["tag", tag])

    def status(self, dest=None):
        """Get status for a repository"""
        dest = dest or self.folder or ""
        return self.run_command(self.init_cmd(dest) + ["status"])

    def init_cmd(self, dest):
        """Given a git directory, initialize a command that sets the git-dir
        and working tree
        """
        git_dir = os.path.join(dest, ".git")
        return [
            "git",
            "--git-dir=%s" % git_dir,
            "--work-tree=%s" % os.path.dirname(git_dir),
        ]

    def run_command(self, cmd):
        """A wrapper to run_command to handle errors"""
        logger.debug(" ".join(cmd))
        response = run_command(cmd)
        if not response["return_code"] == 0:
            logger.exit("Error with %s, %s" % (" ".join(cmd), response["lines"]))
        return response["lines"]
