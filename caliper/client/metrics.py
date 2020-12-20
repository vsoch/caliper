__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsExtractor
import re


def main(args, extra):

    client = MetricsExtractor()
    for name, metric in client.metrics.items():
        if not args.query:
            print("%20s: %s" % (name, metric))
        elif args.query and re.search(args.query, name):
            print("%20s: %s" % (name, metric))
