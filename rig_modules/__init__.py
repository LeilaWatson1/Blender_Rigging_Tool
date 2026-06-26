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

    # CTRL pass: for each template bone, find its CTRL_ or HIDE_ bone and move it
    if ctrl_obj:
        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = ctrl_obj.data.edit_bones
        for bone in template_obj.data.bones:
            if not bone.name.startswith("TEMP_"):
                continue
            bone_name = bone.name[5:]
            target = edit_bones.get(f"CTRL_{bone_name}") or edit_bones.get(f"HIDE_{bone_name}")
            if target:
                target.head = bone.head_local.copy()
                target.tail = bone.tail_local.copy()
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    # DEF pass: move each DEF bone to its Copy Transforms target's world position
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
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')
