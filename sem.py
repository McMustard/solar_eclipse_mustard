#!/usr/bin/env python

# standand imports
import argparse
import csv
import datetime as dt
from datetime import datetime, timezone, timedelta
import math
import logging
import os
import re
import sys


# Constants

# Field names
F_DATE = 'date'
F_TIME = 'time_utc'
F_ACTION = 'action'
F_SHUTTER = 'shutter_speed'
F_APERTURE = 'aperture'
F_ISO = 'iso'
F_FILE = 'file'
F_COMMENT = 'comment'

# Field names for the output CSV
FIELD_NAMES = [ F_DATE, F_TIME, F_ACTION, F_SHUTTER, F_APERTURE, F_ISO,
               F_FILE, F_COMMENT ]


# Functions

def parse_date(date_str) -> datetime:
    try:
        y4, m2, d2 = [int(x) for x in date_str.split('/')]
        return datetime(year=y4, month=m2, day=d2)
    except ValueError:
        pass

    raise RuntimeError(f"Failed to parse date string: {date_str}")


def parse_time(time_str, tzinfo=None) -> datetime:
    try:
        hh, mm, ss = [x for x in time_str.split(':')]
        hh = int(hh)
        mm = int(mm)
        ss, tenths = ss.split('.')
        ss = int(ss)
        micro = int(tenths) * 100_000
        return dt.time(hour=int(hh), minute=int(mm), second=int(ss),
                       microsecond=micro, tzinfo=tzinfo)
    except ValueError:
        pass

    raise RuntimeError(f"Failed to parse time string: {time_str}")


def parse_date_time(date_str, time_str, tzinfo=None) -> datetime:
    try:
        y4, m2, d2 = [int(x) for x in date_str.split('/')]
        hh, mm, ss = [x for x in time_str.split(':')]

        hh = int(hh)
        mm = int(mm)
        ss, tenths = ss.split('.')
        ss = int(ss)
        micro = int(tenths) * 100_000
        return datetime(year=y4, month=m2, day=d2,
                       hour=int(hh), minute=int(mm), second=int(ss),
                       microsecond=micro, tzinfo=tzinfo)
    except ValueError:
        pass

    raise RuntimeError(f"Failed to parse date-time string: " +
                       f"{date_str} or {time_str}")


def parse_time_delta(sign_str, time_str):

    def make_delta(hh, mm, ss):
        delta = timedelta(hours=hh, minutes=mm, seconds=ss)
        if sign_str == '-':
            return -delta
        return delta

    try:
        components = [float(x) for x in time_str.split(':')]
        match components:
            case [hh, mm, ss]:
                return make_delta(hh, mm, ss)
            case [mm, ss]:
                return make_delta(0, mm, ss)

    except ValueError:
        pass

    raise RuntimeError(f"Failed to parse delta string: {time_str}")


def parse_shutter(shutter_str):
    parts = [float(x) for x in shutter_str.split('/', maxsplit=2)]
    match parts:
        case [num, den]:
            return num / den

        case [sec]:
            return sec

    raise RuntimeError(f"Failed to parse shutter string: {shutter_str}")


def find_bounds(sequence, target, key=None):
    seq_forward = list(enumerate(sequence))
    seq_reverse = list(reversed(seq_forward))

    if key is None:
        key = lambda x: x

    def sub_search(sequence, check):
        index, king = None, None
        for i, item in sequence:
            subitem = key(item)
            if check(subitem):
                index, king = i, item
            else:
                break
        return index, king

    min_index, min_king = sub_search(seq_forward,
                                     lambda x: x <= target)
    max_index, max_king = sub_search(seq_reverse,
                                     lambda x: x >= target)
    return ((min_index, min_king), (max_index, max_king))


# Classes

class ScriptCommand:
    """Base class for script commands."""

    def __init__(self):
        pass

    def show(self):
        pass

    def is_nestable(self) -> bool:
        return NotImplemented

    def add_command(self, command) -> bool:
        return NotImplemented

    def generate_actions(self, events, **kwargs):
        return NotImplemented


class ForVarLoop(ScriptCommand):

    def __init__(self, args):
        
        try:
            start, step, end = args
            self.start = float(start)
            self.step = float(step)
            self.end = float(end)
        except:
            logging.error(f"ForVarLoop unexpected args: {args}")
            raise

        self.commands = []

    def __str__(self) -> str:
        return f"FOR (VAR) {self.start} : {self.step} : {self.end}"

    def show(self):
        print(self)
        for c in self.commands:
            c.show()
        end = ForLoopEnd()
        end.show()

    def is_nestable(self) -> bool:
        return True

    def add_command(self, command: ScriptCommand) -> bool:
        if command.is_nestable():
            raise ValueError("cannot nest nestables")
        if isinstance(command, ForLoopEnd):
            return True
        else:
            self.commands.append(command)
        return False

    def generate_actions(self, events, **kwargs):
        actions = []
        value = self.start
        while value < self.end:
            for c in self.commands:
                var = f'{value:04.1f}'
                event, post = c.event.split(' ', maxsplit=2)
                more = c.generate_actions(events,
                                          override_event=f"{event} {var}")
                if event in ['MAGPRE', 'MAGPOST']:
                    for action in more:
                        action.comment += f" (Mag. {var}%)"
                actions.extend(more)
                value += self.step
        return actions


class ForIterLoop(ScriptCommand):

    def __init__(self, args):
        
        try:
            kind, delay, iters = args
            self.kind = int(kind)
            self.delay = float(delay)
            # Round away those odd 1/1000ths
            #self.delay = math.floor(self.delay * 100) / 100
            self.iters = int(iters)
        except Exception as ex:
            logging.error(f"ForIterLoop unexpected args: {args}")
            raise

        self.commands = []

    def __str__(self) -> str:
        return (f"FOR (INTERVALOMETER) {self.kind} : {self.delay} : " +
                f"{self.iterations}")

    def show(self):
        print(self)
        for c in self.commands:
            c.show()
        end = ForLoopEnd()
        end.show()

    def is_nestable(self) -> bool:
        return True

    def add_command(self, command: ScriptCommand) -> bool:
        if command.is_nestable():
            raise ValueError("cannot nest nestables")
        if isinstance(command, ForLoopEnd):
            return True
        else:
            self.commands.append(command)
        return False

    def generate_actions(self, events, **kwargs):
        actions = []
        value = 0.0
        for i in range(self.iters):
            for c in self.commands:
                microsec = int(value * 100) * 10_000
                var = timedelta(microseconds=microsec)
                more = c.generate_actions(events)
                for action in more:
                    action.time += var
                    action.comment += f" (iter. {i+1:03d})"
                actions.extend(more)
            if self.kind == 0:
                value -= self.delay
            else:
                value += self.delay
        return actions


class ForLoopEnd(ScriptCommand):

    def __init__(self, args=[]):
        pass

    def __str__(self) -> str:
        return "ENDFOR"

    def show(self):
        print("END FOR")

    def is_nestable(self) -> bool:
        return False

    def add_command(self, command: ScriptCommand) -> bool:
        raise RuntimeError("ENDFOR is not a compound command")

    def generate_actions(self, events, **kwargs):
        raise RuntimeError("ENDFOR should never actually be in scripts")


class Play(ScriptCommand):

    def __init__(self, args):
        try:
            (event, sign, offset, file, _, _, _, _, _, _, _, comment) = args
            self.event = event
            self.offset = parse_time_delta(sign, offset)
            file, _ = os.path.splitext(file)
            self.file = f"{file}.mp3"
            self.comment = comment
        except:
            logging.error(f"Play unexpected args: {args}")
            raise

    def __str__(self) -> str:
        return f"PLAY"

    def show(self):
        print(self)

    def is_nestable(self) -> bool:
        return False

    def add_command(self, command: ScriptCommand) -> bool:
        raise RuntimeError("PLAY is not a compound command")

    def generate_actions(self, events, **kwargs):
        event = kwargs.get('override_event', self.event)
        time = events.get_time(event) + self.offset
        action = ActionPlay(time=time, soundfile=self.file,
                            comment=self.comment)
        # Just one action
        return [action]


class TakePic(ScriptCommand):

    def __init__(self, args):
        try:
            (event, sign, offset, camera, shutter, aperture, iso, burst,
             quality, size, incremental, comment) = args
            self.event = event
            self.offset = parse_time_delta(sign, offset)
            self.shutter_sec = parse_shutter(shutter)
            self.aperture = float(aperture)
            self.iso = int(iso)
            self.comment = comment
        except:
            logging.error(f"TakePic unexpected args: {args}")
            raise

    def __str__(self) -> str:
        return f"TAKEPIC"

    def show(self):
        print(self)

    def is_nestable(self) -> bool:
        return False

    def add_command(self, command: ScriptCommand) -> bool:
        raise RuntimeError("PLAY is not a compound command")

    def generate_actions(self, events, **kwargs):
        event = kwargs.get('override_event', self.event)
        time = events.get_time(event) + self.offset
        action = ActionTakePic(time=time, shutter=self.shutter_sec,
                               aperture=self.aperture, iso=self.iso,
                               comment=self.comment)
        # Just one action
        return [action]


class Action:
    
    def __init__(self, time: datetime):
        self.time = time

    def __lt__(self, other):
        return self.time < other.time


class ActionTakePic(Action):
    
    def __init__(self, time, shutter, aperture, iso, comment):
        super().__init__(time)
        self.shutter = shutter
        self.aperture = aperture
        self.iso = iso
        self.comment = comment

    def __str__(self):
        return (f"{self.time}: Take Picture SS={self.shutter} " +
                f"aperture: {self.aperture}, ISO={self.iso}")

    def columns(self):
        date = self.time.strftime('%Y/%m/%d')
        time = self.time.strftime('%H:%M:%S.%f')[:-5]
        return [date, time, 'PICT', self.shutter, self.aperture, self.iso,
                self.comment]

    def as_dict(self):
        date = self.time.strftime('%Y/%m/%d')
        time = self.time.strftime('%H:%M:%S.%f')[:-5]
        return { F_DATE: date, F_TIME: time, F_ACTION: 'PICT', F_SHUTTER:
                self.shutter, F_APERTURE: self.aperture, F_ISO: self.iso,
                F_COMMENT: self.comment }


class ActionPlay(Action):

    def __init__(self, time, soundfile, comment):
        super().__init__(time)
        self.soundfile = soundfile
        self.comment = comment

    def __str__(self):
        return (f"{self.time}: Play sound {self.soundfile}")

    def columns(self):
        date = self.time.strftime('%Y/%m/%d')
        time = self.time.strftime('%H:%M:%S.%f')[:-5]
        return [date, time, 'PLAY', self.soundfile, self.comment]

    def as_dict(self):
        date = self.time.strftime('%Y/%m/%d')
        time = self.time.strftime('%H:%M:%S.%f')[:-5]
        return { F_DATE: date, F_TIME: time, F_ACTION: 'PLAY',
                F_FILE: self.soundfile, F_COMMENT: self.comment }


class Script:

    def __init__(self):
        # List of commands
        self.commands = []
        # Event manager.
        self.events = None

    def __str__(self) -> str:
        s = ''
        for i, c in enumerate(self.commands):
            s += f"{i+1}: {c}\n"
        return s

    def show(self):
        for i, c in enumerate(self.commands):
            c.show()

    def add_command(self, command):
        self.commands.append(command)

    def generate_sequence(self):
        actions = []
        for command in self.commands:
            more = command.generate_actions(self.events)
            actions.extend(more)
        return Sequence(actions)


class Sequence:
    """Flat equivalent of `Script`"""

    def __init__(self, actions=None):
        self.actions = actions or [ ]
        # Sort the actions.
        self.actions = list(sorted(self.actions))

    def write_csv(self, file=None):
        file = file or sys.stdout
        writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for row in self.actions:
            writer.writerow(row.as_dict())

    def read_csv(self, file):
        # Clear actions.
        self.actions = []
        reader = csv.DictReader(file, fieldnames=FIELD_NAMES)
        for row in reader:
            action = self._make_action(row)
            if action:
                self.actions.append(action)

    def _make_action(self, csv_row):
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


class ScriptParser:

    def __init__(self):
        self.script = Script()
        self.stack = []

    def parse_script(self, filename):

        with open(filename, 'r') as file:
            return self._parse_script(file)

    def _make_command(self, line):
        args = [x for x in line.split(',')]

        match args:

            case ['FOR', '(VAR)', *rest]:
                return ForVarLoop(rest)

            case ['FOR', '(INTERVALOMETER)', *rest]:
                return ForIterLoop(rest)

            case ['ENDFOR', *rest]:
                return ForLoopEnd(rest)

            case ['TAKEPIC', *rest]:
                return TakePic(rest)

            case ['PLAY', *rest]:
                return Play(rest)

            case [unknown, *rest]:
                raise RuntimeError(f"Unknown command {unknown}")

        return None


    def _parse_script(self, file):

        for line in file:
            # Remove outside spaces
            line = line.strip()
            if line.startswith('#'):
                # Skip comments.
                pass
            elif not line:
                # Skip empty lines
                pass
            else:
                command = self._make_command(line)
                if command:
                    self._add_command(command)

        return self.script

    def _add_command(self, command):
        if self.stack:
            # Apply the command to the stack.
            top = self.stack[-1]
            done = top.add_command(command)
            if done:
                self.stack.pop()
        else:
            # Apply the command to the script.
            if command.is_nestable():
                self.stack.append(command)
            self.script.add_command(command)


class EventManager:

    def __init__(self, events: { str : datetime },
                 pre_mags: [ (float, datetime ) ],
                 post_mags: [ (float, datetime ) ],
                 max_magnitude: float):
        self.events = events
        self.pre_magnitudes = pre_mags
        self.post_magnitudes = list(reversed(post_mags))
        self.max_magnitude = max_magnitude or 1.0
        self.max_magnitude = float(self.max_magnitude)

    def get_time(self, name) -> datetime:
        # Expected events
        # C1, C2, C3, C4, MAX: directly in self.events
        # MAGPRE <float>, MAGPOST <float>
        if name in self.events:
            return self.events[name]
        parts = name.split(' ')

        match parts:
            case ['MAGPRE', percent]:
                pct = float(percent) / 100
                time = self.get_magnitude_time(pct, False)
                if time:
                    return time
                pct = self.max_magnitude * pct
                # Compute duration between when the magnitude starts to
                # increase from 0 (C1), up until it reaches its maximum (MAX).
                t1 = self.get_time('C1')
                t2 = self.get_time('C2')
                # Method: linear
                time = t2 - t1
                offset = time * pct
                return t1 + offset
            case ['MAGPOST', percent]:
                pct = float(percent) / 100
                time = self.get_magnitude_time(pct, True)
                if time:
                    return time
                # Like MAGPRE, but different events
                t1 = self.get_time('C3')
                t2 = self.get_time('C4')
                delta = t2 - t1
                offset = delta * pct
                # unsure about this one
                return t2 - offset

        logging.error(f"Timing of event {name} failed!")
        return None

    def get_magnitude_time(self, magnitude, post):
        mags = self.post_magnitudes if post else self.pre_magnitudes
        lo, hi = find_bounds(mags, magnitude, key=lambda x: x[0])
        lo_i, (lo_m, lo_t) = lo
        hi_i, (hi_m, hi_t) = hi

        # If the bounds are the same, return the time.
        if lo_i == hi_i:
            return lo_t

        # Else, return a time in the middle.
        delta_m = hi_m - lo_m
        percent = (magnitude - lo_m) / delta_m
        offset_t = (hi_t - lo_t) * percent
        ans = lo_t + offset_t
        return ans


class EventParser:

    def __init__(self):
        date = r'(\d{4}/\d{2}/\d{2})'
        time = r'(\d{2}:\d{2}:\d{2}\.\d)'
        cX_a = r'(.).. Contact'
        cX_b = r'C(\d)'
        maxe = r'Max Eclipse'
        spc = r'\s+'
        rest = r'.*'
        decfrac = r'([0-9.]+)'

        self.re_cX_a = re.compile(cX_a + spc + date + spc + time + rest)
        self.re_cX_b = re.compile(cX_b + spc + date + spc + time + rest)
        self.re_max = re.compile(maxe + spc + date + spc + time + rest)
        self.re_maxmag = re.compile(r'Magnitude at maximum .* ' + decfrac)
        self.re_magn = re.compile(time + spc + decfrac + spc + decfrac + spc
                                  + decfrac + rest)

    def parse(self, filename) -> EventManager:
        if not filename:
            return None

        events = { }

        prev_mag = float('-inf')
        pre_mags = [ ]
        post_mags = [ ]
        # Start filling pre-mags
        magnitudes = pre_mags
        max_magnitude = None

        default_date = None

        with open(filename, 'r') as file:
            for line in file:
                if m := self.re_cX_a.match(line):
                    num, date, time = m.groups()
                    event = f"C{num}"
                    time = parse_date_time(date, time, tzinfo=timezone.utc)
                    if not default_date:
                        default_date = time.date()
                    events[event] = time
                elif m := self.re_cX_b.match(line):
                    num, date, time = m.groups()
                    event = f"C{num}"
                    time = parse_date_time(date, time, tzinfo=timezone.utc)
                    events[event] = time
                elif m := self.re_max.match(line):
                    date, time = m.groups()
                    event = "MAX"
                    events[event] = parse_date_time(date, time,
                                                    tzinfo=timezone.utc)
                elif m := self.re_maxmag.match(line):
                    max_magnitude = m.group(1)
                elif m := self.re_magn.match(line):
                    time, _, _, mag = m.groups()
                    time = parse_time(time, tzinfo=timezone.utc)
                    date = datetime.combine(default_date, time)
                    mag = float(mag)
                    if prev_mag and mag < prev_mag:
                        # We've shifted to "post"
                        magnitudes = post_mags
                        # Stop checking.
                        prev_mag = None
                    elif prev_mag:
                        prev_mag = mag
                    magnitudes.append((mag, date))

        if max_magnitude:
            logging.info(f"Max magnitude: {max_magnitude}")
        else:
            logging.error("Did not find max. magnitude in contact file")
        logging.info(f"Found {len(pre_mags)} pre mags")
        logging.info(f"Found {len(post_mags)} post mags")
        return EventManager(events, pre_mags, post_mags, max_magnitude)


# Main function

def main():
    """Main program."""
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

    parser.add_argument('script',  metavar='SCRIPT',
                        help="Solar Eclipse Maestro script")
    parser.add_argument('-t', '--timing-file', required=True,
                        help="file contanining contact times")
    parser.add_argument('-o', '--output-file',
                        help="file name for CSV command output")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Show log messages, stackable")

    args = parser.parse_args()

    LEVELS = [logging.WARN, logging.INFO, logging.DEBUG]
    verbosity = min(args.verbose, len(LEVELS))
    logging.getLogger().setLevel(LEVELS[verbosity])

    scr_parser = ScriptParser()
    script = scr_parser.parse_script(args.script)

    if args.timing_file:
        timing_parser = EventParser()
        script.events = timing_parser.parse(args.timing_file)
        sequence = script.generate_sequence()

        if args.output_file not in [None, '-']:
            with open(args.output_file, 'w', newline='') as outf:
                sequence.write_csv(file=outf)
        else:
            sequence.write_csv()

if __name__ == '__main__':
    main()

