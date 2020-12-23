__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from abc import abstractmethod
from collections.abc import Mapping
from caliper.logger import logger
from caliper.utils.file import get_tmpdir
from distutils.version import StrictVersion
import os

here = os.path.abspath(os.path.dirname(__file__))

EMPTY_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class MetricBase:
    name = "metric"
    description = "Extract a metric for a particular tag or commit"
    date_time_format = "%Y-%m-%dT%H:%M:%S%z"

    def __init__(self, git=None, filename=__file__):
        self._data = {}
        self.git = git
        self.classpath = os.path.dirname(filename)

    def extract(self):
        for tag, index in self.iter_tags():
            self._data[index] = self._extract(tag.commit)

    @property
    def rawdata(self):
        return self._data

    @abstractmethod
    def _extract(self, commit):
        pass

    @abstractmethod
    def get_results(self):
        """return a lookup of the acceptable results type. This varies by
        metric, but if given a results dictionary, the metric should be able
        to match a result to a visualization, for example.
        """
        return {
            "by-file": self.get_file_results(),
            "by-group": self.get_group_results(),
        }

    def get_file_results(self):
        return []

    def get_group_results(self):
        return []

    def plot_results(self, result_file, outdir=None, force=False, title=None):
        """Given a metric has a template and a function to generate data
        for it, create the graph for the user.
        """
        template = os.path.join(self.classpath, "template.html")
        if os.path.exists(template) and hasattr(self, "get_plot_data"):
            from caliper.metrics.graphs import generate_graph

            outdir = outdir or get_tmpdir("%s-graph-" % self.name)
            data = self.get_plot_data(result_file, title=title)
            generate_graph(template=template, data=data, outdir=outdir, force=force)
        else:
            logger.warning("A metric must have template.html and get_plot_data.")

    def iter_tags(self):
        """yield a tag and a string to describe it."""
        for tag in getattr(self.git, "tags", []):
            yield tag, str(tag)


class ChangeMetricBase(MetricBase):

    name = "changemetric"
    description = "Extract a metric between two tags or commits"

    @abstractmethod
    def _extract(self, commit1, commit2):
        pass

    def extract(self):
        for tag, parent, index in self.iter_tags():
            self._data[index] = self._extract(tag.commit, parent)

    def _derive_labels(self):
        """Given a list of change versions, the labels should be returned sorted
        including any EMPTY declarations, which need to be moved to the beginning
        """
        labels = list(self._data)

        # Remove EMPTY label before sorting
        empty = None
        for label in labels:
            if "EMPTY" in label:
                empty = labels.pop(labels.index(label))
                break

        lookup = {x.split("..")[0].lstrip("v"): x for x in labels}
        pairs = [x.split("..") for x in labels]
        versions = [pair[0].lstrip("v") for pair in pairs]
        versions.sort(key=StrictVersion)
        if empty:
            return [empty] + [lookup[x] for x in versions]
        return [lookup[x] for x in versions]

    def iter_tags(self):
        """yield a tag, it's parent, and a string to describe the two for an
        index. In the case of the first commit, we produce an empty sha commit
        """
        for tag in getattr(self.git, "tags", []):
            parent = tag.commit.parents[0] if tag.commit.parents else EMPTY_SHA

            # Derive the diff name
            # TODO: figure out how to create empty commit object
            tag2 = "EMPTY" if isinstance(parent, str) else parent.message.strip()
            index = "%s..%s" % (tag2, tag)
            yield tag, parent, index


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
