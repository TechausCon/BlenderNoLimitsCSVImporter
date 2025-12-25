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

    def __sub__(self, other):
        return MockVector([a - b for a, b in zip(self._data, other._data)])

    def __mul__(self, other):
        if isinstance(other, (int, float)):
             return MockVector([a * other for a in self._data])
        return 0.0

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return self.__mul__(other)
        return 0.0

    @property
    def length(self):
        return sum(x**2 for x in self._data) ** 0.5

    @property
    def length_squared(self):
        return sum(x**2 for x in self._data)

    def normalized(self):
        l = self.length
        if l == 0:
            return MockVector([0.0]*len(self._data))
        return MockVector([x/l for x in self._data])

    def normalize(self):
        l = self.length
        if l != 0:
            self._data = [x/l for x in self._data]
        return None

    def dot(self, other):
        return sum(a * b for a, b in zip(self._data, other._data))

    def cross(self, other):
         # assuming 3d
         x1, y1, z1 = self._data
         x2, y2, z2 = other._data
         return MockVector([
             y1*z2 - z1*y2,
             z1*x2 - x1*z2,
             x1*y2 - y1*x2
         ])

    def rotation_difference(self, other):
        # Return identity matrix mock or something that works with @ normal
        # normal is a vector.
        # quat @ normal -> vector
        # let's return a MockMatrix that acts as identity for now
        return MockMatrix()

    def __matmul__(self, other):
        # dot product or matrix multiplication
        return 0.0

    def __neg__(self):
        return MockVector([-x for x in self._data])

class MockMatrix:
    def __init__(self, rows=None):
        self.rows = rows
        # Initialize columns as MockVectors instead of MagicMocks to support -operator
        self.col = [MockVector([0.0, 0.0, 0.0]) for _ in range(4)]

    def __matmul__(self, other):
        if isinstance(other, MockVector):
            # Very basic matrix vector multiplication mock
            # If identity matrix-ish (TO_BLENDER_COORDINATES), we might want to approximate it?
            # But here we don't know the content of self.rows easily unless we initialized it.

            # If we know it is TO_BLENDER_COORDINATES:
            # ((1.0, 0.0, 0.0),
            #  (0.0, 0.0, -1.0),
            #  (0.0, 1.0, 0.0))
            # (x, y, z) -> (x, -z, y)

            # Since we only use one matrix in the code essentially, we can hack it here or make it generic?
            # Let's make it generic if we can.

            if hasattr(self, '_is_to_blender') and self._is_to_blender:
                 x, y, z = other.x, other.y, other.z
                 return MockVector([x, -z, y])

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

# Helper to identify our matrix
def MockMatrixConstructor(rows=None):
    m = MockMatrix(rows)
    if rows and len(rows) == 3 and rows[0][0] == 1.0 and rows[1][2] == -1.0:
         m._is_to_blender = True
    return m

mathutils.Matrix = MockMatrixConstructor
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
