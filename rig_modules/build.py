import bpy
import math
import mathutils
from .widgets import create_circle_widget, create_arc_arrow_widget, create_circle_arrow_widget, create_double_arrow_widget


# Returns a unique name by checking existing rigs (name_type='rig') or parts (name_type='part'), appending _001, _002 etc. if needed.
# name_type: 'rig' checks DEF_ scene objects; 'part' checks props.parts.
# name: the base name to make unique.
# props: RigToolProperties instance, required when name_type is 'part'.
# Returns: unique string name with numeric suffix if the base name was already taken.
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


# Walks up the parts hierarchy to find the nearest ancestor that has a CTRL_ bone.
# Chain parts resolve to their last CTRL_FK bone (or CTRL_IK for IK-only chains).
# ctrl_obj: the CTRL_ armature object to search for bones.
# parent_bone_name: part name of the desired parent, or "root".
# props: RigToolProperties instance containing the parts hierarchy.
# Returns: the nearest ancestor EditBone with a CTRL_ prefix, or the root EditBone.
def _find_ctrl_parent(ctrl_obj, parent_bone_name, props):
    name = parent_bone_name
    while name and name != "root":
        ctrl = ctrl_obj.data.edit_bones.get(f"CTRL_{name}")
        if ctrl:
            return ctrl
        part = next((p for p in props.parts if p.name == name), None)
        if part and part.is_fk_ik_chain:
            base         = part.chain_base_name
            follow_bones = sorted(
                (eb for eb in ctrl_obj.data.edit_bones if eb.name.startswith(f"HIDE_follow_{base}_")),
                key=lambda b: b.name,
            )
            if follow_bones:
                return follow_bones[-1]
        name = part.parent_name if part else "root"
    return ctrl_obj.data.edit_bones.get("root")


# Resolves the DEF parent edit bone for a given parent_bone_name, handling chain parts.
# Must be called while def_obj is in EDIT mode.
# def_obj: the DEF_ armature object to search for edit bones.
# parent_bone_name: part name of the desired parent, or "root".
# props: RigToolProperties instance containing the parts hierarchy.
# Returns: the matching DEF_ or SKT_ EditBone, or the root EditBone if not found.
def _resolve_def_parent(def_obj, parent_bone_name, props):
    part = next((p for p in props.parts if p.name == parent_bone_name), None)
    if part and part.is_fk_ik_chain:
        chain_bones = sorted(
            (eb for eb in def_obj.data.edit_bones if eb.name.startswith(f"DEF_{part.chain_base_name}_")),
            key=lambda b: b.name,
        )
        return chain_bones[-1] if chain_bones else def_obj.data.edit_bones.get("root")
    if parent_bone_name == "root":
        return def_obj.data.edit_bones.get("root")
    if f"DEF_{parent_bone_name}" in def_obj.data.edit_bones:
        return def_obj.data.edit_bones[f"DEF_{parent_bone_name}"]
    return def_obj.data.edit_bones.get(f"SKT_{parent_bone_name}")


# Appends a new entry to the parts list in the UI and moves it to sit directly under its parent.
# part_name: the name for the new part.
# parent_name: the name of the parent part, or "" for root-level.
# is_socket: True if this part is an SKT_ socket bone.
# Returns: the newly created PropRigPartItem.
def _add_part(context, part_name, parent_name="", is_socket=False):
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
    item.is_socket   = is_socket

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
    return item


# Rotates a coordinate tuple +90° around Z when front_axis is 'Y', converting X-native to Y-native.
# coord: (x, y, z) tuple in X-native space.
# front_axis: 'X' returns coord unchanged; 'Y' rotates it +90° around Z.
# Returns: (x, y, z) tuple adjusted for the given front axis.
def _apply_front_axis(coord, front_axis):
    x, y, z = coord
    return (-y, x, z) if front_axis == 'Y' else coord


# Returns a context override dict for the active VIEW_3D window, required by bpy.ops calls from the N-panel.
# Returns: dict with 'window', 'area', and 'region' keys, or {} if no VIEW_3D is found.
def _get_view3d_override(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {'window': window, 'area': area, 'region': region}
    return {}


# Sets all three armatures visible and unhides HIDE_ bones so they can be edited.
# rig_name: the rig name used to look up DEF_, CTRL_, and TEMPLATE_ objects.
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
# rig_name: the rig name used to look up DEF_, CTRL_, and TEMPLATE_ objects.
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


# Puts Blender back into the correct edit mode for the current tool mode after an operation finishes.
# rig_name: the rig name used to look up the TEMPLATE_ or CTRL_ object.
def restore_mode(context, rig_name):
    mode     = context.scene.rig_tool.mode
    override = _get_view3d_override(context)
    if mode == 'TEMPLATE':
        template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")
        if template_obj:
            context.view_layer.objects.active = template_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
    elif mode == 'POSE':
        ctrl_obj = bpy.data.objects.get(f"CTRL_{rig_name}")
        if ctrl_obj:
            context.view_layer.objects.active = ctrl_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='POSE')
    # 'OBJECT': update_rig_visibility already leaves Blender in object mode


# Creates a TEMP_ bone in the template armature at the given position, with optional parent/child linking.
# bone_color sets a custom pose bone color (RGB tuple); None leaves the bone at the armature default.
# rig_name: the rig whose TEMPLATE_ armature receives the new bone.
# bone_name: the bone name without the TEMP_ prefix.
# parent_bone: name of the parent template bone (without TEMP_ prefix), or None.
# child_bone: name of a child template bone to re-parent under the new bone, or None.
# bone_head: world-space head position (x, y, z).
# bone_tail: world-space tail position (x, y, z).
# bone_color: RGB tuple for the bone colour; None for armature default.
# use_connect: True to connect the new bone's head to its parent's tail.
def add_template(context, rig_name, bone_name, parent_bone=None, child_bone=None, bone_head=(0.0, 0.0, 0.0), bone_tail=(0.0, 0.1, 0.0), bone_color=None, use_connect=False):
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
    new_bone.use_connect = use_connect

    if bone_color:
        new_bone.color.palette = 'CUSTOM'
        new_bone.color.custom.normal = bone_color
        new_bone.color.custom.select = tuple(min(1.0, c + 0.4) for c in bone_color)
        new_bone.color.custom.active = tuple(min(1.0, c + 0.6) for c in bone_color)

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
# rig_name: the name for the new rig; used to name all armatures, collections, and widgets.
# Returns: tuple of (def_obj, ctrl_obj, template_obj) Blender Object references.
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
# rig_name: the rig to add the bone to.
# bone_name: the part name (prefix is added automatically).
# is_deforming: True to create a DEF_ bone in the export armature.
# has_control: True to create a CTRL_ bone and widget in the control armature.
# parent_bone_name: parent part name or "root".
# ctrl_radius: radius (or length) of the widget shape.
# ctrl_axis: axis the widget shape lies on ('X', 'Y', or 'Z').
# bone_head: head position in X-native space (front_axis is applied automatically).
# bone_tail: tail position in X-native space (front_axis is applied automatically).
# ctrl_offset: XYZ offset applied to the widget mesh relative to the bone pivot.
# widget_type: shape to use ('circle', 'arc_arrow', 'circle_arrow', or 'double_arrow').
# ctrl_shape_rotation: extra rotation (radians) applied to the widget mesh in its plane.
# ctrl_color: RGB tuple for the bone's custom colour.
# ctrl_widget_rotation_z: additional Z rotation (radians) applied to the widget verts around the offset.
# bone_prefix: prefix for the DEF_ armature bone; 'DEF' for deforming, 'SKT' for socket bones.
# use_connect: True to connect the new bone's head to its parent's tail.
# Returns: the actual bone name used (may differ from bone_name if a duplicate existed).
def create_bone(context, rig_name, bone_name, is_deforming, has_control, parent_bone_name="root", ctrl_radius=0.5, ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0), bone_tail=(0.1, 0.0, 0.0), ctrl_offset=(0.0, 0.0, 0.0), widget_type='circle', ctrl_shape_rotation=0.0, ctrl_color=(0.8, 0.0, 0.0), ctrl_widget_rotation_z=0.0, bone_prefix="DEF", use_connect=False):
    def_obj, ctrl_obj, template_obj = create_base_rig(context, rig_name)
    override = _get_view3d_override(context)

    front_axis = context.scene.rig_tool.front_axis
    bone_head  = _apply_front_axis(bone_head, front_axis)
    bone_tail  = _apply_front_axis(bone_tail, front_axis)

    bone_name      = _unique_name('part', bone_name, context.scene.rig_tool)
    def_bone_name  = f"{bone_prefix}_{bone_name}"
    ctrl_bone_name = f"CTRL_{bone_name}"

    if is_deforming:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        def_bone = def_obj.data.edit_bones.new(def_bone_name)
        def_bone.head = bone_head
        def_bone.tail = bone_tail
        def_bone.parent = _resolve_def_parent(def_obj, parent_bone_name, context.scene.rig_tool)
        def_bone.use_connect = use_connect
        def_bone.use_deform  = (bone_prefix == "DEF")
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    if has_control:
        wgt_collection = bpy.data.collections.get(f"WGTS_{rig_name}")
        if widget_type == 'arc_arrow':
            ctrl_widget = create_arc_arrow_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)
        elif widget_type == 'circle_arrow':
            ctrl_widget = create_circle_arrow_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)
        elif widget_type == 'double_arrow':
            ctrl_widget = create_double_arrow_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, length=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)
        else:
            ctrl_widget = create_circle_widget(f"WGT_{rig_name}_{bone_name}", wgt_collection, radius=ctrl_radius, axis=ctrl_axis, offset=ctrl_offset, shape_rotation=ctrl_shape_rotation)

        ctrl_widget["widget_type"]    = widget_type
        ctrl_widget["ctrl_axis"]      = ctrl_axis
        ctrl_widget["ctrl_offset"]    = list(ctrl_offset)
        ctrl_widget["shape_rotation"] = ctrl_shape_rotation
        ctrl_widget["ctrl_color"]     = list(ctrl_color)
        ctrl_widget["ctrl_radius"]    = ctrl_radius

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
        ctrl_bone.parent = _find_ctrl_parent(ctrl_obj, parent_bone_name, context.scene.rig_tool)
        ctrl_bone.use_connect = use_connect
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

    _add_part(context, bone_name, parent_bone_name, is_socket=(bone_prefix == "SKT"))
    template_color = (0.0, 0.8, 0.0) if bone_prefix == "SKT" else None
    add_template(context, rig_name, bone_name, parent_bone=parent_bone_name, bone_head=bone_head, bone_tail=bone_tail, bone_color=template_color, use_connect=use_connect)
    return bone_name

# Creates a chain of connected edit bones, returning the last bone created.
# use_connect is False for the first bone (free head) and True for all subsequent bones (head-to-tail).
# ebs: the edit_bones collection of the armature being modified.
# bone_names: list of part names for the chain; the prefix is prepended to each.
# prefix: string prepended to each bone name (e.g. "DEF" or "CTRL_FK").
# bone_parent: the EditBone to use as parent for the first bone in the chain.
# bone_len: length of each bone in Blender units.
# front_axis: 'X' or 'Y' axis for bone placement direction.
# Returns: the last EditBone created in the chain.
def _add_chain_edit_bones(ebs, bone_names, prefix, bone_parent, bone_len, front_axis):
    par = bone_parent
    for i, name in enumerate(bone_names):
        eb             = ebs.new(f"{prefix}_{name}")
        eb.head        = _apply_front_axis((i * bone_len, 0.0, 0.0), front_axis)
        eb.tail        = _apply_front_axis(((i + 1) * bone_len, 0.0, 0.0), front_axis)
        eb.parent      = par
        eb.use_connect = (i > 0)
        par            = eb
    return par


# Creates a single named edit bone with explicit world-space head/tail positions.
# ebs: the edit_bones collection of the armature being modified.
# name: the full bone name including prefix.
# head_pos: (x, y, z) head position in X-native space (front_axis is applied).
# tail_pos: (x, y, z) tail position in X-native space (front_axis is applied).
# parent: the EditBone to parent this bone to.
# front_axis: 'X' or 'Y' axis used to rotate positions into the correct orientation.
# use_connect: True to connect the head to the parent's tail.
# Returns: the newly created EditBone.
def _add_single_edit_bone(ebs, name, head_pos, tail_pos, parent, front_axis, use_connect=False):
    eb             = ebs.new(name)
    eb.head        = _apply_front_axis(head_pos, front_axis)
    eb.tail        = _apply_front_axis(tail_pos, front_axis)
    eb.parent      = parent
    eb.use_connect = use_connect
    return eb


# Applies widget, rotation mode, and custom color to a pose bone.
# pb: the PoseBone to configure.
# widget: the Object to use as the bone's custom shape.
# color: RGB tuple for normal, select, and active bone colours.
def _apply_ctrl_pose(pb, widget, color):
    pb.custom_shape               = widget
    pb.use_custom_shape_bone_size = False
    pb.rotation_mode              = 'QUATERNION'
    pb.color.palette              = 'CUSTOM'
    pb.color.custom.normal        = color
    pb.color.custom.select        = tuple(min(1.0, c + 0.4) for c in color)
    pb.color.custom.active        = tuple(min(1.0, c + 0.6) for c in color)


# Creates a bone chain rig along the forward axis. fk_ik controls which control systems are built:
# 'FK' — FK controls only, 'IK' — IK controls only, 'BOTH' — blendable FK/IK with a slider bone.
# rig_name: the rig to add the chain to.
# base_name: root name for all chain bones; individual bones are named base_name_001, _002, etc.
# is_deforming: True to create DEF_ bones in the export armature.
# has_control: True to create CTRL_ bones and widgets in the control armature.
# chain_length: number of bones in the chain.
# parent_bone_name: parent part name or "root".
# widget_type: shape for FK control widgets ('circle', 'arc_arrow', etc.).
# fk_ik: which control systems to build, as described above.
def create_bone_chain(context, rig_name, base_name, is_deforming, has_control,
                      chain_length=2, parent_bone_name="root", widget_type='circle', fk_ik='BOTH'):
    def_obj, ctrl_obj, template_obj = create_base_rig(context, rig_name)
    override   = _get_view3d_override(context)
    front_axis = context.scene.rig_tool.front_axis
    props      = context.scene.rig_tool
    bone_len   = 0.1
    tip        = chain_length * bone_len

    bone_names     = [f"{base_name}_{i + 1:03d}" for i in range(chain_length)]
    part_name      = {'BOTH': f"FK_IK_{base_name}", 'FK': f"FK_{base_name}", 'IK': f"IK_{base_name}"}[fk_ik]
    fk_color       = (0.8, 0.8, 0.0)
    ik_color       = (0.0, 0.0, 0.8)
    wgt_collection = bpy.data.collections.get(f"WGTS_{rig_name}")

    # ── Pass 1: CTRL edit mode ────────────────────────────────────────────────
    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    ebs         = ctrl_obj.data.edit_bones
    ctrl_parent = _find_ctrl_parent(ctrl_obj, parent_bone_name, props)

    if fk_ik in ('BOTH', 'FK'):
        _add_chain_edit_bones(ebs, bone_names, "CTRL_FK", ctrl_parent, bone_len, front_axis)

    if fk_ik in ('BOTH', 'IK'):
        top_eb = _add_single_edit_bone(
            ebs, f"CTRL_IK_Top_{base_name}",
            (0.0, 0.0, 0.0), (bone_len, 0.0, 0.0),
            ctrl_parent, front_axis,
        )
        _add_chain_edit_bones(ebs, bone_names, "HIDE_IK", top_eb, bone_len, front_axis)
        _add_single_edit_bone(
            ebs, f"CTRL_IK_{base_name}",
            (tip, 0.0, 0.0), (tip + bone_len, 0.0, 0.0),
            top_eb, front_axis,
        )
        _add_single_edit_bone(
            ebs, f"CTRL_IK_Pole_{base_name}",
            (tip * 0.5, bone_len * 1.5, 0.0), (tip * 0.5, bone_len * 2.5, 0.0),
            top_eb, front_axis,
        )

    _add_chain_edit_bones(ebs, bone_names, "HIDE_follow", ctrl_parent, bone_len, front_axis)

    # Hide HIDE_ bones last so earlier operations can still reference them by name.
    for eb in ebs:
        if eb.name.startswith("HIDE_"):
            eb.hide = True

    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pass 2: DEF edit mode ─────────────────────────────────────────────────
    if is_deforming:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        ebs        = def_obj.data.edit_bones
        def_parent = _resolve_def_parent(def_obj, parent_bone_name, props)
        _add_chain_edit_bones(ebs, bone_names, "DEF", def_parent, bone_len, front_axis)
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pass 3: CTRL pose mode ────────────────────────────────────────────────
    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    pbs = ctrl_obj.pose.bones

    if fk_ik in ('BOTH', 'FK') and has_control:
        for name in bone_names:
            wgt = create_circle_widget(f"WGT_{rig_name}_FK_{name}", wgt_collection, radius=0.25, axis='Y')
            _apply_ctrl_pose(pbs[f"CTRL_FK_{name}"], wgt, fk_color)

    if fk_ik in ('BOTH', 'IK') and has_control:
        for bone_n, color in [
            (f"CTRL_IK_Top_{base_name}", (0.0, 0.3, 0.8)),
            (f"CTRL_IK_{base_name}",     ik_color),
        ]:
            wgt = create_circle_widget(f"WGT_{rig_name}_{bone_n}", wgt_collection, radius=0.25, axis='Y')
            _apply_ctrl_pose(pbs[bone_n], wgt, color)
        pole_name = f"CTRL_IK_Pole_{base_name}"
        wgt = create_circle_widget(f"WGT_{rig_name}_{pole_name}", wgt_collection, radius=0.25, axis='Y')
        _apply_ctrl_pose(pbs[pole_name], wgt, ik_color)
        pbs[pole_name].custom_shape_scale_xyz = (0.5, 0.5, 0.5)

        ik_con               = pbs[f"HIDE_IK_{bone_names[-1]}"].constraints.new('IK')
        ik_con.target        = ctrl_obj
        ik_con.subtarget     = f"CTRL_IK_{base_name}"
        ik_con.pole_target   = ctrl_obj
        ik_con.pole_subtarget = f"CTRL_IK_Pole_{base_name}"
        ik_con.chain_count   = chain_length
        ik_con.pole_angle    = math.pi

    for name in bone_names:
        follow_pb = pbs[f"HIDE_follow_{name}"]
        if fk_ik in ('BOTH', 'FK'):
            c           = follow_pb.constraints.new('COPY_TRANSFORMS')
            c.target    = ctrl_obj
            c.subtarget = f"CTRL_FK_{name}"
            c.influence = 1.0
        if fk_ik in ('BOTH', 'IK'):
            c           = follow_pb.constraints.new('COPY_TRANSFORMS')
            c.target    = ctrl_obj
            c.subtarget = f"HIDE_IK_{name}"
            c.influence = 0.0 if fk_ik == 'BOTH' else 1.0

    if fk_ik == 'BOTH' and has_control:
        # Stamp chain_props on every control bone so the Item tab slider appears on any selected chain bone.
        for name in bone_names:
            pbs[f"CTRL_FK_{name}"].chain_props.base_name = base_name
            pbs[f"CTRL_FK_{name}"].chain_props.rig_name  = rig_name
        for ik_bone_name in (f"CTRL_IK_Top_{base_name}", f"CTRL_IK_{base_name}",
                              f"CTRL_IK_Pole_{base_name}"):
            pb = pbs.get(ik_bone_name)
            if pb:
                pb.chain_props.base_name = base_name
                pb.chain_props.rig_name  = rig_name

        # Initial state: FK-dominant, so IK controls start hidden.
        ctrl_obj.data.bones[f"CTRL_IK_{base_name}"].hide     = True
        ctrl_obj.data.bones[f"CTRL_IK_Pole_{base_name}"].hide = True
        ctrl_obj.data.bones[f"CTRL_IK_Top_{base_name}"].hide  = True

    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pass 4: DEF pose mode ─────────────────────────────────────────────────
    if is_deforming:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='POSE')
        for name in bone_names:
            c           = def_obj.pose.bones[f"DEF_{name}"].constraints.new('COPY_TRANSFORMS')
            c.target    = ctrl_obj
            c.subtarget = f"HIDE_follow_{name}"
        first_pb                      = def_obj.pose.bones[f"DEF_{bone_names[0]}"]
        first_pb["chain_part_name"]   = part_name
        first_pb["chain_base_name"]   = base_name
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pass 5: Template bones ────────────────────────────────────────────────
    if fk_ik in ('BOTH', 'FK'):
        for i, name in enumerate(bone_names):
            head     = _apply_front_axis((i * bone_len, 0.0, 0.0), front_axis)
            tail     = _apply_front_axis(((i + 1) * bone_len, 0.0, 0.0), front_axis)
            parent_t = f"FK_{bone_names[i - 1]}" if i > 0 else parent_bone_name
            add_template(context, rig_name, f"FK_{name}",
                         parent_bone=parent_t, bone_head=head, bone_tail=tail, use_connect=(i > 0))

    if fk_ik == 'IK':
        for i, name in enumerate(bone_names):
            head     = _apply_front_axis((i * bone_len, 0.0, 0.0), front_axis)
            tail     = _apply_front_axis(((i + 1) * bone_len, 0.0, 0.0), front_axis)
            parent_t = f"IK_{bone_names[i - 1]}" if i > 0 else parent_bone_name
            add_template(context, rig_name, f"IK_{name}",
                         parent_bone=parent_t, bone_head=head, bone_tail=tail, use_connect=(i > 0))

    if fk_ik in ('BOTH', 'IK'):
        add_template(context, rig_name, f"IK_Pole_{base_name}",
                     parent_bone=parent_bone_name,
                     bone_head=_apply_front_axis((tip * 0.5, bone_len * 1.5, 0.0), front_axis),
                     bone_tail=_apply_front_axis((tip * 0.5, bone_len * 2.5, 0.0), front_axis))

    # ── Pass 6: Parts list ────────────────────────────────────────────────────
    chain_item                  = _add_part(context, part_name, parent_bone_name)
    chain_item.is_fk_ik_chain   = True
    chain_item.chain_base_name  = base_name


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
        chain_tips = {}  # base_name -> (last_index, head, tail) of the last FK bone seen
        for bone_name, (head, tail, roll) in template_data.items():
            target = edit_bones.get(f"CTRL_{bone_name}") or edit_bones.get(f"HIDE_{bone_name}")
            if target:
                target.head = head
                target.tail = tail
                target.roll = roll
                # Sync HIDE_follow and HIDE_IK to match their FK counterpart so DEF bones update correctly.
                if bone_name.startswith("FK_"):
                    suffix = bone_name[3:]
                    for companion in (edit_bones.get(f"HIDE_follow_{suffix}"),
                                      edit_bones.get(f"HIDE_IK_{suffix}")):
                        if companion:
                            companion.head = head
                            companion.tail = tail
                            companion.roll = roll
                    parts = suffix.rsplit("_", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        base, idx = parts[0], int(parts[1])
                        if base not in chain_tips or idx > chain_tips[base][0]:
                            chain_tips[base] = (idx, head, tail)
                # For IK-only chains, sync HIDE_follow from the IK template bones.
                elif bone_name.startswith("IK_"):
                    suffix = bone_name[3:]
                    companion = edit_bones.get(f"HIDE_follow_{suffix}")
                    if companion:
                        companion.head = head
                        companion.tail = tail
                        companion.roll = roll
                    parts = suffix.rsplit("_", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        base, idx = parts[0], int(parts[1])
                        if base not in chain_tips or idx > chain_tips[base][0]:
                            chain_tips[base] = (idx, head, tail)

        # Move CTRL_IK_ to the tip of its FK chain, continuing in the same direction as the last FK bone.
        for base, (_, tip_head, tip_tail) in chain_tips.items():
            ik_eb = edit_bones.get(f"CTRL_IK_{base}")
            if ik_eb:
                ik_eb.head = tip_tail
                ik_eb.tail = tip_tail + (tip_tail - tip_head)
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
