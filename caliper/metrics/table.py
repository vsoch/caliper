__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os

from rich.console import Console
from rich.table import Table as RichTable

import caliper.metrics.colors as colors
from caliper.logger import logger

here = os.path.dirname(os.path.abspath(__file__))


class Table:
    """
    Format a result into a table.
    """

    def __init__(self, data):
        self.data = data
        self.max_widths = {}
        self.ensure_complete()

    def available_width(self, columns):
        """
        Calculate available width based on fields we cannot truncate (urls)
        """
        # We will determine column width based on terminal size
        try:
            width = os.get_terminal_size().columns
        except OSError:
            width = 120

        # Calculate column width
        column_width = int(width / len(columns))
        updated = width

        for _, needed in self.max_widths.items():
            updated = updated - needed

        # We don't have enough space
        if updated < 0:
            logger.warning("Terminal is too small to correctly render!")
            return column_width

        # Otherwise, recalculate column width taking into account truncation
        # We use the updated smaller width, and break it up between columns
        # that don't have a max width
        return int(updated / (len(columns) - len(self.max_widths)))

    def ensure_complete(self):
        """
        If any data missing fields, ensure they are included
        """
        if isinstance(self.data, list):
            self.ensure_complete_list()
        # We don't check other types for now

    def ensure_complete_list(self):
        """
        Given a list result, check the fields.
        """
        fields = set()
        for entry in self.data:
            [fields.add(x) for x in entry.keys()]

        # Ensure fields are present
        for entry in self.data:
            for field in fields:
                if field not in entry:
                    entry[field] = ""

    def table_columns(self):
        """
        Shared function to return consistent table columns
        """
        # Plan to remove empty columns with count 0
        column_counts = {x: 0 for x, _ in self.data[0].items()}

        # Count entries for each column
        for entry in self.data:
            for column, value in entry.items():
                if value is not None:
                    column_counts[column] += 1

        # Get column titles
        columns = []
        contenders = list(self.data[0].keys())
        for column in contenders:
            if column_counts[column] == 0:
                continue
            columns.append(column)
        return columns

    def table_rows(self, columns, limit=25):
        """
        Shared function to yield rows as a list
        """
        # All keys are lowercase
        column_width = self.available_width(columns)
        for i, row in enumerate(self.data):
            # have we gone over the limit?
            if limit and i > limit:
                return

            parsed = []
            for column in columns:
                content = str(row[column]) if row[column] is not None else ""
                if content is not None and len(content) > column_width:
                    content = content[:column_width] + "..."
                parsed.append(content)
            yield parsed

    def table(self, limit=None, title=None, sort_by=None, ascending=False):
        """
        Pretty print a table of results.
        """
        table = RichTable(title=title)

        # No dependencies!
        if not self.data:
            print("There are no results to report.")
            return

        # Get column titles and unique colors
        columns = self.table_columns()
        column_colors = colors.get_rich_colors(len(columns))

        for i, column in enumerate(columns):
            title = " ".join([x.capitalize() for x in column.split("_")])
            table.add_column(title, style=column_colors[i])

        # If we want sorting, filter down to those that have it
        if sort_by is not None and sort_by in self.data[0].keys():
            subset = [x for x in self.data if x.get(sort_by) not in [None, ""]]
            if not subset:
                logger.warning(f"Using filter {sort_by} to sort removes all results.")
                return

            # Break into two groups - first those that have the value, then we will add the rest
            self.data = sorted(subset, key=lambda x: x[sort_by], reverse=not ascending)

        # Add rows
        for row in self.table_rows(columns, limit=limit):
            table.add_row(*row)

        # And print!
        console = Console()
        console.print(table, justify="left")
