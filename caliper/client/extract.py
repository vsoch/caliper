__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsExtractor
import logging

bot = logging.getLogger("caliper.client")


def main(args, extra):

    # TODO: need to create a manager depending on the package type.
    # Create a client to interact with
    client = MetricsExtractor()
