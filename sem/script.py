
# package imports
from .semscript import *
from .sequence import Sequence


class Script:
    """Class for reading an SEM script, and generating a Sequence."""

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


    def add_command(self, command: ScriptCommand):
        """Adds a command to the list."""
        self.commands.append(command)


    def generate_sequence(self):
        """Generates a list of Action objects from the ScriptCommands
        objects."""
        actions = []
        for command in self.commands:
            more = command.generate_actions(self.events)
            actions.extend(more)
        return Sequence(actions)


class ScriptParser:
    """Class to parse an SEM script into a Script object."""

    def __init__(self):
        self.script = Script()
        self.stack = []


    def parse_script(self, filename):
        """Parse an SEM script file."""

        with open(filename, 'r') as file:
            return self._parse_script(file)


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


