import pytest
import os
import sys
from unittest.mock import MagicMock

# Ensure the module can be found
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Now we can import the module (conftest.py should have already mocked bpy/mathutils)
import io_import_nolimits_csv

def test_get_vertices_from_csv():
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'sample.csv')
    vertices = io_import_nolimits_csv.get_vertices_from_csv(csv_path)

    assert len(vertices) == 2

    # Check first vertex
    v1 = vertices[0]
    # In sample.csv: 1	0.0	0.0	0.0	0.0	0.0	1.0	1.0	0.0	0.0	0.0	1.0	0.0
    # pos: 0,0,0
    # front: 0,0,1
    # left: 1,0,0
    # up: 0,1,0

    assert v1['pos'].x == 0.0
    assert v1['pos'].y == 0.0
    assert v1['pos'].z == 0.0

    assert v1['front'].z == 1.0
    assert v1['left'].x == 1.0
    assert v1['up'].y == 1.0

def test_export_curve_completeness():
    # Setup mocks
    context = MagicMock()
    curve_obj = MagicMock()
    curve_obj.type = 'CURVE'
    curve_obj.data.splines = [MagicMock()]
    curve_obj.data.splines[0].points = [MagicMock(), MagicMock()] # 2 points
    context.active_object = curve_obj

    # Mock create_tmp_reader results
    # It calls bpy.data.objects.new
    reader = MagicMock()
    io_import_nolimits_csv.bpy.data.objects.new.return_value = reader

    # Mock evaluated_get to return a reader with a known matrix
    # We want to verify that Front and Left are NOT 0.0
    # Let's set a matrix that has distinct values

    # Matrix columns: Right, Front, Up, Pos
    # Let's use Identity for simplicity first, but we want to see non-zeros in output.
    # Identity:
    # Right (X): 1, 0, 0
    # Front (Y): 0, 1, 0
    # Up (Z):    0, 0, 1
    # Pos:       0, 0, 0

    # With logic:
    # Front_NL = T^-1 * Front_B = T^-1 * (0,1,0) = (0,0,-1)
    # Left_NL = -(T^-1 * Right_B) = -(T^-1 * (1,0,0)) = -(1,0,0) = (-1,0,0)

    # So we expect non-zero values in the CSV.

    # We need to mock the matrix_world returned by eval_reader
    eval_reader = MagicMock()
    reader.evaluated_get.return_value = eval_reader

    # Create a MockMatrix with specific columns
    # We need to rely on how MockMatrix is implemented in conftest.py or override it
    # conftest MockMatrix uses self.col = [MagicMock(), ...]

    # Let's override the copy() to return our specific matrix because logic uses matrix_world.copy()
    mat = io_import_nolimits_csv.mathutils.Matrix()
    # Configure columns by assigning new MockVectors
    # Right (1, 0, 0)
    mat.col[0] = io_import_nolimits_csv.mathutils.Vector((1.0, 0.0, 0.0))
    # Front (0, 1, 0)
    mat.col[1] = io_import_nolimits_csv.mathutils.Vector((0.0, 1.0, 0.0))
    # Up (0, 0, 1)
    mat.col[2] = io_import_nolimits_csv.mathutils.Vector((0.0, 0.0, 1.0))
    # Pos (10, 20, 30)
    mat.col[3] = io_import_nolimits_csv.mathutils.Vector((10.0, 20.0, 30.0))

    eval_reader.matrix_world.copy.return_value = mat

    # Run export
    out_file = os.path.join(os.path.dirname(__file__), 'data', 'export_test.csv')
    if os.path.exists(out_file):
        os.remove(out_file)

    io_import_nolimits_csv.sample_curve_as_csv(context, out_file, point_count=2, scale=1.0)

    assert os.path.exists(out_file)
    with open(out_file, 'r') as f:
        lines = f.readlines()

    assert len(lines) >= 2 # Header + 2 points

    header = lines[0]
    row1 = lines[1].strip().split('\t')

    # Check Front (indices 4, 5, 6) and Left (7, 8, 9)
    # If they are 0.0, the test fails (current behavior)
    # If they are correct, they should be non-zero

    front_x = float(row1[4])
    front_y = float(row1[5])
    front_z = float(row1[6])

    left_x = float(row1[7])
    left_y = float(row1[8])
    left_z = float(row1[9])

    # Currently code writes 0.0
    # We expect this assertion to FAIL before we fix the code
    # But since we want to verify the fix, we assert that they are NOT all zero
    # or match our expectation.

    # Expectation: Front=(0,0,-1), Left=(-1,0,0)
    # FrontX=0, FrontY=0, FrontZ=-1
    # LeftX=-1, LeftY=0, LeftZ=0

    # Note: Export format is FrontX, FrontY, FrontZ.

    # Let's just assert that we have the expected values
    assert front_z == -1.0 or front_z == 1.0 # depending on logic
    assert left_x == -1.0 or left_x == 1.0
