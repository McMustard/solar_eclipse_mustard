
# third-party imports
import gphoto2 as gp


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


