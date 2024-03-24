
# standard imports
from datetime import datetime, timezone
import logging
import re

# package imports
from .strconv import parse_date_time, parse_time

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

        with open(filename, 'r', encoding='utf', errors='replace') as file:
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


