import bpy
import subprocess
import platform


def print_report(panel: bpy.types.Panel, context, report):
    """Display report into the panel"""
    layout = panel.layout

    for category, icon, title in zip(
        ["WARNING", "PASSED", "ERROR"],
        ["ERROR", "CHECKMARK", "CANCEL"],
        ["Warnings", "Passed", "Failed"],
    ):
        if report[category]:
            layout.label(text=title)
            for report_item in report[category]:
                layout.label(text=report_item, icon=icon)


def copy_to_clipboard(text):
    if platform.system() == "Darwin":
        copy_keyword = "pbcopy"
    elif platform.system() == "Windows":
        copy_keyword = "clip"

    subprocess.run(copy_keyword, text=True, universal_newlines=True, input=text)


def cleanup_location(obj: bpy.types.Object):
    obj.select_set(True)
    for c in obj.children:
        c.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    for ob in bpy.context.selected_objects:
        ob.select_set(False)


def get_object_root(obj: bpy.types.Object) -> bpy.types.Object:
    if obj.parent is None:
        return obj
    else:
        return get_object_root(obj.parent)


mesh_name_items = [
    (None, "Frame"),
    ("front_rim", "Front Rim"),
    ("nose_bridge", "Nose Bridge"),
    ("nose_pad_left", "Left Nose Pad"),
    ("nose_pad_right", "Right Nose Pad"),
    ("hinge_frame_left", "Left Hinge Frame"),
    ("hinge_frame_right", "Right Hinge Frame"),
    (None, "Lenses"),
    ("lens_left", "Left Lens"),
    ("lens_right", "Right Lens"),
    ("rim_left", "Left Rim"),
    ("rim_right", "Right Rim"),
    (None, "Left Temple"),
    ("temple_left_inner", "Left Inner Temple"),
    ("temple_left_outer", "Left Outer Temple"),
    ("hinge_temple_left", "Left Hinge Temple"),
    ("screw_left", "Left Screw"),
    (None, "Right Temple"),
    ("temple_right_inner", "Right Inner Temple"),
    ("temple_right_outer", "Right Outer Temple"),
    ("hinge_temple_right", "Right Hinge Temple"),
    ("screw_right", "Right Screw"),
]
