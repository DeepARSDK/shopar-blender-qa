from typing import Set
import bpy
import bmesh

from . import utils
from . import shopar_qa
from mathutils import Vector

hierarchy_parents = {
    "frame": "Model",
    "front_rim": "frame",
    "nose_pad_left": "frame",
    "nose_pad_right": "frame",
    "hinge_frame_right": "frame",
    "hinge_frame_left": "frame",
    "nose_bridge": "frame",
    "lenses": "Model",
    "lens_left": "lenses",
    "lens_right": "lenses",
    "rim_left": "lenses",
    "rim_right": "lenses",
    "temples": "Model",
    "temple_left": "temples",
    "temple_right": "temples",
    "temple_left_inner": "temple_left",
    "temple_left_outer": "temple_left",
    "temple_tip_inner_left": "temple_left",
    "temple_tip_outer_left": "temple_left",
    "hinge_temple_left": "temple_left",
    "screw_left": "temple_left",
    "temple_right_inner": "temple_right",
    "temple_right_outer": "temple_right",
    "temple_tip_inner_right": "temple_right",
    "temple_tip_outer_right": "temple_right",
    "hinge_temple_right": "temple_right",
    "screw_right": "temple_right",
}


def place_in_hierarchy(
    obj, name: str, context: bpy.types.Context, report = None
) -> Set[str]:
    if obj:
        if name in hierarchy_parents:
            obj.name = name
            parent_name = hierarchy_parents[name]
            parent_obj = bpy.data.objects.get(parent_name)
            if parent_obj:
                obj.parent = parent_obj
            else:
                frame_empty = bpy.data.objects.new(parent_name, None)
                bpy.context.scene.collection.objects.link(frame_empty)

                frame_empty.empty_display_size = 0.2
                frame_empty.empty_display_type = "PLAIN_AXES"
                frame_empty.rotation_mode = "QUATERNION"

                place_in_hierarchy(frame_empty, parent_name, context, report)
                obj.parent = frame_empty
        else:
            if report:
                report(
                    {"ERROR"},
                    f"Object '{name}' does not have a defined parent in the hierarchy",
                )
            return {"CANCELLED"}
    else:
        if report:
            report({"ERROR"}, "No active object selected")
        return {"CANCELLED"}

    return {"FINISHED"}


def move_temples(context: bpy.types.Context):
    for ob in context.selected_objects:
        ob.select_set(False)

    for side in ["left", "right"]:
        screw = bpy.data.objects[f"screw_{side}"]
        local_bbox_center = 0.125 * sum((Vector(b) for b in screw.bound_box), Vector())
        global_bbox_center = screw.matrix_world @ local_bbox_center  # type: ignore
        obj = bpy.data.objects[f"temple_{side}"]
        obj.select_set(False)
        utils.cleanup_location(obj)
        if len(shopar_qa.check_scale(obj, [])) > 0:
            return False
        if obj.location == global_bbox_center:
            continue
        if obj.location != Vector((0, 0, 0)):
            utils.cleanup_location(obj)

        obj.location = global_bbox_center
        for child in obj.children:
            child.location = -global_bbox_center
            child.select_set(True)

    bpy.ops.object.transform_apply(location=True)
    return True

def mirrorObjToRight(obj: bpy.types.Object, context: bpy.types.Context):
    new_obj: bpy.types.Object = obj.copy()
    new_obj.name = obj.name.replace('left', 'right')
    if obj.data:
        new_obj.data = obj.data.copy()
    new_obj.animation_data_clear()
    bpy.context.scene.collection.objects.link(new_obj)
    place_in_hierarchy(new_obj, new_obj.name, context)
    if new_obj.type == 'MESH':
        active_obj =  bpy.context.active_object
        bpy.context.view_layer.objects.active = new_obj
        bpy.ops.object.mode_set(mode='EDIT')

        me: bpy.types.Mesh = new_obj.data
        bm = bmesh.from_edit_mesh(me)
        for v in bm.verts:
            v.co.x *= -1
        bmesh.update_edit_mesh(me)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = active_obj
        
    new_obj.location = (-obj.location[0], obj.location[1], obj.location[2])


def mirrorObjToLeft(obj: bpy.types.Object, context: bpy.types.Context):
    new_obj: bpy.types.Object = obj.copy()
    new_obj.name = obj.name.replace('right', 'left')
    if obj.data:
        new_obj.data = obj.data.copy()
    new_obj.animation_data_clear()
    bpy.context.scene.collection.objects.link(new_obj)
    place_in_hierarchy(new_obj, new_obj.name, context)
    if new_obj.type == 'MESH':
        active_obj =  bpy.context.active_object
        bpy.context.view_layer.objects.active = new_obj
        bpy.ops.object.mode_set(mode='EDIT')

        me: bpy.types.Mesh = new_obj.data
        bm = bmesh.from_edit_mesh(me)
        for v in bm.verts:
            v.co.x *= -1
        bmesh.update_edit_mesh(me)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = active_obj
        
    new_obj.location = (-obj.location[0], obj.location[1], obj.location[2])


def mirrorLeftToRight(context:bpy.types.Context):
    left_temple_obj = bpy.data.objects['temple_left']
    mirrorObjToRight(left_temple_obj, context)
    for obj in left_temple_obj.children:
        mirrorObjToRight(obj, context)

def mirrorRightToLeft(context: bpy.types.Context):
    right_temple_obj = bpy.data.objects['temple_right']
    mirrorObjToLeft(right_temple_obj, context)
    for obj in right_temple_obj.children:
        mirrorObjToLeft(obj, context)