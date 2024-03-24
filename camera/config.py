
# standard imports
import logging

# third-party imports
import gphoto2 as gp

# package imports
from .controllers import *


# Keywords for searching settings, to accommodate different makes.
ISO_KEYWORDS = [ 'iso' ]
APERTURE_KEYWORDS = [ 'aperture', 'f-number' ]
SHUTTER_SPEED_KEYWORDS = [ 'shutterspeed' ]


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


