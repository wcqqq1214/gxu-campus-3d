"""Export-only removal must retain tiny valid faces, UVs and the editable mesh."""
import sys
import unittest
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_attributes import omit_zero_area_terrain_faces


class TerrainExportPruningTests(unittest.TestCase):
    def setUp(self):
        data=bpy.data.meshes.new('pruning-fixture')
        data.from_pydata([(0,0,0),(1,0,0),(2,0,0),
                          (0,1,0),(1,1,0),(0,2,0),
                          (0,3,0),(1e-8,3,0),(0,3,1e-8)],[],[(0,1,2),(3,4,5),(6,7,8)])
        data.update();uv=data.uv_layers.new(name='fixture-uv')
        for i,loop in enumerate(uv.data):loop.uv=(i/10,i/20)
        self.obj=bpy.data.objects.new('pruning-fixture',data)
        bpy.context.scene.collection.objects.link(self.obj);self.obj['layer']='terrain'
        self.original=data

    def tearDown(self):
        bpy.data.objects.remove(self.obj,do_unlink=True)
        bpy.data.meshes.remove(self.original)

    def face(self,mesh,index):
        face=mesh.polygons[index]
        return [(tuple(mesh.vertices[mesh.loops[i].vertex_index].co),
                 tuple(mesh.uv_layers.active.data[i].uv)) for i in face.loop_indices]

    def test_collapsed_only_and_valid_face_attributes_preserved(self):
        expected=[self.face(self.original,i) for i in [1,2]]
        count=len(bpy.data.meshes)
        with omit_zero_area_terrain_faces(self.obj) as removed:
            self.assertEqual(removed,1)
            self.assertEqual(len(self.obj.data.polygons),2)
            self.assertEqual([self.face(self.obj.data,i) for i in range(2)],expected)
        self.assertEqual(self.obj.data,self.original)
        self.assertEqual(len(self.original.polygons),3)
        self.assertEqual(len(bpy.data.meshes),count)

    def test_restore_on_export_error(self):
        count=len(bpy.data.meshes)
        with self.assertRaisesRegex(RuntimeError,'export failure'):
            with omit_zero_area_terrain_faces(self.obj):raise RuntimeError('export failure')
        self.assertEqual(self.obj.data,self.original)
        self.assertEqual(len(bpy.data.meshes),count)

    def test_other_layers_are_untouched(self):
        self.obj['layer']='roads'
        with omit_zero_area_terrain_faces(self.obj) as removed:
            self.assertEqual(removed,0)
            self.assertEqual(self.obj.data,self.original)

    def test_quantized_removal_preserves_valid_faces_uvs_and_source(self):
        # The fourth face fixes the domain. The last triangle is small but
        # survives the 18-bit grid; only face 2 collapses under quantization.
        vertices=[tuple(v.co) for v in self.original.vertices]
        vertices += [(-1,-1,-1),(3,4,-1),(3,4,1),
                     (0,2.5,0),(.0001,2.5,0),(0,2.5,.0001)]
        faces=[tuple(p.vertices) for p in self.original.polygons]+[(9,10,11),(12,13,14)]
        self.original.clear_geometry();self.original.from_pydata(vertices,[],faces);self.original.update()
        uv=self.original.uv_layers.active or self.original.uv_layers.new(name='fixture-uv')
        for i,loop in enumerate(uv.data):loop.uv=(i/10,i/20)
        expected=[self.face(self.original,i) for i in (1,3,4)]
        count=len(bpy.data.meshes)
        with omit_zero_area_terrain_faces(self.obj,position_quantization_bits=18) as removed:
            self.assertEqual(removed,2)
            self.assertEqual([self.face(self.obj.data,i) for i in range(3)],expected)
        self.assertIs(self.obj.data,self.original)
        self.assertEqual(len(self.original.polygons),5)
        self.assertEqual(len(bpy.data.meshes),count)

    def test_quantized_removal_cannot_shift_the_position_domain(self):
        # The tiny triangle owns the sole Y maximum. Retain it even though it
        # collapses, otherwise the remaining quantized coordinates could move.
        with omit_zero_area_terrain_faces(self.obj,position_quantization_bits=18) as removed:
            self.assertEqual(removed,1)
            self.assertEqual(len(self.obj.data.polygons),2)

    def test_quantized_cleanup_rejects_transforms_and_restores_on_error(self):
        from mathutils import Matrix
        self.obj.matrix_world=Matrix.Translation((1,0,0))
        with self.assertRaisesRegex(ValueError,'untransformed'):
            with omit_zero_area_terrain_faces(self.obj,position_quantization_bits=18):pass
        self.assertIs(self.obj.data,self.original)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TerrainExportPruningTests))
    if not result.wasSuccessful():raise AssertionError('Ground export pruning failed')
