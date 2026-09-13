"""Check tree contact on explicit nonplanar terrain and unsupported points."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tree_layout import ground_tree_rows
vertices=[(0,0,0),(10,0,0),(10,10,10),(0,10,0)]
faces=[(0,1,2),(0,2,3)]
count=len(bpy.data.meshes)
rows=ground_tree_rows([[7.5,2.5,9,0],[2.5,7.5,12,2,999]],vertices,faces)
assert rows==[[7.5,2.5,9,0,2.5],[2.5,7.5,12,2,2.5]],rows
assert len(bpy.data.meshes)==count
try:ground_tree_rows([[20,20,9,0]],vertices,faces)
except ValueError:pass
else:raise AssertionError('Unsupported tree point accepted')
assert len(bpy.data.meshes)==count
print('3 tree-ground cases passed: both terrain triangles and missing support',flush=True)
