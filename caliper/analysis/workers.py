__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.logger import logger
import multiprocessing
import itertools
import time
import signal
import sys


class Workers:
    def __init__(self, workers=None, show_progress=True):
        self.workers = workers or multiprocessing.cpu_count()
        logger.debug("Using %s workers for multiprocess." % self.workers)
        self.tasks = {}
        self.show_progress = show_progress

    def start(self):
        logger.debug("Starting analysis workers!")
        self.start_time = time.time()

    def end(self):
        self.end_time = time.time()
        self.runtime = self.runtime = self.end_time - self.start_time
        logger.debug("Ending analysis workers, runtime: %s sec" % (self.runtime))

    def add_task(self, key, func, params):
        """Given a function and a set of parameters, add the task to be processed
        with the workers. The key should be some meaningful index to be used to
        assoicate the result after run.
        """
        self.tasks[key] = (func, params)

    def run(self):
        """run will send a list of tasks, a tuple with arguments, through a function.
        The tasks should be added with add_task.
        """
        # Keep track of some progress for the user
        progress = 1
        total = len(self.tasks)

        # if we don't have tasks, don't run
        if not self.tasks:
            return

        # results will also have the same key to look up
        finished = dict()
        results = []

        try:
            prefix = "[%s/%s]" % (progress, total)
            if self.show_progress:
                logger.show_progress(0, total, length=35, prefix=prefix)
            pool = multiprocessing.Pool(self.workers, init_worker)

            self.start()
            for key, task in self.tasks.items():
                func, params = task
                if not self.show_progress:
                    logger.info("Processing task %s: %s of %s" % (key, progress, total))
                result = pool.apply_async(multi_wrapper, multi_package(func, [params]))

                # Store the key with the result
                results.append((key, result))
                break

            while len(results) > 0:
                pair = results.pop()
                key, result = pair
                result.wait()
                if self.show_progress:
                    logger.show_progress(progress, total, length=35, prefix=prefix)
                progress += 1
                prefix = "[%s/%s]" % (progress, total)
                finished[key] = result.get()

            self.end()
            pool.close()
            pool.join()

        except (KeyboardInterrupt, SystemExit):
            logger.error("Keyboard interrupt detected, terminating workers!")
            pool.terminate()
            sys.exit(1)

        except:
            logger.exit("Error running task.")

        return finished


# Supporting functions for MultiProcess Worker
def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def multi_wrapper(func_args):
    function, kwargs = func_args
    return function(**kwargs)


def multi_package(func, kwargs):
    zipped = zip(itertools.repeat(func), kwargs)
    return zipped
