bl_info = {
    "name": "shopar_qa",
    "author": "ShopAR",
    "description": "Automatic QA check for ShopAR assets creation.",
    "blender": (2, 80, 0),
    "version": (0, 1, 6),
    "category": "Object",
}

from typing import Set
import bpy
from bpy.types import Context

from . import addon_updater_ops
from . import shopar_qa
from . import shopar_creation
from . import utils


def operator_execute(self, context: Context) -> Set[int] | Set[str]:
    root = utils.get_object_root(context.active_object)
    original_name = root.name
    root.name = "Model"
    result = shopar_creation.place_in_hierarchy(
        context.active_object, self.part, context=context, report=self.report
    )
    root.name = original_name
    return result


class ShopAR_Panel(bpy.types.Panel):
    bl_label = f"ShopAR Blender tools v" + ".".join(map(str, bl_info["version"]))
    bl_idname = "OBJECT_PT_shopar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ShopAR QA"

    def draw(self, context: Context):
        addon_updater_ops.check_for_update_background()
        addon_updater_ops.update_notice_box_ui(self, context)
        return


class ShopAR_Creation_Panel(bpy.types.Panel):
    bl_label = f"ShopAR Creation Tools"
    bl_idname = "OBJECT_PT_shopar_test"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ShopAR QA"
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "OBJECT_PT_shopar"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        # Move temples to screws button
        if (
            "temple_left" in context.scene.objects  # type: ignore
            and "screw_left" in context.scene.objects  # type: ignore
            and "temple_right" in context.scene.objects  # type: ignore
            and "screw_right" in context.scene.objects  # type: ignore
        ):
            layout.operator("object.move_temples")
            layout.separator()
        if "temple_left" in context.scene.objects: # type: ignore
            layout.operator('object.mirror_left_to_right')
        if "temple_right" in context.scene.objects: # type: ignore
            layout.operator('object.mirror_right_to_left')


        if context.active_object is not None:
            for item in utils.mesh_name_items:
                if item[0] is None:
                    layout.label(text=item[1])
                else:
                    layout.operator(operator=f"object.{item[0]}")
            

class ShopAR_QA_Panel(bpy.types.Panel):
    bl_label = f"ShopAR QA tools"
    bl_idname = "OBJECT_PT_shopar_qa"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ShopAR QA"
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "OBJECT_PT_shopar"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        # Temples rotation
        if (
            "temple_left" in context.scene.objects  # type: ignore
            and "temple_right" in context.scene.objects  # type: ignore
        ):
            layout.label(text="Test temple rotation (quaternion mode)")
            if context.scene.objects["temple_left"].rotation_mode == "QUATERNION":
                layout.prop(
                    context.scene.objects["temple_left"],
                    "rotation_quaternion",
                    index=3,
                    text="Left temple rotation",
                )
            if context.scene.objects["temple_right"].rotation_mode == "QUATERNION":
                layout.prop(
                    context.scene.objects["temple_right"],
                    "rotation_quaternion",
                    index=3,
                    text="Right temple rotation",
                )

        # QA glasses
        if len(context.selected_objects) == 0:  # type: ignore
            layout.label(text="Select an object to check")
            OBJECT_OT_QAGlassesOperator.QA_report = {}
            return

        layout.separator()
        layout.label(text="QA Glasses for ShopAR:")
        layout.operator("object.qa_glasses")
        if OBJECT_OT_QAGlassesOperator.QA_report:

            utils.print_report(self, context, OBJECT_OT_QAGlassesOperator.QA_report)
            if len(OBJECT_OT_QAGlassesOperator.QA_report["ERROR"]) > 0:
                layout.operator("object.copy_report")


class OBJECT_OT_MoveTemplesOperator(bpy.types.Operator):
    bl_idname = "object.move_temples"
    bl_label = "Move Temples to Screws"
    bl_description = "Move temple groups to the approximate location of screws."

    def execute(self, context: Context) -> Set[int] | Set[str]:
        if shopar_creation.move_temples(context=context):
            self.report({"INFO"}, "Moved temples to screws")
            return {"FINISHED"}
        else:
            self.report(
                {"ERROR"}, "Set scale of nodes in temple groups to (1,1,1) before continuing."
            )
            return {"CANCELLED"}


class OBJECT_OT_QAGlassesOperator(bpy.types.Operator):
    bl_idname = "object.qa_glasses"
    bl_label = "QA Glasses model"
    bl_description = "QA Glasses for ShopAR"
    QA_report: dict = {}

    def execute(self, context: Context) -> Set[int] | Set[str]:
        if len(context.selected_objects) == 0:  # type: ignore
            return {"CANCELLED"}
        QA_report = {}
        QA_report = shopar_qa.check_model(context=context)
        self.__class__.QA_report = QA_report
        self.report({"INFO"}, "Finished automatic QA")
        return {"FINISHED"}


class OBJECT_OT_CopyReportOperator(bpy.types.Operator):
    bl_idname = "object.copy_report"
    bl_label = "Copy errors"
    bl_description = "Copy errors from the panel"

    def execute(self, context: bpy.types.Context) -> Set[int] | Set[str]:
        text = "\n\n".join(
            [item for item in OBJECT_OT_QAGlassesOperator.QA_report["ERROR"]]
        )
        utils.copy_to_clipboard(text)
        return {"FINISHED"}

class OBJECT_OT_MirrorGlassesRightToLeft(bpy.types.Operator):
    bl_idname = "object.mirror_right_to_left"
    bl_label = "Mirror Right Temple To Left"
    bl_description = "Mirror right temple of glasses to the right. Components must be named after the ShopAR specification."
    def execute(self, context: Context) -> Set[int] | Set[str]:
        shopar_creation.mirrorRightToLeft(context=context)
        return {"FINISHED"}

class OBJECT_OT_MirrorGlassesLeftToRight(bpy.types.Operator):
    bl_idname = "object.mirror_left_to_right"
    bl_label = "Mirror Left Temple to Right"
    bl_description = "Mirror left components of glasses to right. Components must be named after the ShopAR specification."
    def execute(self, context: Context) -> Set[int] | Set[str]:
        shopar_creation.mirrorLeftToRight(context=context)
        return {"FINISHED"}
    

@addon_updater_ops.make_annotations
class ShopAR_QA_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # Addon updater preferences.
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
    )

    updater_interval_months = bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )

    updater_interval_days = bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=1,
        min=0,
        max=31,
    )

    updater_interval_hours = bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )

    updater_interval_minutes = bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout

        addon_updater_ops.update_settings_ui(self, context)


classes = [
    ShopAR_Panel,
    ShopAR_Creation_Panel,
    ShopAR_QA_Panel,
    OBJECT_OT_QAGlassesOperator,
    OBJECT_OT_CopyReportOperator,
    OBJECT_OT_MoveTemplesOperator,
    ShopAR_QA_Preferences,
    OBJECT_OT_MirrorGlassesLeftToRight,
    OBJECT_OT_MirrorGlassesRightToLeft,
]


def register():
    addon_updater_ops.register(bl_info)
    for item in utils.mesh_name_items:
        if item[0] is None:
            continue
        new_class = type(
            f"{item}Operator",
            (bpy.types.Operator,),
            {
                "bl_idname": f"object.{item[0]}",
                "bl_label": item[1],
                "part": item[0],
                # data members
                "execute": operator_execute,
            },
        )
        if new_class not in classes:
            classes.append(new_class)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)


def unregister():
    addon_updater_ops.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
