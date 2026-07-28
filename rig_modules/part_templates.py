import bpy
import math
from .build import _get_view3d_override, add_template, create_base_rig, create_bone, create_bone_chain, armatures_visible, update_rig_visibility, _apply_front_axis, _resolve_def_parent

# Visibility-aware wrapper: makes all armatures visible, creates the bone, then restores visibility.
# rig_name: the rig to add the bone to.
# bone_name: the part name (without prefix).
# is_deforming: True to create a DEF_ bone in the export armature.
# has_control: True to create a CTRL_ bone and widget.
# **kwargs: forwarded to create_bone (parent_bone_name, ctrl_radius, widget_type, etc.).
def add_bone(context, rig_name, bone_name, is_deforming, has_control, **kwargs):
    armatures_visible(rig_name)
    create_bone(context, rig_name, bone_name, is_deforming, has_control, **kwargs)
    update_rig_visibility(context, rig_name)

# Creates cylinder_latch and cylinder bones, sets up a HIDE_follow bone in the CTRL armature
# to drive the cylinder's rotation independently of its latch movement.
# parent_bone_name controls where cylinder_latch is parented (use "local" when called from a template).
# base_name sets the root name for both bones: base_name_latch and base_name.
# front_axis controls whether bone positions are oriented toward +X or +Y.
# Returns the actual cylinder part name used, which may differ from base_name if duplicates exist.
def create_cylinder_part(context, rig_name, parent_bone_name="root", base_name="cylinder", front_axis=None):
    if front_axis is None:
        front_axis = context.scene.rig_tool.front_axis
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    ax = lambda c: _apply_front_axis(c, front_axis)

    latch_widget_rot_z = math.pi / 2 if front_axis == 'X' else -math.pi / 2
    latch_name = create_bone(context, rig_name, f"{base_name}_latch", True, True,
                             parent_bone_name=parent_bone_name, ctrl_radius=0.05,
                             ctrl_axis='X',
                             bone_head=(0.1, 0.0, 0.15), bone_tail=(0.2, 0.0, 0.15),
                             ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow',
                             ctrl_shape_rotation=math.pi, ctrl_widget_rotation_z=latch_widget_rot_z,
                             ctrl_color=(0.0, 0.0, 0.8))

    cyl_name = create_bone(context, rig_name, base_name, True, True,
                           parent_bone_name=latch_name, ctrl_radius=0.05,
                           ctrl_axis='Y',
                           bone_head=(0.1, 0.15, 0.2), bone_tail=(0.2, 0.15, 0.2),
                           ctrl_color=(0.0, 0.0, 0.8))

    def_obj  = bpy.data.objects.get(f"DEF_{rig_name}")
    ctrl_obj = bpy.data.objects.get(f"CTRL_{rig_name}")
    override = _get_view3d_override(context)

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    for constraint in def_obj.pose.bones[f"DEF_{cyl_name}"].constraints:
        if constraint.type == 'COPY_TRANSFORMS':
            constraint.subtarget = f"HIDE_follow_{cyl_name}"
            break
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    follow_bone = ctrl_obj.data.edit_bones.new(f"HIDE_follow_{cyl_name}")
    follow_bone.head = ax((0.1, 0.0, 0.2))
    follow_bone.tail = ax((0.2, 0.0, 0.2))
    follow_bone.parent = ctrl_obj.data.edit_bones[f"CTRL_{latch_name}"]
    follow_bone.use_connect = False
    follow_bone.hide = True
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.update()  # Let depsgraph register HIDE_follow_ before constraints reference it.

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    follow_pose = ctrl_obj.pose.bones[f"HIDE_follow_{cyl_name}"]
    copy_rot = follow_pose.constraints.new('COPY_ROTATION')
    copy_rot.target = ctrl_obj
    copy_rot.subtarget = f"CTRL_{cyl_name}"
    copy_rot.use_x = True
    copy_rot.use_y = True
    copy_rot.use_z = True
    ctrl_obj.pose.bones[f"CTRL_{cyl_name}"].cylinder_props.part_name = cyl_name
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    add_template(context, rig_name, f"follow_{cyl_name}", parent_bone=latch_name,
                 bone_head=ax((0.1, 0.0, 0.2)), bone_tail=ax((0.2, 0.0, 0.2)))

    update_rig_visibility(context, rig_name)
    return cyl_name


# Visibility-aware wrapper for bone chain creation.
# rig_name: the rig to add the chain to.
# base_name: root name for all chain bones.
# is_deforming: True to create DEF_ bones in the export armature.
# has_control: True to create CTRL_ bones and widgets.
# chain_length: number of bones in the chain.
# parent_bone_name: parent part name or "root".
# widget_type: shape for FK control widgets.
# fk_ik: 'FK', 'IK', or 'BOTH' — which control systems to build.
def add_bone_chain(context, rig_name, base_name, is_deforming, has_control, chain_length=2, parent_bone_name="root", widget_type='circle', fk_ik='BOTH'):
    armatures_visible(rig_name)
    create_bone_chain(context, rig_name, base_name, is_deforming, has_control,
                      chain_length=chain_length, parent_bone_name=parent_bone_name, widget_type=widget_type,
                      fk_ik=fk_ik)
    update_rig_visibility(context, rig_name)

# NOT FINISHED NEED TO ADD PANEL!
# Makes a chain of bones that follow a NurbsCurve via per-bone Follow Path constraints.
# Bones are unconnected so each slides independently along the curve, looping from end back to start.
# bone_amount sets the number of bones and the number of interior curve control points (total points = bone_amount + 2).
# curve_length sets the straight-line length of the curve along the front axis.
def create_bullet_feed(context, rig_name, bone_amount, curve_length, parent_bone_name="root", base_name="bullet_feed", front_axis=None):
    print("fin")
#     if front_axis is None:
#         front_axis = context.scene.rig_tool.front_axis
#     create_base_rig(context, rig_name)
#     armatures_visible(rig_name)

#     ax          = lambda c: _apply_front_axis(c, front_axis)
#     override    = _get_view3d_override(context)
#     bone_length = curve_length / bone_amount

#     # Create NurbsCurve with bone_amount interior points.
#     curve_data = bpy.data.curves.new(f"{rig_name}_{base_name}", type='CURVE')
#     curve_data.dimensions = '3D'
#     curve_obj  = bpy.data.objects.new(f"{rig_name}_{base_name}", curve_data)
#     rig_collection = bpy.data.collections.get(rig_name)
#     if rig_collection:
#         rig_collection.objects.link(curve_obj)

#     total_points = bone_amount
#     spline = curve_data.splines.new('NURBS')
#     spline.points.add(total_points - 1)
#     spacing = curve_length / (total_points - 1)
#     for i in range(total_points):
#         pos = ax((i * spacing, 0.0, 0.0))
#         spline.points[i].co = (*pos, 1.0)
#     spline.use_endpoint_u = True
#     spline.order_u = min(4, total_points)

#     # Build unconnected DEF_ bones — each slides along the curve independently.
#     def_obj = bpy.data.objects.get(f"DEF_{rig_name}")
#     if def_obj:
#         context.view_layer.objects.active = def_obj
#         with context.temp_override(**override):
#             bpy.ops.object.mode_set(mode='EDIT')

#         props     = context.scene.rig_tool
#         parent_eb = _resolve_def_parent(def_obj, parent_bone_name, props)
#         for i in range(bone_amount):
#             eb             = def_obj.data.edit_bones.new(f"DEF_{base_name}_{i + 1:03d}")
#             eb.head        = ax((i * bone_length, 0.0, 0.0))
#             eb.tail        = ax(((i + 1) * bone_length, 0.0, 0.0))
#             eb.parent      = parent_eb
#             eb.use_connect = False

#         with context.temp_override(**override):
#             bpy.ops.object.mode_set(mode='OBJECT')

#         context.view_layer.update()

#         # Add a Follow Path constraint to each bone, staggered evenly along the curve.
#         context.view_layer.objects.active = def_obj
#         with context.temp_override(**override):
#             bpy.ops.object.mode_set(mode='POSE')

#         for i in range(bone_amount):
#             pb = def_obj.pose.bones.get(f"DEF_{base_name}_{i + 1:03d}")
#             if pb:
#                 follow                    = pb.constraints.new('FOLLOW_PATH')
#                 follow.target             = curve_obj
#                 follow.use_fixed_location = True
#                 follow.offset_factor      = i / bone_amount

#         with context.temp_override(**override):
#             bpy.ops.object.mode_set(mode='OBJECT')

#     update_rig_visibility(context, rig_name)