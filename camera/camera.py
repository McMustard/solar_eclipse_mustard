# standard imports
import logging
import traceback as tb

# package imports
from .config import CameraConfig
from .dump import dump_abilities

# third-party imports
from gphoto2 import GPhoto2Error
import gphoto2 as gp


class CameraInitFailed(Exception):
    """Conveys that camera initialization failed, or no cameras were found."""
    
    def __init__(self, message):
        self.message = message


class Camera:
    """Decorates a gp.Camera object."""

    def __init__(self, model=None, port=None, delete=False):
        self.gp_camera = gp.Camera()
        self._select(model, port)
        self.iso_ctrl = None
        self.aperture_ctrl = None
        self.shutterspeed_ctrl = None
        self.delete_images = delete
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
            logging.info("Selecting first available camera")
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

        logging.debug(f"port index: {port_idx}")
        self.gp_camera.set_port_info(ports[port_idx])

        logging.debug(f"model index: {abil_idx}")
        self.gp_camera.set_abilities(abilities_list[abil_idx])


    def close(self):
        """Releases the camera connection."""
        try:
            self.gp_camera.exit()
        except GPhoto2Error as ex:
            logging.exception(ex)


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
        """Trigger a capture (only) and return immediately."""
        self.gp_camera.trigger_capture()


    def trigger_capture_and_wait(self, timeout=100, max_iters=10):
        """Trigger a capture, wait for the camera to be ready again, """
        """and delete the image if configured to."""

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
        iters = 0
        while event not in ends:
            try:
                event, data = gp_camera.wait_for_event(timeout)
            except GPhoto2Error as ex:
                tb.print_exc()
                break
            if event == gp.GP_EVENT_FILE_ADDED:
                if self.delete_images:
                    logging.info(f"Deleting image: {data.folder}/{data.name}")
                    gp_camera.file_delete(data.folder, data.name)
            iters += 1
            if iters >= max_iters: break


    def capture(self):
        """Capture an image, and wait for the file to be written."""
        self.gp_camera.capture(gp.GP_CAPTURE_IMAGE)
        # TODO delete the file here?


    def preview(self):
        """Retrieve an image of the camera's live view."""
        image = gp.CameraFile()
        self.gp_camera.capture_preview(image)
        return image


