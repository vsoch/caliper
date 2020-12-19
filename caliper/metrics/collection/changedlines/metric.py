__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import ChangeMetricBase
import os

import git as gitpython

DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
EMPTY_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class Changedlines(ChangeMetricBase):

    name = "changedlines"
    description = "count lines added and removed between versions"

    def __init__(self):
        self._data = {}

    @property
    def rawdata(self):
        return self._data

    def extract(self, git):
        """given a file before and after, count the number of changed lines"""
        repo = gitpython.Repo(git.folder)
        for tag in repo.tags:
            parent = tag.commit.parents[0] if tag.commit.parents else EMPTY_SHA

            # Derive the diff name
            tag2 = "EMPTY" if isinstance(parent, str) else parent.message.strip()
            index = "%s..%s" % (tag2, tag)

            # A ChangeMetric stores tag diffs
            self._data[index] = self._extract(git, tag.commit, parent)

    def _extract(self, git, commit1, commit2):
        """The second commit should be the parent"""
        diffs = {diff.a_path: diff for diff in commit1.diff(commit2)}
        data = []

        # The stats on the commit is a summary of all the changes for this
        # commit, we'll iterate through it to get the information we need.
        for filepath, stats in commit1.stats.files.items():

            # Select the diff for the path in the stats
            diff = diffs.get(filepath)

            # Was the path renamed?
            if not diff:
                for diff in diffs.values():
                    if diff.b_path == git.folder and diff.renamed:
                        break

            # Update the stats with the additional information
            stats.update(
                {
                    "object": os.path.join(git.folder, filepath),
                    "commit": commit1.hexsha,
                    "author": commit1.author.email,
                    "timestamp": commit1.authored_datetime.strftime(DATE_TIME_FORMAT),
                    "size": diff_size(diff),
                }
            )
            if stats:
                data.append(stats)

        return data

    def get_file_results(self):
        """return a lookup of changes, where each change has a list of files"""
        return self._data

    def get_summed_results(self):
        """Get summed values (e.g., lines changed) across files"""
        results = {}
        summary_keys = ["size", "insertions", "deletions", "lines"]
        for index, items in self._data.items():
            results[index] = dict((x, 0) for x in summary_keys)
            for item in items:
                for key in summary_keys:
                    results[index][key] += item.get(key, 0)
        return results


def diff_size(diff):
    """Calculate the size of the diff by comparing blob size
    Computes the size of the diff by comparing the size of the blobs.
    """
    # New file
    if not diff.a_blob and diff.new_file:
        return diff.b_blob.size

    # Deletion (should be negative)
    if not diff.b_blob and diff.deleted_file:
        return -1 * diff.a_blob.size

    return diff.a_blob.size - diff.b_blob.size
