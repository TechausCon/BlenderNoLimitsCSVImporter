# <pep8 compliant>
from contextvars import Token
import csv
import pathlib
import logging
from typing import List, Dict, Any, Tuple

import math
import bpy
import mathutils
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.types import Operator, Context, Object, Spline
from bpy_extras.io_utils import ImportHelper, ExportHelper

# Setup logging
logger = logging.getLogger(__name__)

TOOL_NAME = "NoLimits 2 Professional Track Data (.csv)"

bl_info = {
    "name": "NoLimits 2 Professional Track Data (.csv)",
    "author": "Daniel Hilpert",
    "version": (3, 0, 1),
    "blender": (2, 80, 0),
    "location": "File > Import > NoLimits 2 Professional Track Data (.csv)",
    "description": "Generates a curve object from NoLimits 2 Roller Coaster "
                   "Simulation Professional CSV data",
    "wiki_url": "https://github.com/bestdani/BlenderNoLimitsCSVImporter",
    "category": "Import-Export"
}

TO_BLENDER_COORDINATES = mathutils.Matrix(
    ((1.0, 0.0, 0.0),
     (0.0, 0.0, -1.0),
     (0.0, 1.0, 0.0))
)


def get_vertices_from_csv(file_path: pathlib.Path) -> List[Dict[str, mathutils.Vector]]:
    vertices = []

    with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
        treader = csv.reader(csv_file, delimiter='\t', quotechar='|')
        for line_num, row in enumerate(treader, start=1):
            if not row:
                continue
            try:
                # Ensure we have enough columns. The file format seems to expect at least 13 columns (indices 0 to 12)
                # No. (0), PosX (1), PosY (2), PosZ (3), FrontX (4), FrontY (5), FrontZ (6),
                # LeftX (7), LeftY (8), LeftZ (9), UpX (10), UpY (11), UpZ (12)
                if len(row) < 13:
                    # Skip header or malformed lines silently or log debug
                    continue

                vertices.append(
                    {
                        'pos': mathutils.Vector(
                            (float(row[1]), float(row[2]), float(row[3]))
                        ),
                        'front': mathutils.Vector(
                            (float(row[4]), float(row[5]), float(row[6]))
                        ),
                        'left': mathutils.Vector(
                            (float(row[7]), float(row[8]), float(row[9]))
                        ),
                        'up': mathutils.Vector(
                            (float(row[10]), float(row[11]), float(row[12]))
                        )
                    }
                )
            except ValueError:
                # Likely a header line or malformed number
                logger.debug(f"Skipping line {line_num} in CSV: {row}")
                continue
            except IndexError:
                logger.warning(f"Skipping line {line_num} in CSV due to missing columns: {row}")
                continue

    return vertices


def apply_vertex_positions(spline: Spline, vertices: List[Dict[str, mathutils.Vector]]):
    for i, vertex in enumerate(vertices):
        new_point = spline.points[i]
        new_point.co = (TO_BLENDER_COORDINATES @ vertex['pos']).to_4d()


def create_tmp_reader(context: Context, target_object: Object):
    reader = bpy.data.objects.new('tmp_curve_reader', None)
    reader.empty_display_type = 'ARROWS'
    context.layer_collection.collection.objects.link(reader)
    constraint = reader.constraints.new('FOLLOW_PATH')
    constraint.target = target_object
    constraint.use_curve_follow = True
    constraint.use_fixed_location = True
    return constraint, reader


def apply_tilt_values(vertices: List[Dict[str, mathutils.Vector]], spline_points):
    """
    Calculates and applies tilt angles for each vertex to align the curve normal
    with the expected up vector.
    This replaces the slow method of using a Follow Path constraint and scene updates.
    """
    if not vertices:
        return

    points = [TO_BLENDER_COORDINATES @ v['pos'] for v in vertices]
    target_ups = [TO_BLENDER_COORDINATES @ v['up'] for v in vertices]
    count = len(points)

    # Calculate geometric tangents for the Poly Spline
    tangents = []
    for i in range(count - 1):
        diff = points[i+1] - points[i]
        if diff.length_squared > 0:
            tangents.append(diff.normalized())
        else:
            # Use previous tangent or Z up if first
            tangents.append(mathutils.Vector((0, 0, 1)) if i == 0 else tangents[-1])

    if count > 1:
        tangents.append(tangents[-1])
    else:
        tangents.append(mathutils.Vector((0, 0, 1)))

    # Initialize Minimum Twist Normal (Default Blender Behavior)
    current_tangent = tangents[0]
    up_vec = mathutils.Vector((0, 0, 1))
    if abs(current_tangent.z) > 0.9999: # Parallel to Z
        up_vec = mathutils.Vector((1, 0, 0))

    # Calculate initial normal perpendicular to tangent
    normal = current_tangent.cross(up_vec).cross(current_tangent).normalized()

    for i in range(count):
        t_curr = tangents[i]

        if i > 0:
            t_prev = tangents[i-1]
            # Transport normal from prev to curr (Minimum Twist)
            if t_prev.dot(t_curr) < 0.999999:
                quat = t_prev.rotation_difference(t_curr)
                normal = quat @ normal

        # normal is now the "un-tilted" Blender normal
        target_up = target_ups[i]

        # Project target_up onto the plane perpendicular to t_curr
        target_up_proj = target_up - (target_up.dot(t_curr)) * t_curr
        if target_up_proj.length_squared > 0:
            target_up_proj.normalize()
        else:
            target_up_proj = normal

        # Calculate angle between 'normal' and 'target_up_proj'
        dot = normal.dot(target_up_proj)
        dot = max(-1.0, min(1.0, dot))
        angle = math.acos(dot)

        # Determine sign using cross product relative to tangent
        cross = normal.cross(target_up_proj)
        if cross.dot(t_curr) < 0:
            angle = -angle

        spline_points[i].tilt = angle


def create_empties(context: Context, name: str, vertices: List[Dict[str, mathutils.Vector]], parent_object: Object):
    collection = bpy.data.collections.new(name)
    context.scene.collection.children.link(collection)

    for vertex in vertices:
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = 'ARROWS'

        matrix_nl2 = mathutils.Matrix().to_3x3()
        matrix_nl2.col[0] = vertex['left']
        matrix_nl2.col[1] = vertex['up']
        matrix_nl2.col[2] = vertex['front']

        matrix_blender = (TO_BLENDER_COORDINATES @ matrix_nl2).to_4x4()
        matrix_blender.col[3] = (
                TO_BLENDER_COORDINATES @ vertex['pos']).to_4d()

        obj.matrix_world = matrix_blender

        collection.objects.link(obj)


def add_curve_from_csv(context: Context, file_path: str, import_raw_points: bool):
    file_path_obj = pathlib.Path(file_path)
    name = file_path_obj.stem

    vertices = get_vertices_from_csv(file_path_obj)

    if not vertices:
        # Should we raise an error or just return?
        # Returning FINISHED with a warning report might be better if invoked from operator
        return {'CANCELLED'}

    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.twist_mode = 'MINIMUM'
    curve_data.dimensions = '3D'

    spline = curve_data.splines.new('POLY')
    spline.resolution_u = 1
    spline.tilt_interpolation = 'LINEAR'
    spline.points.add(len(vertices) - 1)

    apply_vertex_positions(spline, vertices)

    curve_object = bpy.data.objects.new(name + " Object", curve_data)
    curve_object.location = (0, 0, 0)

    if import_raw_points:
        create_empties(context, name + " Raw", vertices, curve_object)

    context.scene.collection.objects.link(curve_object)
    apply_tilt_values(vertices, spline.points)

    return {'FINISHED'}


def sample_curve_as_csv(context: Context, file_path: str, point_count: int):
    file_path_obj = pathlib.Path(file_path)
    curve = context.active_object
    if not curve or curve.type != 'CURVE':
        return {'CANCELLED'}

    # Ensure point_count is valid
    if point_count == 0:
        if curve.data.splines:
             point_count = len(curve.data.splines[0].points)
        else:
             point_count = 0

    if point_count < 2:
         # Need at least 2 points to define a path properly for this export
         # or handle 1 point edge case
         pass

    largest_index = point_count - 1
    if largest_index <= 0:
        largest_index = 1

    constraint, reader = create_tmp_reader(context, curve)

    matrices = []
    for i in range(point_count):
        offset = i / largest_index
        constraint.offset_factor = offset
        dg = bpy.context.evaluated_depsgraph_get()
        bpy.context.scene.frame_current = 1
        eval_reader = reader.evaluated_get(dg)
        matrices.append(eval_reader.matrix_world.copy())

    bpy.data.objects.remove(reader, do_unlink=True)

    csv_header = '"No."\t"PosX"\t"PosY"\t"PosZ"\t' \
                 '"FrontX"\t"FrontY"\t"FrontZ"\t' \
                 '"LeftX"\t"LeftY"\t"LeftZ"\t' \
                 '"UpX"\t"UpY"\t"UpZ"'

    csv_rows = [csv_header]
    for i, m in enumerate(matrices):
        pos = m.col[3]
        up = m.col[2]
        csv_rows.append(
            f'{i + 1}\t{pos.x}\t{pos.z}\t{-pos.y}'
            f'\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t'
            f'{up.x}\t{up.z}\t{-up.y}'
        )

    csv_content = '\n'.join(csv_rows)
    with open(file_path_obj.with_suffix('.csv'), 'w') as f:
        f.write(csv_content)

    return {'FINISHED'}


class ImportNl2Csv(Operator, ImportHelper):
    """Imports coaster track splines as a curve"""
    bl_idname = "import_nl.csv_data"
    bl_label = TOOL_NAME

    filename_ext = ".csv"

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,
    )

    import_raw_points: BoolProperty(
        default=False,
        name="Import Raw Points (slow!)",
        description="Imports the raw points as empties. Attention, this can take several minutes for many vertices!",
    )

    def execute(self, context):
        return add_curve_from_csv(
            context, self.filepath, self.import_raw_points
        )


class ExportNl2Csv(Operator, ExportHelper):
    """Exports the active curve as a NoLimits 2 Professional compatible CSV
    file"""
    bl_idname = "export_nl.csv_data"
    bl_label = TOOL_NAME

    filename_ext = ".csv"

    point_count: IntProperty(
        name="Point Count",
        default=0,
        min=0,
    )

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        result = sample_curve_as_csv(context, self.filepath, self.point_count)
        if result != {'FINISHED'}:
            self.report(
                {'ERROR_INVALID_CONTEXT'}, 'No valid curve object selected'
            )
        return result


def menu_func_import(self, context):
    self.layout.operator(
        ImportNl2Csv.bl_idname,
        text=ImportNl2Csv.bl_label
    )


def menu_func_export(self, context):
    self.layout.operator(
        ExportNl2Csv.bl_idname,
        text=ExportNl2Csv.bl_label
    )


def register():
    bpy.utils.register_class(ImportNl2Csv)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.utils.register_class(ExportNl2Csv)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportNl2Csv)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(ExportNl2Csv)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.import_nl.csv_data('INVOKE_DEFAULT')
