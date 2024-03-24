
# standard imports
import math


def find_nearest(iterable, value, distance=min, evaluator=None):
    """Returns the index and value closest to a given value."""
    def key(x):
        i, x = x
        if x is None:
            return float('inf')
        try:
            return abs(value - x)
        except ValueError:
            return float('inf')
        except TypeError:
            return float('inf')
    if evaluator:
        iterable = [evaluator(x) for x in iterable]
    return min(enumerate(iterable), key=key)


def iso_stops(iso):
    """Return the number of stops corresponding to the given ISO, where ISO
    100 is the baseline, at zero stops."""
    return math.log(iso/100, 2)


def ss_stops(ss):
    """Return the number of stops corresponding to the given shutter speed,
    where 1 second is the baseline, at zero stops."""
    return math.log(ss, 2)


def fstop_stops(ap):
    """Return the number of stops corresponding to the given aperture, where
    f/1 is 0 stops."""
    return -2 * math.log(ap, 2)

