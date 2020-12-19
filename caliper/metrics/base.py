__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from abc import abstractmethod
from collections.abc import Mapping
from caliper.logger import logger
import os

here = os.path.abspath(os.path.dirname(__file__))


class MetricBase:
    name = "metric"
    description = "Extract a metric for a particular tag or commit"

    @abstractmethod
    def extract(self, git):
        pass

    @abstractmethod
    def _extract(self, git, commit):
        pass

    @abstractmethod
    def get_file_results(self):
        pass

    @abstractmethod
    def get_summed_results(self):
        pass


class ChangeMetricBase(MetricBase):

    name = "changemetric"
    description = "Extract a metric between two tags or commits"

    @abstractmethod
    def _extract(self, git, commit1, commit2):
        pass


class MetricFinder(Mapping):
    """This is a metric cache (inspired by spack packages) that will keep
    a cache of all installed metrics under caliper/metrics/collection
    """

    _metrics = {}

    def __init__(self, metrics_path=None):

        # Default to the collection folder, add to metrics cache if not there
        self.metrics_path = metrics_path or os.path.join(here, "collection")
        self.update()

    def update(self):
        """Add a new path to the metrics cache, if it doesn't exist"""
        self._metrics = self._find_metrics()

    def _find_metrics(self):
        """Find metrics based on listing folders under the metrics collection
        folder.
        """
        # Create a metric lookup dictionary
        metrics = {}
        for metric_name in os.listdir(self.metrics_path):
            metric_dir = os.path.join(self.metrics_path, metric_name)
            metric_file = os.path.join(metric_dir, "metric.py")

            # Skip files in collection folder
            if os.path.isfile(metric_dir):
                continue

            # Continue if the file doesn't exist
            if not os.path.exists(metric_file):
                logger.debug(
                    "%s does not appear to have a metric.py, skipping." % metric_dir
                )
                continue

            # The class name means we split by underscore, capitalize, and join
            class_name = "".join([x.capitalize() for x in metric_name.split("_")])
            metrics[metric_name] = "caliper.metrics.collection.%s.metric.%s" % (
                metric_name,
                class_name,
            )
        return metrics

    def __getitem__(self, name):
        return self._metrics.get(name)

    def __iter__(self):
        return iter(self._metrics)

    def __len__(self):
        return len(self._metrics)
