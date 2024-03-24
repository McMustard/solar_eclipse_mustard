
# standard imports
from datetime import datetime, timedelta, time


def format_date(date: datetime):
    """Format the date in the way it should be used for sequences."""
    return date.strftime('%Y/%m/%d')


def format_time(time):
    """Format the time in the way it should be used for sequences."""
    return time.strftime('%H:%M:%S.%f')[:-5]


def parse_date(date_str) -> datetime:
    """Parse a date string of the form Y/M/D."""
    try:
        y4, m2, d2 = [int(x) for x in date_str.split('/')]
        return datetime(year=y4, month=m2, day=d2)
    except ValueError:
        pass

    raise ValueError(f"Failed to parse date string: {date_str}")


def parse_time(time_str, tzinfo=None) -> datetime:
    """Parse a time string of the form H:M:S.s."""

    try:
        hh, mm, ss = [x for x in time_str.split(':')]
        hh = int(hh)
        mm = int(mm)
        ss, tenths = ss.split('.')
        ss = int(ss)
        micro = int(tenths) * 100_000
        return time(hour=int(hh), minute=int(mm), second=int(ss),
                    microsecond=micro, tzinfo=tzinfo)
    except ValueError:
        pass

    raise ValueError(f"Failed to parse time string: {time_str}")


def parse_date_time(date_str, time_str, tzinfo=None) -> datetime:
    """Parse separate date and time strings."""

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
        raise ValueError(f"Failed to parse date-time string: "
                         f"{date_str} or {time_str}")


def parse_time_delta(sign_str, time_str):
    """Parses a time delta string along with a separate sign component."""

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
        raise RuntimeError(f"Failed to parse delta string: {time_str}")


def parse_shutter(shutter_str):
    """Parses a shutter speed as a float or int, or fraction thereof."""
    parts = [float(x) for x in shutter_str.split('/', maxsplit=2)]
    match parts:
        case [num, den]:
            return num / den

        case [sec]:
            return sec

    raise RuntimeError(f"Failed to parse shutter string: {shutter_str}")


