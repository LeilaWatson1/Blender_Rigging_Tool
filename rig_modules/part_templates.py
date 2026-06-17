import bpy
import math
from .build import _get_view3d_override, add_template, create_base_rig, create_bone, armatures_visible, update_rig_visibility


# Creates cylinder_latch and cylinder bones, sets up HIDE_follow_cylinder in the CTRL armature
# to drive DEF_cylinder's rotation independently of its latch movement.
# parent_bone_name controls where cylinder_latch is parented (use "local" when called from a template).
def create_cylinder_part(context, rig_name, parent_bone_name="root"):
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, "cylinder_latch", True, True,
                parent_bone_name=parent_bone_name, ctrl_radius=0.05, ctrl_axis='Y',
                bone_head=(0.0, 0.1, 0.15), bone_tail=(0.0, 0.2, 0.15),
                ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow',
                ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))

    create_bone(context, rig_name, "cylinder", True, True,
                parent_bone_name="cylinder_latch", ctrl_radius=0.05, ctrl_axis='Y',
                bone_head=(-0.15, 0.1, 0.2), bone_tail=(-0.15, 0.2, 0.2),
                ctrl_color=(0.0, 0.0, 0.8))

    def_obj  = bpy.data.objects.get(f"DEF_{rig_name}")
    ctrl_obj = bpy.data.objects.get(f"CTRL_{rig_name}")
    override = _get_view3d_override(context)

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    for constraint in def_obj.pose.bones["DEF_cylinder"].constraints:
        if constraint.type == 'COPY_TRANSFORMS':
            constraint.subtarget = "HIDE_follow_cylinder"
            break
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    follow_bone = ctrl_obj.data.edit_bones.new("HIDE_follow_cylinder")
    follow_bone.head = (0.0, 0.1, 0.2)
    follow_bone.tail = (0.0, 0.2, 0.2)
    follow_bone.parent = ctrl_obj.data.edit_bones["CTRL_cylinder_latch"]
    follow_bone.use_connect = False
    follow_bone.hide = True
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    follow_pose = ctrl_obj.pose.bones["HIDE_follow_cylinder"]
    copy_rot = follow_pose.constraints.new('COPY_ROTATION')
    copy_rot.target = ctrl_obj
    copy_rot.subtarget = "CTRL_cylinder"
    copy_rot.use_x = False
    copy_rot.use_y = True
    copy_rot.use_z = False
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    add_template(context, rig_name, "follow_cylinder", parent_bone="cylinder_latch",
                 bone_head=(0.0, 0.1, 0.2), bone_tail=(0.0, 0.2, 0.2))

    update_rig_visibility(context, rig_name)
