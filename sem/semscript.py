
#standard imports
from abc import ABC, abstractmethod
import logging
import os

# package imports
from .strconv import *
from .action import Action, ActionTakePic, ActionPlay


class ScriptCommand:
    """Base class for SEM script commands."""

    def __init__(self):
        pass


    @abstractmethod
    def is_nestable(self) -> bool:
        """Return whether the command can contain other commands."""
        return NotImplemented


    @abstractmethod
    def add_command(self, command) -> bool:
        """Add a command to this command's nested sequence."""
        return NotImplemented


    @abstractmethod
    def generate_actions(self, events, **kwargs):
        """Given this command and any nested commands, generate a list of
        Action objects."""
        return NotImplemented


class ForVarLoop(ScriptCommand):
    """Represents an SEM `FOR (VAR)` command block."""

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
    """Represents an SEM `FOR (INTERVALOMETER)` command block."""

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
    """Represents an SEM `ENDFOR` marker, not a true command."""

    def __init__(self, args=[]):
        pass


    def __str__(self) -> str:
        return "ENDFOR"


    def is_nestable(self) -> bool:
        return False


    def add_command(self, command: ScriptCommand) -> bool:
        raise ValueError("ENDFOR is not a compound command")


    def generate_actions(self, events, **kwargs):
        raise ValueError("ENDFOR should never actually be in scripts")


class Play(ScriptCommand):
    """Represents an SEM `PLAY` command."""

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


    def is_nestable(self) -> bool:
        return False


    def add_command(self, command: ScriptCommand) -> bool:
        raise ValueError("PLAY is not a compound command")


    def generate_actions(self, events, **kwargs):
        event = kwargs.get('override_event', self.event)
        time = events.get_time(event) + self.offset
        action = ActionPlay(time=time, soundfile=self.file,
                            comment=self.comment)
        # Just one action
        return [action]


class TakePic(ScriptCommand):
    """Represents an SEM `TAKEPIC` command."""

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


    def is_nestable(self) -> bool:
        return False


    def add_command(self, command: ScriptCommand) -> bool:
        raise ValueError("PLAY is not a compound command")


    def generate_actions(self, events, **kwargs):
        event = kwargs.get('override_event', self.event)
        time = events.get_time(event) + self.offset
        action = ActionTakePic(time=time, shutter=self.shutter_sec,
                               aperture=self.aperture, iso=self.iso,
                               comment=self.comment)
        # Just one action
        return [action]


