__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import ChangeMetricBase
import os


class Changedlines(ChangeMetricBase):

    name = "changedlines"
    description = "count lines added and removed between versions"

    def _extract(self, commit1, commit2):
        """The second commit should be the parent"""

        diffs = {diff.a_path: diff for diff in commit1.diff(commit2)}
        data = []

        # commit, we'll iterate through it to get the information we need.
        for filepath, metrics in commit1.stats.files.items():

            # Select the diff for the path in the stats
            diff = diffs.get(filepath)

            # Was the path renamed?
            if not diff:
                for diff in diffs.values():
                    if diff.b_path == self.git.folder and diff.renamed:
                        break

            # Update the stats with the additional information
            metrics.update(
                {
                    "object": os.path.join(self.git.folder, filepath),
                    "commit": commit1.hexsha,
                    "author": commit1.author.email,
                    "timestamp": commit1.authored_datetime.strftime(
                        self.date_time_format
                    ),
                }
            )
            if metrics:
                data.append(metrics)

        return data

    def get_file_results(self):
        """return a lookup of changes, where each change has a list of files"""
        return self._data

    def get_summed_results(self):
        """Get summed values (e.g., lines changed) across files"""
        results = {}
        summary_keys = ["insertions", "deletions", "lines"]
        for index, items in self._data.items():
            results[index] = dict((x, 0) for x in summary_keys)
            for item in items:
                for key in summary_keys:
                    results[index][key] += item.get(key, 0)
        return results
