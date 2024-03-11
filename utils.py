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
            layout.separator()
            layout.label(text=title)
            for report_item in report[category]:
                layout.label(text=report_item, icon=icon)


def copy_to_clipboard(text):
    if platform.system() == "Darwin":
        copy_keyword = "pbcopy"
    elif platform.system() == "Windows":
        copy_keyword = "clip"

    subprocess.run(copy_keyword, text=True, universal_newlines=True, input=text)
