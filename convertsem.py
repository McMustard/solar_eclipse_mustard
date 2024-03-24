#!/usr/bin/env Python

# standard imports
import argparse
import logging

# local imports
from sem import ScriptParser, EventParser

# third-party imports
import gphoto2 as gp


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

