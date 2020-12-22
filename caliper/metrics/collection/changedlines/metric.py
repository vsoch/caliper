__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.logger import logger
from caliper.utils.file import read_json
from caliper.metrics.base import ChangeMetricBase
import os


class Changedlines(ChangeMetricBase):

    name = "changedlines"
    description = "count lines added and removed between versions"

    def __init__(self, git):
        super().__init__(git=git, filename=__file__)

    def get_plot_data(self, result_file):
        """Given extracted data, return data to render into a template. This
        function should load data into self._data.
        """
        result_file = os.path.abspath(result_file)
        if not os.path.exists(result_file):
            logger.exit("%s does not exist" % result_file)

        # Derive the result type based on data keys
        self._data = read_json(result_file)
        filename = os.path.basename(result_file)
        if not self._data:
            logger.exit("Data file %s is empty." % filename)

        # We currently only plot insertions and deletions
        keys = list(list(self._data.values())[0].keys())
        for key in ["insertions", "deletions"]:
            if key not in keys:
                logger.exit("key %s is missing from %s." % (key, filename))

        # Prepare datasets, each of a different color, and title
        labels = self._derive_labels()
        insertion_dataset = [self._data[label]["insertions"] for label in labels]
        deletion_dataset = [self._data[label]["deletions"] for label in labels]
        datasets = [
            {"data": insertion_dataset, "title": "Insertions", "color": "turquoise"},
            {"data": deletion_dataset, "title": "Deletions", "color": "tomato"},
        ]

        return {
            "datasets": datasets,
            "title": "Insertions and Deletions",
            "labels": labels,
        }

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
