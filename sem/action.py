
# standard imports
from abc import ABC, abstractmethod
from datetime import datetime

# module imports
from .fields import *
from .strconv import format_date, format_time


class Action(ABC):
    """Base class for actions that can be sequenced."""
    
    def __init__(self, time: datetime):
        self.time = time


    def __lt__(self, other):
        return self.time < other.time


    @abstractmethod
    def columns(self):
        return NotImplemented


    @abstractmethod
    def as_dict(self):
        return NotImplemented


class ActionTakePic(Action):
    """Represents the capture of an image."""
    
    def __init__(self, time, shutter, aperture, iso, comment):
        super().__init__(time)
        self.shutter = shutter
        self.aperture = aperture
        self.iso = iso
        self.comment = comment


    def __repr__(self):
        return (f"ActionTakePic(time={self.time},shutter={self.shutter},"
                f"aperture={self.aperture},iso={self.iso},"
                f"comment={self.comment}")


    def __str__(self):
        return (f"{self.time}: Take Picture SS={self.shutter} "
                f"aperture: {self.aperture}, ISO={self.iso}")


    def columns(self):
        date = format_date(self.time)
        time = format_time(self.time)
        return [date, time, 'PICT', self.shutter, self.aperture, self.iso,
                self.comment]


    def as_dict(self):
        date = format_date(self.time)
        time = format_time(self.time)
        return { F_DATE: date, F_TIME: time, F_ACTION: 'PICT', F_SHUTTER:
                self.shutter, F_APERTURE: self.aperture, F_ISO: self.iso,
                F_COMMENT: self.comment }


class ActionPlay(Action):
    """Represents the playing of a sound file."""

    def __init__(self, time, soundfile, comment):
        super().__init__(time)
        self.soundfile = soundfile
        self.comment = comment


    def __repr__(self):
        return (f"ActionPlay(time={self.time},soundfile={self.soundfile},"
                f"comment={self.comment})")


    def __str__(self):
        return (f"{self.time}: Play sound {self.soundfile}")


    def columns(self):
        date = format_date(self.time)
        time = format_time(self.time)
        return [date, time, 'PLAY', self.soundfile, self.comment]


    def as_dict(self):
        date = format_date(self.time)
        time = format_time(self.time)
        return { F_DATE: date, F_TIME: time, F_ACTION: 'PLAY',
                F_FILE: self.soundfile, F_COMMENT: self.comment }


