#!/usr/bin/env python

# Purpose:
# Run simple camera capture sequences to exercise the `camera` module, to
# collect information about cameras, and to stress test them.


# standard imports
import argparse
from datetime import datetime, timedelta
import logging

# local imports
from camera import Camera, CameraInitFailed

# third-party imports
import gphoto2 as gp


def list_cameras():
    """List information about attached cameras."""
    # Load port data.
    ports = gp.PortInfoList()
    ports.load()

    # List ports.
    for i, port in enumerate(ports):
        name = port.get_name()
        path = port.get_path()
        dtype = port.get_type()
        print(f"port {i+1}: {name} on {path} [{dtype}]")

    # Load ability data.
    abilities_list = gp.CameraAbilitiesList()
    abilities_list.load()

    # Detect cameras.
    detected_cameras = abilities_list.detect(ports)

    # List detected cameras.
    for i, (model, port) in enumerate(detected_cameras):
        print(f"camera {i+1}: \"{model}\" on {port}")


def do_print(args):
    """Handle the `print` subcommand."""

    camera = Camera(args.model, args.port)
    camera.dump()
    camera.close()


def do_test(args):
    """Handle the `test` subcommand."""

    camera = Camera(args.model, args.port)

    # 
    if False:
        aps = [ '4', 'f/5.6', '1/8' ]
        isos = [ '125', '200', '401', '650' ]
        sss = [ '1/30', str(1/16), '1/20', '1', '2s' ]
    else:
        aps = args.apertures or [ ]
        isos = args.isos or [ ]
        sss = args.shutter_speeds or [ ]

    rounds = args.count or 1
    #burst = args.burst or 1
    burst = 1

    # Move around `t1` and `t2` to time different things.
    timing = []

    exposure_count = 0
    t_start = datetime.now()

    for _ in range(rounds):
        for ap in aps:
            camera.set_aperture(ap)
            for iso in isos:
                camera.set_iso(iso)
                for ss in sss:
                    print(f"Aperture {ap}, iso {iso}, ss {ss}")
                    camera.set_shutter_speed(ss)
                    camera.apply_settings()

                    t1 = datetime.now()
                    for count in range(burst):
                        camera.trigger_capture_and_wait()
                        exposure_count += 1
                    t2 = datetime.now()
                    delta = t2 - t1
                    # Discount the shutter speed
                    # TODO
                    timing.append(delta)
    t_end = datetime.now()

    camera.close()

    delta0 = timedelta()
    if timing:
        print("Timing data per shot:")
        print(f"tot: {sum(timing,start=delta0)}")
        print(f"avg: {sum(timing,start=delta0)/len(timing)}")
        print(f"min: {min(timing)}")
        print(f"max: {max(timing)}")

    delta1 = t_end - t_start
    print(f"Total execution time: {delta1}")
    print(f"Total exposures taken: {exposure_count}")


def do_capture(args):
    """Handles the `capture` subcommand."""
    camera = Camera(args.model, args.port)
    if args.aperture:
        camera.set_aperture(args.aperture)
    if args.iso:
        camera.set_iso(args.iso)
    if args.shutter_speed:
        camera.set_shutter_speed(args.shutter_speed)
    if args.aperture or args.iso or args.shutter_speed:
        camera.apply_settings()
    camera.capture()
    camera.close()


def main():
    """Main program."""

    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    subs = parser.add_subparsers(required=True)

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
    camera.add_argument('-m', '--model', type=str,
                        help="camera model name (exact)")
    camera.add_argument('-p', '--port', metavar="PORT", type=str,
                        help="port path (e.g. \"usb:000,000\")")

    # Exposure arguments
    exposure = argparse.ArgumentParser(add_help=False)
    exposure.add_argument('-F', '--aperture', type=str,
                          help="camera aperture setting")
    exposure.add_argument('-I', '--iso', type=str,
                          help="camera ISO setting")
    exposure.add_argument('-S', '--shutter-speed', '--ss', metavar="SPEED",
                          type=str,
                          help="camera shutter speed setting")

    # Subcommand: capture
    c_capture = subs.add_parser('capture',
                                parents=[common, camera, exposure],
                                help="take a quick capture")
    c_capture.add_argument('-b', '--burst', type=int,
                           help="number of shots to take")
    c_capture.add_argument('-d', '--delay', '--interval', type=float,
                           help="interval between shots")
    c_capture.set_defaults(function=do_capture)

    # Subcommand: print
    c_print = subs.add_parser('print',
                              parents=[common, camera],
                              help="print everything possible about " +
                              "the first connected camera")
    c_print.set_defaults(function=do_print)

    # Subcommand: test
    c_test = subs.add_parser('test',
                             parents=[common, camera],
                             help="cycle through some exposure settings, " +
                             "and take some pictures")
    c_test.add_argument('--apertures', nargs='*',
                        help="apertures to cycle")
    c_test.add_argument('--shutter-speeds', nargs='*',
                        help="shutter speeds to cycle")
    c_test.add_argument('--isos', nargs='*',
                        help="ISOs to cycle")
    c_test.add_argument('--count', default=1, type=int,
                        help="number of times to complete the sequence")
    c_test.set_defaults(function=do_test)

    # Parse
    args = parser.parse_args()

    # Set logging verbosity.
    LEVELS = [logging.WARN, logging.INFO, logging.DEBUG]
    verbosity = min(args.verbose, len(LEVELS))
    logging.getLogger().setLevel(LEVELS[verbosity])

    # Enable gphoto2 logging.
    if args.debug_gphoto:
        callback_obj = gp.check_result(gp.use_python_logging())

    # Execute the subcommand.
    try:
        # Listing cameras is a special action.
        if args.list_cameras:
            list_cameras()
            return

        if args.function:
            args.function(args)
    except CameraInitFailed as ex:
        logging.error(ex.message)


if __name__ == '__main__':
    main()

