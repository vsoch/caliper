__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricBase


class Totalcounts(MetricBase):

    name = "totalcounts"
    description = "retrieve total counts of files and lines for each commit"

    def _extract(self, commit):
        total_files = len(self.git.ls_files())
        return {
            "commit": commit.hexsha,
            "timestamp": commit.authored_datetime.strftime(self.date_time_format),
            "files": total_files,
        }

    def get_file_results(self):
        """return a lookup of changes, where each change has a list of files"""
        return self._data

    def get_summed_results(self):
        """Get summed values (e.g., lines changed) across files"""
        return self._data
