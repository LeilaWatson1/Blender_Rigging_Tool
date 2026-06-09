import bpy
import bmesh
import math


def create_circle_widget(name, collection, radius=1.0, vertices=32, axis='Z'):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    verts = []
    for i in range(vertices):
        angle = (2 * math.pi * i) / vertices
        c, s = math.cos(angle) * radius, math.sin(angle) * radius
        if axis == 'X':
            v = (0.0, c, s)
        elif axis == 'Y':
            v = (c, 0.0, s)
        else:
            v = (c, s, 0.0)
        verts.append(bm.verts.new(v))

    bm.verts.ensure_lookup_table()
    for i in range(vertices):
        bm.edges.new((verts[i], verts[(i + 1) % vertices]))

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj
