import bpy
import bmesh
import math


# Rotates a 2D point (x, y) by angle radians around the origin.
def _rotate_2d(x, y, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (c * x - s * y, s * x + c * y)


# Maps a flat (x, y) coordinate onto a 3D axis plane (X, Y, or Z) and applies an offset.
def _apply_axis(x, y, axis, offset):
    ox, oy, oz = offset
    if axis == 'X':
        return (ox, x + oy, y + oz)
    elif axis == 'Y':
        return (x + ox, oy, y + oz)
    else:
        return (x + ox, y + oy, oz)


# Creates a wire circle mesh object in the given collection, used as a bone custom shape.
def create_circle_widget(name, collection, radius=1.0, vertices=32, axis='Z', offset=(0.0, 0.0, 0.0), shape_rotation=0.0):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    verts = []
    for i in range(vertices):
        angle = (2 * math.pi * i) / vertices
        c, s = math.cos(angle) * radius, math.sin(angle) * radius
        c, s = _rotate_2d(c, s, shape_rotation)
        verts.append(bm.verts.new(_apply_axis(c, s, axis, offset)))

    bm.verts.ensure_lookup_table()
    for i in range(vertices):
        bm.edges.new((verts[i], verts[(i + 1) % vertices]))

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# Creates a wire arc with arrowheads at both ends, used as a bone custom shape for single-axis rotation controls.
def create_arc_arrow_widget(name, collection, radius=1.0, axis='Z', offset=(0.0, 0.0, 0.0), shape_rotation=0.0):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    arc_segments = 20
    start_angle = math.radians(25)
    end_angle   = math.radians(155)
    arrow_size  = radius * 0.2
    barb_angle  = math.radians(35)

    def add_vert(x, y):
        rx, ry = _rotate_2d(x, y, shape_rotation)
        return bm.verts.new(_apply_axis(rx, ry, axis, offset))

    def add_arrowhead(tip_vert, tip_x, tip_y, dir_x, dir_y):
        bx, by = -dir_x, -dir_y
        c, s = math.cos(barb_angle), math.sin(barb_angle)
        b1 = add_vert(tip_x + (c * bx - s * by) * arrow_size,
                      tip_y + (s * bx + c * by) * arrow_size)
        b2 = add_vert(tip_x + (c * bx + s * by) * arrow_size,
                      tip_y + (-s * bx + c * by) * arrow_size)
        bm.edges.new((tip_vert, b1))
        bm.edges.new((tip_vert, b2))

    # Build arc
    arc_verts = []
    for i in range(arc_segments + 1):
        t = i / arc_segments
        a = start_angle + t * (end_angle - start_angle)
        arc_verts.append(add_vert(math.cos(a) * radius, math.sin(a) * radius))

    for i in range(arc_segments):
        bm.edges.new((arc_verts[i], arc_verts[i + 1]))

    # Arrowhead at start pointing CW
    a = start_angle
    add_arrowhead(arc_verts[0],
                  math.cos(a) * radius, math.sin(a) * radius,
                  math.sin(a), -math.cos(a))

    # Arrowhead at end pointing CCW
    a = end_angle
    add_arrowhead(arc_verts[-1],
                  math.cos(a) * radius, math.sin(a) * radius,
                  -math.sin(a), math.cos(a))

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# Creates a wire circle with four outward arrows, used as a bone custom shape for multi-directional controls like root.
def create_circle_arrow_widget(name, collection, radius=1.0, axis='Z', offset=(0.0, 0.0, 0.0), shape_rotation=0.0):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    circle_verts = 32
    arrow_length = radius * 0.5
    barb_size    = radius * 0.2
    barb_angle   = math.radians(35)

    def add_vert(x, y):
        rx, ry = _rotate_2d(x, y, shape_rotation)
        return bm.verts.new(_apply_axis(rx, ry, axis, offset))

    # Circle
    verts = []
    for i in range(circle_verts):
        angle = (2 * math.pi * i) / circle_verts
        verts.append(add_vert(math.cos(angle) * radius, math.sin(angle) * radius))

    for i in range(circle_verts):
        bm.edges.new((verts[i], verts[(i + 1) % circle_verts]))

    # Four outward arrows at 0, 90, 180, 270 degrees
    c_barb, s_barb = math.cos(barb_angle), math.sin(barb_angle)
    for i in range(4):
        a = math.pi / 2 * i
        dx, dy = math.cos(a), math.sin(a)

        base_x, base_y = dx * radius, dy * radius
        tip_x,  tip_y  = dx * (radius + arrow_length), dy * (radius + arrow_length)

        bx, by = -dx, -dy
        b1x = tip_x + (c_barb * bx - s_barb * by) * barb_size
        b1y = tip_y + (s_barb * bx + c_barb * by) * barb_size
        b2x = tip_x + (c_barb * bx + s_barb * by) * barb_size
        b2y = tip_y + (-s_barb * bx + c_barb * by) * barb_size

        base_v  = add_vert(base_x, base_y)
        tip_v   = add_vert(tip_x,  tip_y)
        barb1_v = add_vert(b1x, b1y)
        barb2_v = add_vert(b2x, b2y)

        bm.edges.new((base_v, tip_v))
        bm.edges.new((tip_v, barb1_v))
        bm.edges.new((tip_v, barb2_v))

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# Creates a straight line with arrowheads at both ends, used as a bone custom shape for linear slide controls.
def create_double_arrow_widget(name, collection, length=0.1, axis='Z', offset=(0.0, 0.0, 0.0), shape_rotation=0.0):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    half       = length / 2
    barb_size  = length * 0.15
    barb_angle = math.radians(35)

    def add_vert(x, y):
        rx, ry = _rotate_2d(x, y, shape_rotation)
        return bm.verts.new(_apply_axis(rx, ry, axis, offset))

    def add_arrowhead(tip_vert, tip_x, tip_y, dir_x, dir_y):
        bx, by = -dir_x, -dir_y
        c, s = math.cos(barb_angle), math.sin(barb_angle)
        b1 = add_vert(tip_x + (c * bx - s * by) * barb_size,
                      tip_y + (s * bx + c * by) * barb_size)
        b2 = add_vert(tip_x + (c * bx + s * by) * barb_size,
                      tip_y + (-s * bx + c * by) * barb_size)
        bm.edges.new((tip_vert, b1))
        bm.edges.new((tip_vert, b2))

    left_v  = add_vert(-half, 0.0)
    right_v = add_vert( half, 0.0)
    bm.edges.new((left_v, right_v))

    add_arrowhead(left_v,  -half, 0.0, -1.0, 0.0)
    add_arrowhead(right_v,  half, 0.0,  1.0, 0.0)

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj
