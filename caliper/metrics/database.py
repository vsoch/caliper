__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import re
import sqlite3
from contextlib import ContextDecorator
from functools import partial, update_wrapper

from caliper.logger import logger


class with_connection:
    """
    Provide the function with a connection with open and close.

    This is used as a decorator. When added, self.conn of the
    class is instantiated for interacting with, and cleaned up
    at the end.
    """

    def __init__(self, func):
        update_wrapper(self, func)
        self.func = func

    def __get__(self, obj, objtype):
        return partial(self.__call__, obj)

    def __call__(self, cls, *args, **kwargs):
        """
        Create the connection, only if we don't have one yet.

        This allows the database class to also be used as:

        with self.db:
            # Do queries
        """
        opened = False
        if cls.conn is None:
            opened = True
            cls.conn = cls.db.cursor()
        res = self.func(cls, *args, **kwargs)
        if opened:
            cls.conn.close()
            cls.conn = None
        return res


class Database(ContextDecorator):
    """
    In-memory (or file based) database to store metrics (if they get large)
    """

    def __init__(self, filename=":memory:", create_sql=None):
        self.db = sqlite3.connect(filename)
        self.db.create_function("regexp", 2, lambda x, y: 1 if re.search(x, y) else 0)
        self.conn = None
        if create_sql:
            # Allow for more than one statement
            if not isinstance(create_sql, list):
                create_sql = [create_sql]
            for sql in create_sql:
                self.execute(sql, fetchall=False)
        self.filename = filename

    def __enter__(self):
        self.conn = self.db.cursor()
        return self

    def __exit__(self, *exc):
        self.conn.close()
        self.conn = None
        return False

    @with_connection
    def execute(self, command, fetchall=True):
        """
        Execute a command to the table.

        fetch_all (when False) is intended for queries that you don't need a result.
        """
        try:
            if fetchall:
                return self.conn.execute(command).fetchall()
            return self.conn.execute(command)
        except Exception as e:
            logger.exit(e)

    @with_connection
    def execute_one(self, table, item):
        """
        Add one row to the table.
        """
        if not item:
            return

        keys = list(item.keys())
        values = tuple(item[x] for x in keys)
        insert_values = ",".join(keys)
        insert_qs = ",".join("?" * len(keys))
        try:
            return self.conn.execute(
                f"insert into {table}({insert_values}) values ({insert_qs})", values
            )
        except Exception as e:
            logger.exit(e)

    @with_connection
    def execute_many(self, table, items):
        """
        Create the database, creating the instances table.
        """
        if not items:
            return

        # Keys should be consistent across
        keys = list(items[0].keys())
        values = [tuple(item[x] for x in keys) for item in items]
        insert_values = ",".join(keys)
        insert_qs = ",".join("?" * len(keys))
        try:
            return self.conn.executemany(
                f"insert into {table}({insert_values}) values ({insert_qs})", values
            )
        except Exception as e:
            logger.exit(e)

    def filter_instances(self, props):
        """
        Use properties to filter instances down to a desired set based.
        """
        basequery = "SELECT DISTINCT cloud, cloud_select_id FROM instances"
        # No properties,
        if not props:
            return {"instance": self.execute(f"{basequery};")}

        query = ""

        # Assemble rest of query
        for _, key in enumerate(props):
            if not query:
                query = basequery
            else:
                query += f"INTERSECT {basequery}"

            # Case 1: we have a range with lookup min/max
            value = props[key]

            # Each function here returns a complete sql statement
            if key in ["like", "unlike"]:
                value = parse_regex(key, value)

            elif key.startswith("range:"):
                value = parse_range(key, value)
            else:
                value = parse_value(key, value)
            query += f" WHERE {value}\n"

        logger.debug(query)
        return {"instance": self.execute(f"{query};")}


def parse_value(key, value):
    """
    Parse a provided attribute value into an query.
    If we get here, it's not a range.

    True/False -> 1, 0
    string     -> "string"
    """
    if isinstance(value, bool):
        return (
            f"value_bool IS NOT NULL AND attribute='{key}' and value_bool={int(value)}"
        )
    if isinstance(value, str):
        return f"value IS NOT NULL AND attribute='{key}' and value='{value}'"
    if isinstance(value, (int, float)):
        return f"value_number IS NOT NULL AND attribute='{key}' and value_number={int(value)}"

    # We should not get here
    raise ValueError("A value that isn't bool or string should not be parsed.")


def parse_regex(key, value):
    """
    SELECT * from person WHERE name REGEXP '^us'
    """
    if key == "like":
        return f"instance REGEXP '{value}'"
    return f"NOT instance REGEXP '{value}'"


def parse_range(key, value):
    """
    Given a stated range, e.g.,:

    range_gpus: {'min': 2, 'max': None}

    Return either a min/max rule, or just a min,or just a max.
    """
    # If we get to a range without min/max this is an error (and shouldn't happen)
    key = key.replace("range:", "", 1)
    min_value = value["min"]
    max_value = value["max"]

    # All of these are numbers, so we only care about value_number
    if min_value is not None and max_value is not None:
        return f"value_number IS NOT NULL AND attribute='{key}' AND value_number >= {min_value} AND value_number <= {max_value}"

    if min_value is not None:
        return f"value_number IS NOT NULL AND attribute='{key}' and value_number >= {min_value}"

    # Max value set
    return f"value_number IS NOT NULL AND attribute='{key}' and value_number <= {max_value}"
