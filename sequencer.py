#!/usr/bin/env python

# standard imports
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import logging
import os
import time
import traceback as tb

# third-party imports
import gphoto2 as gp
from playsound import playsound

# local imports
import camera as cam
import sem

# Constants

SOUNDS_DIR = 'sounds'


class Sequencer:

    def __init__(self, args):
        self.sequence = sem.Sequence()

        self.no_sound = args.no_sound
        self.no_camera = args.no_camera
        self.actions = self._collect_actions(args)

        if self.no_camera:
            self.camera = None
        else:
            self.camera = self._select_camera(args)
        self.time_offset = self._set_clock(args)
        self.executor = ThreadPoolExecutor()


    def _collect_actions(self, args):
        # Scan the file
        with open(args.sequence, 'r', newline='') as seqfile:
            self.sequence.read_csv(seqfile)

        # Filter
        actions_out = []
        for action in self.sequence.actions:
            if isinstance(action, sem.ActionTakePic):
                if not self.no_camera:
                    actions_out.append(action)
            elif isinstance(action, sem.ActionPlay):
                if not self.no_sound:
                    actions_out.append(action)
        return actions_out


    def _select_camera(self, args):
        # Select the camera.
        return cam.Camera(model=args.model, port=args.port)


    def _set_clock(self, args):
        if args.time:
            current = dt.datetime.now().astimezone()
            virtual = args.time.astimezone()
            logging.info(f"Setting virtual time to {virtual} from {current}")
            return args.time.astimezone() - dt.datetime.now().astimezone()
        else:
            return dt.timedelta()


    def _current_time(self):
        return dt.datetime.now().astimezone() + self.time_offset


    def execute(self):
        for action in self.actions:
            now = self._current_time()
            delay = action.time - now
            delay_sec = delay.total_seconds()

            if delay_sec < 0:
                # Skip the command (time travel)
                continue

            logging.info(f"Next command in {delay_sec} seconds")

            if delay_sec > 0:
                time.sleep(delay_sec)

            self._execute_action(action)


    def _execute_action(self, action):
        if isinstance(action, sem.ActionTakePic):
            self.executor.submit(self._execute_pict, action)
        elif isinstance(action, sem.ActionPlay):
            self.executor.submit(self._execute_play, action)


    def _execute_play(self, action):
        filename = os.path.join(SOUNDS_DIR, action.soundfile)
        logging.info(f"Play: {filename}")
        try:
            playsound(filename)
        except:
            tb.print_exc()


    def _execute_pict(self, action):
        # TODO set settings early
        try:
            f = action.aperture
            i = action.iso
            s = action.shutter
            self.camera.set_aperture(f)
            self.camera.set_iso(i)
            self.camera.set_shutter_speed(s)
            self.camera.apply_settings()

            self.camera.trigger_capture_and_wait()
        except:
            tb.print_exc()


# Custom argument types

def date_time_arg(date_time_str):
    """Parse arguments of type `date_time'."""
    date, time = date_time_str.split(' ', maxsplit=2)
    return sem.parse_date_time(date, time)


# Main program

def main():
    """Main program."""

    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-V', '--verbose', action='count', default=0,
                        help="increase log verbosity")
    common.add_argument('-G', '--debug-gphoto', action='store_true',
                        help="enable gphoto2 logging (very verbose)")

    # Camera-selection arguments
    camera = argparse.ArgumentParser(add_help=False)
    camera.add_argument('--list-cameras', action='store_true',
                        help="list camera models and exit")
    camera.add_argument('-m', '--model', type=str, required=True,
                        help="camera model name (exact)")
    camera.add_argument('-p', '--port', metavar="PORT", type=str,
                        help="port path (e.g. \"usb:000,000\")")

    # Main arguments
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@',
                                     parents=[common, camera])
    parser.add_argument('sequence', metavar='SEQUENCE',
                        help="times and exposures sequence file")

    parser.add_argument('-t', '--time', type=date_time_arg,
                        help="time travel: set the virtual current local " +
                        "time")

    parser.add_argument('--no-sound', action='store_true',
                        help="skip PLAY actions")
    parser.add_argument('--no-camera', action='store_true',
                        help="skip PICT actions")

    # Parse
    args = parser.parse_args()

    # Set logging verbosity.
    LEVELS = [logging.WARN, logging.INFO, logging.DEBUG]
    verbosity = min(args.verbose, len(LEVELS))
    logging.getLogger().setLevel(LEVELS[verbosity])

    # Enable gphoto2 logging.
    if args.debug_gphoto:
        callback_obj = gp.check_result(gp.use_python_logging())

    if args.time:
        print("=" * 78)
        print("TIME OVERRIDE IN EFFECT")
        print("=" * 78)

    # Execute the subcommand.
    try:
        sequencer = Sequencer(args)
        sequencer.execute()
    except cam.CameraInitFailed as ex:
        logging.error(ex.message)


if __name__ == '__main__':
    main()

