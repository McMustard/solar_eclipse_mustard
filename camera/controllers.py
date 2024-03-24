
# standard imports
import logging

# package imports
from .calculations import *


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
        """Selects the aperture, but does not apply it."""

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


class IsoController:
    """Select the iso setting."""
    
    def __init__(self, widget):
        self.widget = widget
        self.iso_strs = widget.choices
        self.iso_ints = [int(x) if x.isdigit() else None
                         for x in widget.choices]
        self.iso_map = { }


    def select(self, iso):
        """Selects the ISO, but does not apply it."""

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


class ShutterSpeedController:
    """Select the shutter speed, accepting different notations."""

    def __init__(self, widget):
        self.widget = widget
        self.ss_strs = widget.choices
        self.ss_norms = [self._normalize_ss(x)
                         for x in widget.choices]
        self.ss_map = { }


    def select(self, ss):
        """Selects the shutter speed, but does not apply it."""

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


