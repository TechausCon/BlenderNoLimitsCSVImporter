import sys
from unittest.mock import MagicMock

# --- Mock mathutils ---
class MockVector:
    def __init__(self, seq):
        self._data = list(seq)

    def __repr__(self):
        return f"Vector({self._data})"

    def __getitem__(self, i):
        return self._data[i]

    def __len__(self):
        return len(self._data)

    @property
    def x(self): return self._data[0]
    @property
    def y(self): return self._data[1]
    @property
    def z(self): return self._data[2]

    def to_4d(self):
        return MockVector(self._data + [1.0])

    def copy(self):
        return MockVector(self._data)

    def cross(self, other):
        return MockVector([0.0, 0.0, 0.0])

    def angle(self, other):
        return 0.0

    def __matmul__(self, other):
        # dot product or matrix multiplication
        return 0.0

class MockMatrix:
    def __init__(self, rows=None):
        self.rows = rows
        self.col = [MagicMock() for _ in range(4)]
        # Make col access return a MockVector-like object with xyz
        for c in self.col:
            c.xyz = MockVector([0.0, 0.0, 0.0])

    def __matmul__(self, other):
        if isinstance(other, MockVector):
            # Return a dummy vector result
            return MockVector([0.0]*len(other))
        if isinstance(other, MockMatrix):
            return MockMatrix()
        return self

    def to_3x3(self):
        return self

    def to_4x4(self):
        return self

    def copy(self):
        return MockMatrix()

mathutils = MagicMock()
mathutils.Vector = MockVector
mathutils.Matrix = MockMatrix
sys.modules['mathutils'] = mathutils

# --- Mock bpy ---
bpy = MagicMock()
bpy.props = MagicMock()
bpy.types = MagicMock()

# Mock properties
def MockProperty(default=None, **kwargs):
    return default

bpy.props.StringProperty = MockProperty
bpy.props.IntProperty = MockProperty
bpy.props.BoolProperty = MockProperty

# Define distinct classes for inheritance
class MockOperator:
    pass

bpy.types.Operator = MockOperator

sys.modules['bpy'] = bpy
sys.modules['bpy.props'] = bpy.props
sys.modules['bpy.types'] = bpy.types

# --- Mock bpy_extras ---
bpy_extras = MagicMock()
io_utils = MagicMock()

class MockImportHelper:
    pass

class MockExportHelper:
    pass

io_utils.ImportHelper = MockImportHelper
io_utils.ExportHelper = MockExportHelper
bpy_extras.io_utils = io_utils

sys.modules['bpy_extras'] = bpy_extras
sys.modules['bpy_extras.io_utils'] = io_utils
