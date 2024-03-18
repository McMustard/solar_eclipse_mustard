#!/usr/bin/env python

# standard imports
import argparse
import datetime as dt
import logging
import math
import time

# third-party imports
import gphoto2 as gp

# Keywords for searching settings, to accommodate different makes.
ISO_KEYWORDS = [ 'iso' ]
APERTURE_KEYWORDS = [ 'aperture', 'f-number' ]
SHUTTER_SPEED_KEYWORDS = [ 'shutterspeed' ]

# Functions

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
    return math.log(iso/100, 2)


def ss_stops(ss):
    return math.log(ss, 2)


def fstop_stops(ap):
    return -2 * math.log(ap, 2)


def dump_abilities(abilities):
    """Print the values of a gp.CameraAbilities object"""
    print("Camera abilities: ")
    print(f"{abilities.device_type=}")
    print(f"{abilities.file_operations=}")
    print(f"{abilities.folder_operations=}")
    print(f"{abilities.id=}")
    print(f"{abilities.library=}")
    print(f"{abilities.model=}")
    print(f"{abilities.operations=}")
    print(f"{abilities.port=}")
    print(f"{abilities.speed=}")
    print(f"{abilities.status=}")
    print(f"{abilities.usb_class=}")
    print(f"{abilities.usb_product=}")
    print(f"{abilities.usb_subclass=}")
    print(f"{abilities.usb_vendor=}")


def dump_widget(widget, tabs=0):
    tab = tabs * 4 * ' '

    print(f"{tab}{widget.get_label()} [{widget.get_name()}]:")

    try:
        print(f"{tab}    choices: {', '.join(widget.get_choices())}")
    except gp.GPhoto2Error:
        # choices N/A
        pass

    try:
        print(f"{tab}    range: {widget.get_range()}")
    except gp.GPhoto2Error:
        # range N/A
        pass

    try:
        print(f"{tab}    value: {widget.get_value()}")
    except gp.GPhoto2Error:
        # value N/A
        pass

    for c in widget.get_children():
        dump_widget(c, tabs + 1)


class Widget:
    """Decorates a gp.widget object tree"""

    def __init__(self, gp_widget):
        self._build(gp_widget, self)


    def _build(self, gp_widget, widget):
        widget.gp_widget = gp_widget
        widget.name = gp_widget.get_name()
        widget.label = gp_widget.get_label()
        widget.choices = None
        widget.range = None
        widget.value = None
        widget.children = []

        wtype = gp_widget.get_type()
        get_choices, get_toggle, get_range, get_value = [False] * 4

        # Extract values depending on the widget type.
        match wtype:
            case gp.GP_WIDGET_SECTION:
                widget.wtype = 'section'

            case gp.GP_WIDGET_TEXT:
                widget.wtype = 'text'
                get_value = True

            case gp.GP_WIDGET_RANGE:
                widget.wtype = 'range'
                get_range = True
                get_value = True

            case gp.GP_WIDGET_TOGGLE:
                widget.wtype = 'toggle'
                get_toggle = True
                get_value = True

            case gp.GP_WIDGET_RADIO:
                widget.wtype = 'radio'
                get_choices = True
                get_value = True

            case gp.GP_WIDGET_MENU:
                widget.wtype = 'menu'
                get_choices = True
                get_value = True

            case gp.GP_WIDGET_DATE:
                widget.wtype = 'date'
                get_value = True

        if get_choices:
            widget.choices = list(gp_widget.get_choices())

        if get_range:
            widget.slider = list(gp_widget.get_range())

        if get_value:
            widget.value = gp_widget.get_value()

        if get_toggle:
            widget.choices = [0, 1]

        # Descend into child nodes.
        for gp_child in gp_widget.get_children():
            new_child = Widget(gp_child)
            widget.children.append(new_child)


class IsoController:
    """Select the iso setting."""
    
    def __init__(self, widget):
        self.widget = widget
        self.iso_strs = widget.choices
        self.iso_ints = [int(x) for x in widget.choices]
        self.iso_map = { }


    def select(self, iso):
        gp_widget = self.widget.gp_widget
        if iso in self.iso_strs:
            logging.info(f"Setting iso to {iso} directly")
            gp_widget.set_value(iso)
        elif iso in self.iso_map:
            logging.info(f"Setting iso to {iso} via cache")
            gp_widget.set_value(self.iso_map[iso])
        else:
            try:
                i, v = find_nearest(self.iso_ints, int(iso),
                                    distance=iso_stops)
                closest_iso = self.iso_strs[i]
                logging.info(f"Closest iso: {closest_iso}")
                self.iso_map[iso] = closest_iso
                gp_widget.set_value(closest_iso)
            except ValueError:
                logging.error(f"Cannot set iso to {iso}")


class ApertureController:
    """Select the aperture setting, accepting different notations."""
    
    def __init__(self, widget):
        self.widget = widget
        self.fstop_strs = widget.choices
        logging.info(f"Apertures: {self.fstop_strs}")
        self.fstop_norms = [self._normalize_fstop(x)
                               for x in self.fstop_strs]
        self.fstop_map = { }


    def select(self, fstop):
        gp_widget = self.widget.gp_widget
        if fstop in self.fstop_strs:
            logging.info(f"Setting aperture to {fstop} directly")
            gp_widget.set_value(fstop)
        elif fstop in self.fstop_map:
            logging.info(f"Setting aperture to {fstop} via cache")
            gp_widget.set_value(self.fstop_map[fstop])
        else:
            logging.info(f"Need to look up aperture {fstop}")
            try:
                norm = self._normalize_fstop(fstop)
                # Aperture isn't linear, but this will be fine.
                i, v = find_nearest(self.fstop_norms, norm,
                                    distance=fstop_stops)
                closest_fstop = self.fstop_strs[i]
                logging.info(f"Closest aperture: {closest_fstop}")
                self.fstop_map[fstop] = closest_fstop
                gp_widget.set_value(closest_fstop)
            except ValueError:
                logging.error(f"Cannot set fstop to {fstop}")

    def _normalize_fstop(self, fstop):
        """Normalize aperture, e.g. 8, 1/8, f/8 --> 8"""
        match fstop.split('/', maxsplit=2):
            case [den] | ['f', den] | ['1', den]:
                return float(den)
            case _:
                logging.error(f"Cannot handle aperture {fstop}")
        return None


class ShutterSpeedController:
    """Select the shutter speed, accepting different notations."""

    def __init__(self, widget):
        self.widget = widget
        self.ss_strs = widget.choices
        self.ss_norms = [self._normalize_ss(x)
                         for x in widget.choices]
        self.ss_map = { }


    def select(self, ss):
        gp_widget = self.widget.gp_widget
        if ss in self.ss_strs:
            gp_widget.set_value(ss)
        elif ss in self.ss_map:
            gp_widget.set_value(self.ss_map[ss])
        else:
            try:
                norm = self._normalize_ss(ss)
                # Aperture isn't linear, but this will be fine.
                i, v = find_nearest(self.ss_norms, norm,
                                    distance=ss_stops)
                closest_ss = self.ss_strs[i]
                logging.info(f"Closest shutter speed: {closest_ss}")
                self.ss_map[ss] = closest_ss
                gp_widget.set_value(closest_ss)
            except ValueError:
                logging.error(f"Cannot set shutter speed to {ss}")


    def _normalize_ss(self, ss):
        """Normalize ss, e.g. 1/2 to 0.5"""

        multiplier = 1
        if ss.endswith('s') or ss.endswith('"'):
            ss = ss[:-1]
        elif ss.endswith('m'):
            multiplier = 60
            ss = ss[:-1]

        try:
            match ss.split('/', maxsplit=2):
                case [den]:
                    return float(den) * multiplier
                case [num, den]:
                    return float(num) / float(den)
                case _:
                    logging.error(f"Cannot handle shutter speed {ss}")
        except ValueError:
            logging.error(f"Could not handle shutter speed {ss}")

        return None


class CameraConfig:
    """Decorate a gp.widget object"""

    def __init__(self, gp_widget):
        self.gp_widget = gp_widget
        self.widget = Widget(gp_widget)
        self.iso_ctrl = None
        self.aperture_ctrl = None
        self.shutterspeed_ctrl = None
        self._populate()


    def _populate(self):
        def check_widget(widget):

            if widget.name in ISO_KEYWORDS:
                logging.info(f"Found iso widget {widget.name}")
                self.iso_ctrl = IsoController(widget)
            elif widget.name in APERTURE_KEYWORDS:
                logging.info(f"Found aperture widget {widget.name}")
                self.aperture_ctrl = ApertureController(widget)
            elif widget.name in SHUTTER_SPEED_KEYWORDS:
                logging.info(f"Found shutter speed widget {widget.name}")
                self.shutterspeed_ctrl = ShutterSpeedController(widget)
            for child in widget.children:
                check_widget(child)

        check_widget(self.widget)


    def dump(self):
        dump_widget(self.gp_widget)


class CameraInitFailed(Exception):
    
    def __init__(self, message):
        self.message = message


class Camera:
    """Decorates a gp.Camera object."""

    def __init__(self, model=None, port=None):
        self.gp_camera = gp.Camera()
        self._select(model, port)
        self.iso_ctrl = None
        self.aperture_ctrl = None
        self.shutterspeed_ctrl = None
        try:
            self.gp_camera.init()
        except gp.GPhoto2Error:
            # Hide the old exception when reporting this one.
            raise CameraInitFailed("No cameras detected") from None
        gp_widget = self.gp_camera.get_config()
        self.config = CameraConfig(gp_widget)

    def _select(self, model, port):
        """Creates a camera object given arguments."""

        # If no filters specified, don't filter.
        if not model and not port:
            logging.info("Selecting first camera")
            return

        # Load port data.
        ports = gp.PortInfoList()
        ports.load()

        # Load ability data.
        abilities_list = gp.CameraAbilitiesList()
        abilities_list.load()

        # Detect cameras.
        detected_cameras = abilities_list.detect(ports)

        matches = []
        for det_model, det_port in detected_cameras:
            if model and model in det_model:
                # Qualifies
                pass
            else:
                # Disqualified
                continue
            # Port checking is deferred until it's needed.
            # No disqualifications.
            matches.append((det_model, det_port))
        
        if not matches:
            error = "No connected cameras match"
            raise CameraInitFailed(error)

        if len(matches) > 1:
            error = "Camera model and/or port are not specific enough"
            raise CameraInitFailed(error)
        
        # Use the one match.
        model, port = matches[0]

        # Try to find the user's ports.
        port_idx = ports.lookup_path(port)
        abil_idx = abilities_list.lookup_model(model)

        logging.info(f"port index: {port_idx}")
        self.gp_camera.set_port_info(ports[port_idx])

        logging.info(f"model index: {abil_idx}")
        self.gp_camera.set_abilities(abilities_list[abil_idx])


    def close(self):
        """Releases the camera connection."""
        self.gp_camera.exit()


    def dump(self):
        """Prints a list of abilities and configuration settings."""
        # Abilities
        abilities = self.gp_camera.get_abilities()
        dump_abilities(abilities)

        # Config
        self.config.dump()


    def set_aperture(self, aperture: str):
        """Sets the aperture value for the next `apply_settings()` call."""
        logging.info(f"Setting aperture to \"{aperture}\"")
        self.config.aperture_ctrl.select(aperture)


    def set_shutter_speed(self, shutter: str):
        """Sets the shutter speed value for the next `apply_settings()` call."""
        logging.info(f"Setting shutter speed to \"{shutter}\"")
        self.config.shutterspeed_ctrl.select(shutter)


    def set_iso(self, iso: str):
        """Sets the iso for the next `apply_settings()` call."""
        logging.info(f"Setting iso to \"{iso}\"")
        self.config.iso_ctrl.select(iso)


    def apply_settings(self):
        """Applies exposure settings, updating the camera."""
        gp_widget = self.config.gp_widget
        self.gp_camera.set_config(gp_widget)


    def trigger_capture(self):
        """Trigger a capture and return immediately."""
        self.gp_camera.trigger_capture()


    def trigger_capture_and_wait(self, timeout=100):
        """Trigger a capture and wait for the camera to be ready again."""

        # timout is 1/1000 s (so 100 is 1/10 s)
        gp_camera = self.gp_camera
        gp_camera.trigger_capture()
        event = None
        # 1: timeout
        # 2: file added
        # 3: folder added
        # 4: capture complete
        # 5: file changed
        ends = [gp.GP_EVENT_CAPTURE_COMPLETE,
                gp.GP_EVENT_FILE_ADDED]
        while event not in ends:
            event, data = gp_camera.wait_for_event(timeout)


    def capture(self):
        """Capture an image, and wait for the file to be written."""
        self.gp_camera.capture(gp.GP_CAPTURE_IMAGE)


    def preview(self):
        """Retrieve an image of the camera's live view."""
        image = gp.CameraFile()
        self.gp_camera.capture_preview(image)
        return image


def _list_cameras():
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


# Subcommand handlers

def do_print(args):
    """Handle the `print` subcommand."""

    camera = Camera(args.model, args.port)
    camera.dump()
    camera.close()


def do_test(args):
    """Handle the `test` subcommand."""

    camera = Camera(args.model, args.port)

    # Apertures in a few different formats
    aps = [ '4', 'f/5.6', '1/8' ]

    # ISOs with some off-values to test nearness.
    isos = [ '125', '200', '401', '650' ]

    # Shutter speeds in a few different formats.
    sss = [ '1/30', str(1/16), '1/20', '1', '2s' ]

    # Number of shots per setting
    burst = 1

    # Move around `t1` and `t2` to time different things.
    timing = []

    for ap in aps:
        camera.set_aperture(ap)
        for iso in isos:
            camera.set_iso(iso)
            for ss in sss:
                print(f"Aperture {ap}, iso {iso}, ss {ss}")
                camera.set_shutter_speed(ss)
                camera.apply_settings()

                t1 = dt.datetime.now()
                for count in range(burst):
                    camera.trigger_capture_and_wait()
                    pass

                t2 = dt.datetime.now()
                timing.append(t2 - t1)

                time.sleep(0.5)

    camera.close()

    delta0 = dt.timedelta()
    print("Timing stats for whatever was being timed")
    print(f"tot: {sum(timing,start=delta0)}")
    print(f"avg: {sum(timing,start=delta0)/len(timing)}")
    print(f"min: {min(timing)}")
    print(f"max: {max(timing)}")


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
    c_test.set_defaults(function=do_test)

    # Subcommand: capture
    c_capture = subs.add_parser('capture',
                                parents=[common, camera, exposure],
                                help="take a quick capture")
    c_capture.add_argument('-b', '--burst', type=int,
                           help="number of shots to take")
    c_capture.add_argument('-d', '--delay', '--interval', type=float,
                           help="interval between shots")
    c_capture.set_defaults(function=do_capture)

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
            _list_cameras()
            return

        if args.function:
            args.function(args)
    except CameraInitFailed as ex:
        logging.error(ex.message)


if __name__ == '__main__':
    main()

