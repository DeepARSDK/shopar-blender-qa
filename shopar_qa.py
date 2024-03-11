from typing import Set
import bpy
from mathutils import Vector, Matrix
import difflib

allowed_groups = ["frame", "lenses", "temples"]
temple_names = ["temple_left", "temple_right"]
allowed_nodes = {
    "frame": [
        "front_rim",
        "nose_pad_left",
        "nose_pad_right",
        "hinge_frame_right",
        "hinge_frame_left",
        "nose_bridge",
    ],
    "lenses": ["lens_left", "lens_right", "rim_left", "rim_right"],
    "temples": {
        "temple_left": [
            "temple_left_inner",
            "temple_left_outer",
            "temple_tip_inner_left",
            "temple_tip_outer_left",
            "hinge_temple_left",
            "screw_left",
        ],
        "temple_right": [
            "temple_right_inner",
            "temple_right_outer",
            "temple_tip_inner_right",
            "temple_tip_outer_right",
            "hinge_temple_right",
            "screw_right",
        ],
    },
}
obligatory_names = {
    "frame",
    "lenses",
    "temples",
    "temple_left",
    "temple_right",
    "front_rim",
    "lens_left",
    "lens_right",
    "temple_left_outer",
    "temple_right_outer",
}


def check_names(obj: bpy.types.Object):
    output = []
    obligatory_names_left = set(obligatory_names)

    def invalidate(name, possible):
        fix = difflib.get_close_matches(name, possible, 1)
        return f'3.1 Invalid name: "{name}"' + (
            f', did you mean "{fix[0]}"?' if len(fix) > 0 else ""
        )

    for group in obj.children:
        obligatory_names_left.discard(group.name)

        if group.name not in allowed_groups:
            output.append(
                invalidate(group.name, allowed_groups)
                + f' Skipping the check of children of "{group.name}".'
            )
            continue
        if group.name == "temples":
            for temples_group in group.children:
                obligatory_names_left.discard(temples_group.name)

                if temples_group.name not in temple_names:
                    output.append(
                        invalidate(temples_group.name, temple_names)
                        + f' Skipping the check of children of "{temples_group.name}".'
                    )
                    continue
                for node in temples_group.children:
                    obligatory_names_left.discard(node.name)

                    if node.name not in allowed_nodes[group.name][temples_group.name]:
                        if not node.name.startswith("misc_"):
                            output.append(
                                invalidate(
                                    node.name,
                                    allowed_nodes[group.name][temples_group.name],
                                )
                            )
        else:
            for node in group.children:
                obligatory_names_left.discard(node.name)

                if node.name not in allowed_nodes[group.name]:
                    if not node.name.startswith("misc_"):
                        output.append(invalidate(node.name, allowed_nodes[group.name]))

    if len(obligatory_names_left) > 0:
        for obligatory_name in obligatory_names_left:
            output.append(f"3.1 Missing node {obligatory_name}")

    return output


def check_faces(obj):
    num_triangles_total = 0
    num_ngons_total = 0

    if obj.type == "MESH":
        for poly in obj.data.polygons:
            if len(poly.vertices) == 3:
                num_triangles_total += 1
            elif len(poly.vertices) > 3:
                num_ngons_total += 1

    for child in obj.children:
        a, b = check_faces(child)
        num_triangles_total += a
        num_ngons_total += b

    return num_triangles_total, num_ngons_total


def count_materials(obj, unique_materials: Set):
    # Recursively count materials in children
    if obj.type == "MESH":
        for slot in obj.material_slots:
            if slot.material is not None:
                unique_materials.add(slot.material)
    else:
        for child in obj.children:
            count_materials(child, unique_materials)

    return len(unique_materials)


def check_scale(obj: bpy.types.Object, output):
    for child in obj.children:
        check_scale(child, output)
    if obj.scale != Vector((1, 1, 1)):
        output.append(f'2.1 Invalid scale {obj.scale} of object "{obj.name}"')
    return output


def check_location(obj: bpy.types.Object, output):
    for child in obj.children:
        check_location(child, output)
    if obj.location != Vector((0, 0, 0)) and obj.name not in temple_names:
        output.append(f'2.1 Invalid location {obj.location} of object "{obj.name}"')
    elif obj.location == Vector((0, 0, 0)) and obj.name in temple_names:
        output.append(f'3.3  Temple group "{obj.name}" location in world origin')
    return output


def check_uv(obj: bpy.types.Object, uv_maps: Set):
    if obj.type == "MESH" and isinstance(obj.data, bpy.types.Mesh):
        for uv_map in obj.data.uv_layers:
            uv_maps.add(uv_map.name)
    else:
        for child in obj.children:
            check_uv(child, uv_maps)

    return len(uv_maps)


def check_model(context: bpy.types.Context):
    report = {"ERROR": [], "INFO": [], "WARNING": [], "PASSED": []}
    obj = context.active_object
    if obj.parent is not None:
        while obj.parent is not None:
            obj = obj.parent
        report["WARNING"].append(
            f'Didn\'t select root node, running the check on the root parent "{obj.name[:20]}..."'
        )

    # 2.1
    scale_output = check_scale(obj, [])
    if len(scale_output) > 0:
        for error in scale_output:
            report["ERROR"].append(error)
    else:
        report["PASSED"].append(f"2.1 Scale of all nodes = 1")

    # 2.3
    location_output = check_location(obj, [])
    if len(location_output) > 0:
        for error in location_output:
            report["ERROR"].append(error)
    else:
        report["PASSED"].append(
            f"2.1/2.3 Origin of all nodes in (0,0,0), except temples"
        )

    # 3.1
    names_report = check_names(obj)
    if len(names_report) == 0:
        report["PASSED"].append("3.1 No invalid names, contains obligatory nodes")
        report["PASSED"].append("3.2 Temples groups existing")
    else:
        for name in names_report:
            report["ERROR"].append(name)

    num_triangles, num_ngons = check_faces(obj)

    # 3.12
    if num_triangles > 20_000:
        report["ERROR"].append(f"3.12 Number of triangles too big: {num_triangles}")
    else:
        report["PASSED"].append(f"3.12 Number of triangles <20k: {num_triangles}")

    # 3.13
    if num_ngons > 0:
        report["ERROR"].append(f"3.13 Number of ngons >0: {num_ngons}")
    else:
        report["PASSED"].append("3.13. All faces are triangles")

    # 4.1
    num_uv_maps = check_uv(obj, set())
    if num_uv_maps > 1:
        report["ERROR"].append(f"4.1 Number of UV maps >1: {num_uv_maps}")
    else:
        report["PASSED"].append("4.1 Number of UV maps: 1")

    # 5.12
    num_materials = count_materials(obj, set())
    if num_materials != 1:
        report["ERROR"].append(f"5.12 Number of materials: {num_materials}")
    else:
        report["PASSED"].append(f"5.12 Number of materials: {num_materials}")
    return report


def update_children(obj, vector):
    if obj.type == "MESH" and isinstance(obj.data, bpy.types.Mesh):
        obj.location = -vector
    else:
        for c in obj.children:
            update_children(c, vector)


def move_temples(context: bpy.types.Context):
    for ob in bpy.context.selected_objects:
        ob.select_set(False)

    for side in ["left", "right"]:
        screw = bpy.data.objects[f"screw_{side}"]
        local_bbox_center = 0.125 * sum((Vector(b) for b in screw.bound_box), Vector())
        global_bbox_center = screw.matrix_world @ local_bbox_center
        obj = bpy.data.objects[f"temple_{side}"]
        obj.select_set(False)
        if obj.location == global_bbox_center:
            continue

        obj.location = global_bbox_center
        for child in obj.children:
            child.location = -global_bbox_center
            child.select_set(True)

    bpy.ops.object.transform_apply(location=True)
