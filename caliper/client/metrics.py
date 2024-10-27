__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2024, Vanessa Sochat"
__license__ = "MPL 2.0"

import re

from caliper.metrics import MetricsExtractor


def main(args, extra):
    client = MetricsExtractor()
    for name, metric in client.metrics.items():
        if not args.query:
            print("%20s: %s" % (name, metric))
        elif args.query and re.search(args.query, name):
            print("%20s: %s" % (name, metric))
