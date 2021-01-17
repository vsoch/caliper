__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
from git import Repo
from caliper.utils.command import run_command
from caliper.logger import logger


class GitManager:
    """Interact with a Git repository. This mananger is not intended to extract
    versions (e.g., self.specs) so it does not subclass ManagerBase.
    """

    def __init__(self, folder=None, quiet=False):
        """initialize a git manager. The folder can be empty if intending to
        init a new repository, or not existing if a clone is intended.
        """
        self.folder = folder or ""
        self.quiet = quiet
        self.repo = None
        self._update_repo(self.folder)

    def _update_repo(self, dest):
        self.git_dir = os.path.join(dest, ".git")
        if os.path.exists(self.git_dir):
            self.repo = Repo(self.git_dir)

    def add(self, filename=".", dest=None):
        """Add a file to the git repository"""
        dest = dest or self.folder or ""
        return self.run_command(self.init_cmd(dest) + ["add", filename])

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

    def status(self, dest=None):
        """Add a file to the git repository"""
        dest = dest or self.folder or ""
        return self.run_command(self.init_cmd(dest) + ["status"])

    def clone(self, repo, dest=None):
        """Given a repository, clone it with run_command"""

        # Destination folder can default to present working directory
        dest = dest or self.folder or ""
        self.run_command(["git", "clone", "--depth", "1", repo, dest])
        return dest

    def init(self, dest=None):
        """init an empty repository in a directory of choice"""
        dest = dest or self.folder or ""
        self.run_command(["git", "init", dest])
        self._update_repo(dest)
        self.config("user.name", "vsoch-caliper", dest)
        self.config("user.email", "vsoch-caliper@users.noreply.github.com", dest)
        return dest

    def config(self, key, value, dest=None):
        self.run_command(self.init_cmd(dest) + ["config", key, value])

    def checkout(self, commit, dest=None):
        self.run_command(self.init_cmd(dest) + ["checkout", commit])

    def ls_files(self, dest=None):
        """init an empty repository in a directory of choice"""
        dest = dest or self.folder or ""
        files = self.run_command(self.init_cmd(dest) + ["ls-files"]) or []
        if files:
            return [x for x in files[0].split("\n") if x]
        return files

    def tag(self, tag, dest=None):
        """Create a tag for a particular commit"""
        dest = dest or self.folder or ""
        return self.run_command(self.init_cmd(dest) + ["tag", tag])

    @property
    def tags(self):
        """A wrapper to expose git.repo.tags"""
        return getattr(self.repo, "tags", [])

    def init_cmd(self, dest):
        """Given a git directory, initialize a command that sets the git-dir
        and working tree
        """
        dest = dest or "."
        git_dir = os.path.join(dest, ".git")
        return [
            "git",
            "--git-dir=%s" % git_dir,
            "--work-tree=%s" % os.path.dirname(git_dir),
        ]

    def run_command(self, cmd):
        """A wrapper to run_command to handle errors"""
        logger.debug(" ".join(cmd))
        response = run_command(cmd, quiet=self.quiet)
        if not response["return_code"] == 0:
            logger.exit("Error with %s, %s" % (" ".join(cmd), response["lines"]))
        return response["lines"]
