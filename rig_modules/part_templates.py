import bpy
import math
from .build import _get_view3d_override, add_template, create_base_rig, create_bone, create_bone_chain, armatures_visible, update_rig_visibility, _apply_front_axis

# Visibility-aware wrapper: makes all armatures visible, creates the bone, then restores visibility.
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
    copy_rot.use_x = False
    copy_rot.use_y = True
    copy_rot.use_z = False
    ctrl_obj.pose.bones[f"CTRL_{cyl_name}"].cylinder_props.part_name = cyl_name
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    add_template(context, rig_name, f"follow_{cyl_name}", parent_bone=latch_name,
                bone_head=ax((0.1, 0.0, 0.2)), bone_tail=ax((0.2, 0.0, 0.2)))

    update_rig_visibility(context, rig_name)
    return cyl_name


# Visibility-aware wrapper for bone chain creation.
def add_bone_chain(context, rig_name, base_name, is_deforming, has_control, chain_length=2, parent_bone_name="root", widget_type='circle', fk_ik='BOTH'):
    armatures_visible(rig_name)
    create_bone_chain(context, rig_name, base_name, is_deforming, has_control,
                      chain_length=chain_length, parent_bone_name=parent_bone_name, widget_type=widget_type,
                      fk_ik=fk_ik)
    update_rig_visibility(context, rig_name)