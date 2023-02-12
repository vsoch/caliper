__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"


class require_commit:
    """
    Require the metric to have a commit.
    """
    def __init__(self, func):
        update_wrapper(self, func)
        self.func = func

    def __get__(self, obj, objtype):
        return partial(self.__call__, obj)

    def __call__(self, cls, *args, **kwargs):
        commit = None
        if "commit" in kwargs:
            commit = kwargs['commit']       
        elif args:
            commit = args[0]

        if not commit:
            logger.warning(f'Metric extractor {cls.name} requires a commit.')
            return {}        
        return self.func(cls, *args, **kwargs)
