import pytest
import os
import sys

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

def test_get_vertices_invalid_file():
    # Test with non-existent file?
    # Or create a malformed csv
    pass
