from typing import Set
import bpy
from mathutils import Vector, Matrix
import difflib

from . import utils

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
    # TODO add required nose pads
    # "nose_pad_left",
    # "nose_pad_right",
    "lens_left",
    "lens_right",
    "temple_left_outer",
    "temple_right_outer",
}


def check_names(obj: bpy.types.Object) -> list:
    output = []
    obligatory_names_left = set(obligatory_names)

    def invalidate(name, possible):
        fix = difflib.get_close_matches(name, possible, 1)
        return f'Invalid name: "{name}"' + (
            f', did you mean "{fix[0]}"?' if len(fix) > 0 else ""
        )

    for group in obj.children:
        obligatory_names_left.discard(group.name)

        if group.name not in allowed_groups:
            output.append(
                invalidate(group.name, allowed_groups)
                + f' Skipping the check of potential children of "{group.name}".'
            )
            continue
        if group.name == "temples":
            for temples_group in group.children:
                obligatory_names_left.discard(temples_group.name)

                if temples_group.name not in temple_names:
                    output.append(
                        invalidate(temples_group.name, temple_names)
                        + f' Skipping the check of potential children of "{temples_group.name}".'
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
            output.append(f"Missing node {obligatory_name}")

    return output


def check_faces(obj) -> tuple[int, int]:
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


def count_materials(obj, unique_materials: Set) -> int:
    # Recursively count materials in children
    if obj.type == "MESH":
        for slot in obj.material_slots:
            if slot.material is not None:
                unique_materials.add(slot.material)
    else:
        for child in obj.children:
            count_materials(child, unique_materials)

    return len(unique_materials)


def check_scale(obj: bpy.types.Object, output: list) -> list:
    for child in obj.children:
        check_scale(child, output)
    if obj.scale != Vector((1, 1, 1)):
        output.append(f'Invalid scale {obj.scale} of object "{obj.name}"')
    return output


def check_location(obj: bpy.types.Object, output: list):
    for child in obj.children:
        check_location(child, output)
    # if obj.location != Vector((0, 0, 0)) and obj.name not in temple_names:
    #     output.append(f'2.1 Invalid location {obj.location} of object "{obj.name}"')
    if obj.location == Vector((0, 0, 0)) and obj.name in temple_names:
        output.append(f'Temple group "{obj.name}" location in world origin')
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
        obj = utils.get_object_root(obj)
        report["WARNING"].append(
            f'Didn\'t select root node, running the check on the root parent "{obj.name[:20]}..."'
        )

    # TODO only for root
    scale_output = check_scale(obj, [])
    if len(scale_output) > 0:
        for error in scale_output:
            report["ERROR"].append(error)
    else:
        report["PASSED"].append(f"2.1 Scale of all nodes = 1")

    # TODO only for root
    location_output = check_location(obj, [])
    if obj.location != Vector((0, 0, 0)) or len(location_output) > 0:
        if obj.location != Vector((0, 0, 0)):
            report["ERROR"].append(f"Root location {obj.location} not (0,0,0)")
        if len(location_output) > 0:
            for error in location_output:
                report["ERROR"].append(error)
    else:
        report["PASSED"].append(
            f"2.1/2.3 Origin of all nodes in (0,0,0), except temples"
        )

    # check naming and hierarchy
    names_report = check_names(obj)
    if len(names_report) == 0:
        report["PASSED"].append("No invalid names, contains obligatory nodes")
        report["PASSED"].append("Temples groups existing")
    else:
        for name in names_report:
            report["ERROR"].append(name)

    # only triangles and number of triangles
    MAX_NUM_TRIANGLES = 100_000

    num_triangles, num_ngons = check_faces(obj)
    if num_triangles > MAX_NUM_TRIANGLES:
        report["ERROR"].append(f"Number of triangles too big: {num_triangles}")
    else:
        report["PASSED"].append(
            f"Number of triangles <{MAX_NUM_TRIANGLES}: {num_triangles}"
        )

    if num_ngons > 0:
        report["ERROR"].append(f"Number of ngons >0: {num_ngons}")
    else:
        report["PASSED"].append("All faces are triangles")

    return report
