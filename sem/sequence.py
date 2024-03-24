
# standard imports
import csv
from datetime import timezone
import sys

# package imports
from .action import ActionTakePic, ActionPlay
from .fields import *
from .strconv import parse_date_time


class Sequence:
    """Sequence of timed Action objects."""

    def __init__(self, actions=None):
        self.actions = actions or [ ]
        # Sort the actions.
        self.actions = list(sorted(self.actions))


    def write_csv(self, file=None):
        """Writes the sequence into a CSV file with a header row."""

        file = file or sys.stdout
        writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for row in self.actions:
            writer.writerow(row.as_dict())


    def read_csv(self, file):
        """Reads a sequence from a CSV file with an optional header row."""
        # Clear actions.
        self.actions = []
        reader = csv.DictReader(file, fieldnames=FIELD_NAMES)
        for row in reader:
            action = self._make_action(row)
            if action:
                self.actions.append(action)


    def _make_action(self, csv_row):
        """Construct an Action object corresponding to a CSV data row."""
        if csv_row[F_DATE] == 'date':
            # header row
            return None

        # Extract fields
        time = parse_date_time(csv_row[F_DATE], csv_row[F_TIME],
                               tzinfo=timezone.utc)

        action = csv_row[F_ACTION]
        shutter = csv_row[F_SHUTTER]
        aperture = csv_row[F_APERTURE]
        iso = csv_row[F_ISO]
        file = csv_row[F_FILE]
        comment = csv_row[F_COMMENT]

        match action:
            case 'PICT':
                return ActionTakePic(time, shutter, aperture, iso, comment)

            case 'PLAY':
                return ActionPlay(time, file, comment)


