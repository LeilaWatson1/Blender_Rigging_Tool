import bpy
import math
import mathutils
from .widgets import create_circle_widget, create_arc_arrow_widget, create_circle_arrow_widget


# Returns a unique name by checking existing rigs (name_type='rig') or parts (name_type='part'), appending _001, _002 etc. if needed.
def _unique_name(name_type, name, props=None):
    if name_type == 'rig':
        existing = {obj.name[4:] for obj in bpy.data.objects if obj.name.startswith("DEF_")}
    else:
        existing = {part.name for part in props.parts}
    if name not in existing:
        return name
    i = 1
    while f"{name}_{i:03d}" in existing:
        i += 1
    return f"{name}_{i:03d}"


# Appends a new entry to the parts list in the UI and moves it to sit directly under its parent.
def _add_part(context, part_name, parent_name=""):
    props = context.scene.rig_tool
    indent     = 0
    parent_idx = None
    for i, part in enumerate(props.parts):
        if part.name == parent_name:
            indent     = part.indent + 1
            parent_idx = i
            break
    item = props.parts.add()
    item.name        = part_name
    item.parent_name = parent_name
    item.indent      = indent

    if parent_idx is not None:
        new_idx    = len(props.parts) - 1
        insert_idx = parent_idx + 1
        for i in range(parent_idx + 1, new_idx):
            if props.parts[i].indent > props.parts[parent_idx].indent:
                insert_idx = i + 1
            else:
                break
        if insert_idx < new_idx:
            props.parts.move(new_idx, insert_idx)


# Rotates a coordinate tuple +90° around Z when front_axis is 'Y', converting X-native to Y-native.
def _apply_front_axis(coord, front_axis):
    x, y, z = coord
    return (-y, x, z) if front_axis == 'Y' else coord


# Swaps 'X' and 'Y' axis labels when front_axis is 'Y', leaving 'Z' unchanged.
def _apply_front_axis_str(axis, front_axis):
    if front_axis != 'Y':
        return axis
    return {'X': 'Y', 'Y': 'X'}.get(axis, axis)


# Returns a context override dict for the active VIEW_3D window, required by bpy.ops calls from the N-panel.
def _get_view3d_override(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {'window': window, 'area': area, 'region': region}
    return {}


# Sets all three armatures visible and unhides HIDE_ bones so they can be edited.
def armatures_visible(rig_name):
    for prefix in ("DEF_", "CTRL_", "TEMPLATE_"):
        obj = bpy.data.objects.get(f"{prefix}{rig_name}")
        if obj:
            obj.hide_viewport = False
    ctrl_obj = bpy.data.objects.get(f"CTRL_{rig_name}")
    if ctrl_obj:
        for bone in ctrl_obj.data.bones:
            if bone.name.startswith("HIDE_"):
                bone.hide = False


# Shows or hides armatures based on the current mode, and re-hides HIDE_ bones in Pose Mode.
def update_rig_visibility(context, rig_name):
    mode         = context.scene.rig_tool.mode
    def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
    ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
    template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")

    in_template_mode = (mode == 'TEMPLATE')

    if def_obj:      def_obj.hide_viewport      = in_template_mode
    if ctrl_obj:     ctrl_obj.hide_viewport     = in_template_mode
    if template_obj: template_obj.hide_viewport = not in_template_mode

    if ctrl_obj and not in_template_mode:
        for bone in ctrl_obj.data.bones:
            if bone.name.startswith("HIDE_"):
                bone.hide = True


# Creates a TEMP_ bone in the template armature at the given position, with optional parent/child linking.
def add_template(context, rig_name, bone_name, parent_bone=None, child_bone=None, bone_head=(0.0, 0.0, 0.0), bone_tail=(0.0, 0.1, 0.0)):
    template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")
    if not template_obj:
        return

    override = _get_view3d_override(context)
    TEMP_bone_name = f"TEMP_{bone_name}"

    context.view_layer.objects.active = template_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')

    edit_bones = template_obj.data.edit_bones
    new_bone = edit_bones.new(TEMP_bone_name)
    new_bone.head = bone_head
    new_bone.tail = bone_tail
    new_bone.use_connect = False

    if parent_bone:
        parent_TEMP_name = f"TEMP_{parent_bone}"
        if parent_TEMP_name in edit_bones:
            new_bone.parent = edit_bones[parent_TEMP_name]

    if child_bone:
        child_TEMP_name = f"TEMP_{child_bone}"
        if child_TEMP_name in edit_bones:
            edit_bones[child_TEMP_name].parent = new_bone

    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')


# Creates the DEF/CTRL/TEMPLATE armatures, root bones, widget collection, and root Copy Transforms constraint.
# Returns early with existing objects if the rig collection already exists.
# Root bone orientation follows front_axis from scene properties.
def create_base_rig(context, rig_name):
    if rig_name in bpy.data.collections:
        return (
            bpy.data.objects.get(f"DEF_{rig_name}"),
            bpy.data.objects.get(f"CTRL_{rig_name}"),
            bpy.data.objects.get(f"TEMPLATE_{rig_name}"),
        )

    front_axis = context.scene.rig_tool.front_axis
    ax         = lambda c: _apply_front_axis(c, front_axis)
    override   = _get_view3d_override(context)

    rig_collection = bpy.data.collections.new(rig_name)
    context.scene.collection.children.link(rig_collection)

    wgt_collection = bpy.data.collections.new(f"WGTS_{rig_name}")
    rig_collection.children.link(wgt_collection)
    wgt_collection.hide_viewport = True
    wgt_collection.hide_render = True

    def_armature = bpy.data.armatures.new(f"DEF_{rig_name}")
    def_obj = bpy.data.objects.new(f"DEF_{rig_name}", def_armature)
    rig_collection.objects.link(def_obj)

    ctrl_armature = bpy.data.armatures.new(f"CTRL_{rig_name}")
    ctrl_obj = bpy.data.objects.new(f"CTRL_{rig_name}", ctrl_armature)
    rig_collection.objects.link(ctrl_obj)

    template_armature = bpy.data.armatures.new(f"TEMPLATE_{rig_name}")
    template_obj = bpy.data.objects.new(f"TEMPLATE_{rig_name}", template_armature)
    rig_collection.objects.link(template_obj)

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    root_bone = def_armature.edit_bones.new("root")
    root_bone.head = ax((0.0, 0.0, 0.0))
    root_bone.tail = ax((0.1, 0.0, 0.0))
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    ctrl_root = ctrl_armature.edit_bones.new("CTRL_root")
    ctrl_root.head = ax((0.0, 0.0, 0.0))
    ctrl_root.tail = ax((0.1, 0.0, 0.0))
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    ctrl_widget = create_circle_arrow_widget(f"WGT_{rig_name}_root", wgt_collection)

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    ctrl_root_pose = ctrl_obj.pose.bones["CTRL_root"]
    ctrl_root_pose.custom_shape = ctrl_widget
    ctrl_root_pose.use_custom_shape_bone_size = False
    ctrl_root_pose.rotation_mode = 'QUATERNION'
    ctrl_root_pose.color.palette = 'CUSTOM'
    ctrl_root_pose.color.custom.normal = (0.8, 0.0, 0.0)
    ctrl_root_pose.color.custom.select = (1.0, 0.4, 0.4)
    ctrl_root_pose.color.custom.active = (1.0, 0.6, 0.6)
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    root_pose = def_obj.pose.bones["root"]
    copy_transforms = root_pose.constraints.new('COPY_TRANSFORMS')
    copy_transforms.target = ctrl_obj
    copy_transforms.subtarget = "CTRL_root"
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    return def_obj, ctrl_obj, template_obj


# Creates DEF_ and/or CTRL_ bones for a named part, sets up the widget, assigns the Copy Transforms
# constraint linking DEF to CTRL, registers the part in the UI list, and returns the actual name used.
def create_bone(context, rig_name, bone_name, is_deforming, has_control, parent_bone_name="root", ctrl_radius=0.5, ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0), bone_tail=(0.0, 0.1, 0.0), ctrl_offset=(0.0, 0.0, 0.0), widget_type='circle', ctrl_shape_rotation=0.0, ctrl_color=(0.8, 0.0, 0.0), ctrl_widget_rotation_z=0.0):
    def_obj, ctrl_obj, template_obj = create_base_rig(context, rig_name)
    override = _get_view3d_override(context)

    front_axis = context.scene.rig_tool.front_axis
    bone_head  = _apply_front_axis(bone_head, front_axis)
    bone_tail  = _apply_front_axis(bone_tail, front_axis)

    bone_name      = _unique_name('part', bone_name, context.scene.rig_tool)
    def_bone_name  = f"DEF_{bone_name}"
    ctrl_bone_name = f"CTRL_{bone_name}"

    if is_deforming:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        def_bone = def_obj.data.edit_bones.new(def_bone_name)
        def_bone.head = bone_head
        def_bone.tail = bone_tail
        def_parent_name = parent_bone_name if parent_bone_name == "root" else f"DEF_{parent_bone_name}"
        def_bone.parent = def_obj.data.edit_bones[def_parent_name]
        def_bone.use_connect = False
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    if has_control:
        wgt_collection = bpy.data.collections.get(f"WGTS_{rig_name}")
        if widget_type == 'arc_arrow':
            ctrl_widget = create_arc_arrow_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)
        elif widget_type == 'circle_arrow':
            ctrl_widget = create_circle_arrow_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)
        else:
            ctrl_widget = create_circle_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)

        if ctrl_widget_rotation_z != 0.0:
            rot3   = mathutils.Matrix.Rotation(ctrl_widget_rotation_z, 3, 'Z')
            pivot  = mathutils.Vector(ctrl_offset)
            for vert in ctrl_widget.data.vertices:
                vert.co = rot3 @ (vert.co - pivot) + pivot

        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        ctrl_bone = ctrl_obj.data.edit_bones.new(ctrl_bone_name)
        ctrl_bone.head = bone_head
        ctrl_bone.tail = bone_tail
        ctrl_bone.parent = ctrl_obj.data.edit_bones[f"CTRL_{parent_bone_name}"]
        ctrl_bone.use_connect = False
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='POSE')
        ctrl_pose_bone = ctrl_obj.pose.bones[ctrl_bone_name]
        ctrl_pose_bone.custom_shape = ctrl_widget
        ctrl_pose_bone.use_custom_shape_bone_size = False
        ctrl_pose_bone.rotation_mode = 'QUATERNION'
        ctrl_pose_bone.color.palette = 'CUSTOM'
        ctrl_pose_bone.color.custom.normal = ctrl_color
        ctrl_pose_bone.color.custom.select = tuple(min(1.0, c + 0.4) for c in ctrl_color)
        ctrl_pose_bone.color.custom.active = tuple(min(1.0, c + 0.6) for c in ctrl_color)
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    if is_deforming and has_control:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='POSE')
        def_pose_bone = def_obj.pose.bones[def_bone_name]
        copy_transforms = def_pose_bone.constraints.new('COPY_TRANSFORMS')
        copy_transforms.target = ctrl_obj
        copy_transforms.subtarget = ctrl_bone_name
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    _add_part(context, bone_name, parent_bone_name)
    add_template(context, rig_name, bone_name, parent_bone=parent_bone_name, bone_head=bone_head, bone_tail=bone_tail)
    return bone_name


# Visibility-aware wrapper: makes all armatures visible, creates the bone, then restores visibility.
def add_bone(context, rig_name, bone_name, is_deforming, has_control, **kwargs):
    armatures_visible(rig_name)
    create_bone(context, rig_name, bone_name, is_deforming, has_control, **kwargs)
    update_rig_visibility(context, rig_name)
