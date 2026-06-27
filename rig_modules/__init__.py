import bpy
from .build import (
    create_base_rig,
    add_bone,
    create_bone,
    add_template,
    armatures_visible,
    update_rig_visibility,
    restore_mode,
    _get_view3d_override,
    _unique_name,
    _apply_front_axis,
)
from .part_templates import create_cylinder_part
from .templates import create_revolver_template, create_pistol_template


# Moves CTRL/HIDE bones to match template positions, then moves DEF bones to follow their
# Copy Transforms targets, applying all template edits to the live rig.
def pose_update(context, rig_name):
    def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
    ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
    template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")
    if not template_obj:
        return

    override = _get_view3d_override(context)

    # Read head, tail, and roll from template edit bones — roll is only on EditBone,
    # not on the object-mode Bone, so we must enter edit mode to retrieve it.
    context.view_layer.objects.active = template_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    template_data = {
        eb.name[5:]: (eb.head.copy(), eb.tail.copy(), eb.roll)
        for eb in template_obj.data.edit_bones
        if eb.name.startswith("TEMP_")
    }
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    # CTRL pass: apply head, tail, and roll to each matching CTRL_ or HIDE_ bone.
    if ctrl_obj:
        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = ctrl_obj.data.edit_bones
        for bone_name, (head, tail, roll) in template_data.items():
            target = edit_bones.get(f"CTRL_{bone_name}") or edit_bones.get(f"HIDE_{bone_name}")
            if target:
                target.head = head
                target.tail = tail
                target.roll = roll
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    # DEF pass: move each DEF bone to its Copy Transforms target's world position and copy roll.
    if def_obj and ctrl_obj:
        bone_targets = {}
        for pose_bone in def_obj.pose.bones:
            for c in pose_bone.constraints:
                if c.type == 'COPY_TRANSFORMS':
                    bone_targets[pose_bone.name] = c.subtarget
                    break

        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        ctrl_data_bones = ctrl_obj.data.bones
        def_inv = def_obj.matrix_world.inverted()
        for def_bone_name, subtarget in bone_targets.items():
            ctrl_bone = ctrl_data_bones.get(subtarget)
            if not ctrl_bone:
                continue
            edit_bone = def_obj.data.edit_bones.get(def_bone_name)
            if edit_bone:
                edit_bone.head = def_inv @ (ctrl_obj.matrix_world @ ctrl_bone.head_local)
                edit_bone.tail = def_inv @ (ctrl_obj.matrix_world @ ctrl_bone.tail_local)
                part_name = def_bone_name[4:]  # strip "DEF_"
                if part_name in template_data:
                    edit_bone.roll = template_data[part_name][2]
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')
