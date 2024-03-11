bl_info = {
    "name": "shopar_qa",
    "author": "ShopAR",
    "description": "Automatic QA check for ShopAR assets creation.",
    "blender": (2, 80, 0),
    "version": (0, 1, 0),
    "category": "Object",
}

from typing import Set
import bpy
from bpy.types import Context

from . import addon_updater_ops
from . import shopar_qa
from . import utils


class ShopAR_QA_Panel(bpy.types.Panel):
    bl_label = f"ShopAR QA v" + '.'.join(map(str, bl_info["version"]))
    bl_idname = "OBJECT_PT_shopar_qa"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ShopAR QA"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        addon_updater_ops.check_for_update_background()
        layout = self.layout
        # purge = layout.operator(operator="outliner.orphans_purge", text="Clean up")
        # purge.do_local_ids = True
        # purge.do_linked_ids = True
        # purge.do_recursive = True
        layout.operator("object.move_temples")
        # apply = layout.operator(operator="object.transform_apply")
        # apply.location=True
        if len(context.selected_objects) == 0:
            layout.label(text="Select an object to check")
            OBJECT_OT_QAGlassesOperator.report = {}
            return
        layout.label(text="QA Glasses for ShopAR:")
        layout.operator("object.qa_glasses")
        if OBJECT_OT_QAGlassesOperator.report:
            layout.separator()
            if (
                "temple_left" in context.scene.objects
                and "temple_right" in context.scene.objects
            ):
                layout.label(text="Test temple rotation")
                layout.prop(
                    context.scene.objects["temple_left"],
                    "rotation_quaternion",
                    index=3,
                    text="Left temple rotation",
                )
                layout.prop(
                    context.scene.objects["temple_right"],
                    "rotation_quaternion",
                    index=3,
                    text="Right temple rotation",
                )
            utils.print_report(self, context, OBJECT_OT_QAGlassesOperator.report)
            if len(OBJECT_OT_QAGlassesOperator.report["ERROR"]) > 0:
                layout.operator("object.copy_report")
        addon_updater_ops.update_notice_box_ui(self, context)


class OBJECT_OT_QAMoveOrigin(bpy.types.Operator):
    bl_idname = "object.move_temples"
    bl_label = "Move Temples to Screws"
    bl_description = "Move temple groups to the approximate location of screws."

    def execute(self, context: Context) -> Set[int] | Set[str]:
        shopar_qa.move_temples(context=context)
        self.report({"INFO"}, "Moved temples to screws")
        return {"FINISHED"}


class OBJECT_OT_QAGlassesOperator(bpy.types.Operator):
    bl_idname = "object.qa_glasses"
    bl_label = "QA Glasses model"
    bl_description = "QA Glasses for ShopAR"
    report: dict = {}

    def execute(self, context: Context) -> Set[int] | Set[str]:
        if len(context.selected_objects) == 0:
            return {"CANCELLED"}
        report = {}
        report = shopar_qa.check_model(context=context)
        self.__class__.report = report
        self.report({"INFO"}, "Finished automatic QA")
        return {"FINISHED"}


class OBJECT_OT_CopyReport(bpy.types.Operator):
    bl_idname = "object.copy_report"
    bl_label = "Copy errors"
    bl_description = "Copy errors from the panel"

    def execute(self, context: bpy.types.Context) -> Set[int] | Set[str]:
        text = "\n\n".join(
            [item for item in OBJECT_OT_QAGlassesOperator.report["ERROR"]]
        )
        utils.copy_to_clipboard(text)
        return {"FINISHED"}

@addon_updater_ops.make_annotations
class ShopARQAPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

	# Addon updater preferences.
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=3,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)
    def draw(self, context):
        layout = self.layout

        addon_updater_ops.update_settings_ui(self, context)


classes = (
    ShopAR_QA_Panel,
    OBJECT_OT_QAGlassesOperator,
    OBJECT_OT_CopyReport,
    OBJECT_OT_QAMoveOrigin,
    ShopARQAPreferences
)


def register():
    addon_updater_ops.register(bl_info)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)


def unregister():
    addon_updater_ops.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
