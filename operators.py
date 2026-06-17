import bpy
from .rig_modules import create_base_rig, add_bone, create_revolver_template, create_cylinder_part, update_rig_visibility, armatures_visible, pose_update, _get_view3d_override

# the Python functions behind your shelf buttons


# Recomputes each part's indent depth from its parent, running multiple passes until no values change.
def _recalculate_indents(props):
    changed = True
    while changed:
        changed = False
        indent_map = {part.name: part.indent for part in props.parts}
        for part in props.parts:
            new_indent = indent_map.get(part.parent_name, -1) + 1
            if part.indent != new_indent:
                part.indent = new_indent
                indent_map[part.name] = new_indent
                changed = True


# Reorders the parts list so every parent appears before its children, using a depth-first traversal.
def _sort_parts_by_hierarchy(props):
    children = {part.name: [] for part in props.parts}
    roots = []
    for part in props.parts:
        if part.parent_name in children:
            children[part.parent_name].append(part.name)
        else:
            roots.append(part.name)

    order = []
    def dfs(name):
        order.append(name)
        for child in children[name]:
            dfs(child)
    for name in roots:
        dfs(name)

    for target_idx, name in enumerate(order):
        current_idx = next(i for i, p in enumerate(props.parts) if p.name == name)
        props.parts.move(current_idx, target_idx)


# Reparents the DEF_, CTRL_, and TEMP_ bones for a part across all three armatures.
def _reparent_bones(context, bone_name, rig_name, new_parent):
    override = _get_view3d_override(context)
    armatures_visible(rig_name)

    def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
    ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
    template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")

    if def_obj:
        context.view_layer.objects.active = def_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        def_bone = def_obj.data.edit_bones.get(f"DEF_{bone_name}")
        new_def_parent = def_obj.data.edit_bones.get("root" if new_parent == "root" else f"DEF_{new_parent}")
        if def_bone and new_def_parent:
            def_bone.parent = new_def_parent
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    if ctrl_obj:
        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        ctrl_bone = ctrl_obj.data.edit_bones.get(f"CTRL_{bone_name}")
        new_ctrl_parent = ctrl_obj.data.edit_bones.get(f"CTRL_{new_parent}")
        if ctrl_bone and new_ctrl_parent:
            ctrl_bone.parent = new_ctrl_parent
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    if template_obj:
        context.view_layer.objects.active = template_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='EDIT')
        temp_bone = template_obj.data.edit_bones.get(f"TEMP_{bone_name}")
        if temp_bone:
            temp_bone.parent = None if new_parent == "root" else template_obj.data.edit_bones.get(f"TEMP_{new_parent}")
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    update_rig_visibility(context, rig_name)


# Updates a part's parent, recalculates indents, sorts the list by hierarchy, and reparents bones.
def _set_parent(context, item, rig_name, new_parent):
    bone_name = item.name
    item.parent_name = new_parent
    props = context.scene.rig_tool
    _recalculate_indents(props)
    _sort_parts_by_hierarchy(props)
    for i, part in enumerate(props.parts):
        if part.name == bone_name:
            props.active_part_index = i
            break
    _reparent_bones(context, bone_name, rig_name, new_parent)


# Toggles the Single Bone UI panel open or closed.
class RIGTOOL_OT_add_bone(bpy.types.Operator):
    bl_idname = "rig_tool.add_bone"
    bl_label = "Add Bone"
    bl_description = "Show options for adding a bone to the rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        props.show_add_bone_ui = not props.show_add_bone_ui
        return {'FINISHED'}


# Creates a single DEF/CTRL bone pair with the settings entered in the Single Bone panel.
class RIGTOOL_OT_create_bone(bpy.types.Operator):
    bl_idname = "rig_tool.create_bone"
    bl_label = "Create"
    bl_description = "Create the bone with the specified settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        add_bone(
            context,
            props.rig_name,
            props.bone_name,
            props.is_deforming,
            props.has_control,
        )
        props.show_add_bone_ui = False
        return {'FINISHED'}


# Creates all bones for the revolver template.
class RIGTOOL_OT_template_revolver(bpy.types.Operator):
    bl_idname = "rig_tool.template_revolver"
    bl_label = "Revolver"
    bl_description = "Contains: cylinder, cylinder latch, trigger, and safety parts"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        create_revolver_template(context, props.rig_name)
        return {'FINISHED'}


# Adds a standalone cylinder part (cylinder_latch + cylinder + follow setup) to the current rig.
class RIGTOOL_OT_add_cylinder_part(bpy.types.Operator):
    bl_idname = "rig_tool.add_cylinder_part"
    bl_label = "Cylinder"
    bl_description = "Add a cylinder part with latch and rotation follow"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        create_cylinder_part(context, props.rig_name)
        return {'FINISHED'}


# Switches between Template Mode and Pose Mode, updating armature visibility and applying template positions.
class RIGTOOL_OT_set_mode(bpy.types.Operator):
    bl_idname = "rig_tool.set_mode"
    bl_label = "Set Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.rig_tool
        props.mode = self.mode
        if self.mode == 'POSE':
            armatures_visible(props.rig_name)
            pose_update(context, props.rig_name)
        update_rig_visibility(context, props.rig_name)
        return {'FINISHED'}


# Moves the selected part up or down in the list and updates its parent to match its new position.
class RIGTOOL_OT_move_part(bpy.types.Operator):
    bl_idname = "rig_tool.move_part"
    bl_label = "Move Part"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    def execute(self, context):
        props = context.scene.rig_tool
        idx = props.active_part_index
        if self.direction == 'UP' and idx > 0:
            props.parts.move(idx, idx - 1)
            props.active_part_index -= 1
        elif self.direction == 'DOWN' and idx < len(props.parts) - 1:
            props.parts.move(idx, idx + 1)
            props.active_part_index += 1
        else:
            return {'FINISHED'}

        new_idx = props.active_part_index
        item = props.parts[new_idx]
        above = props.parts[new_idx - 1] if new_idx > 0 else None
        below = props.parts[new_idx + 1] if new_idx < len(props.parts) - 1 else None

        new_parent = above.parent_name if above else "root"
        if below and above and below.indent > above.indent:
            new_parent = below.parent_name

        if item.parent_name != new_parent:
            item.parent_name = new_parent
            _recalculate_indents(props)
            _reparent_bones(context, item.name, props.rig_name, new_parent)

        return {'FINISHED'}


# Sets the parent of the selected part to the value chosen in the Parent search field.
class RIGTOOL_OT_set_parent(bpy.types.Operator):
    bl_idname = "rig_tool.set_parent"
    bl_label = "Set Parent"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}
        item = props.parts[props.active_part_index]
        new_parent = props.parent_selector
        if not new_parent or new_parent == item.name:
            return {'CANCELLED'}
        _set_parent(context, item, props.rig_name, new_parent)
        return {'FINISHED'}


# Parents the selected part directly to root, removing it from any sub-hierarchy.
class RIGTOOL_OT_parent_to_root(bpy.types.Operator):
    bl_idname = "rig_tool.parent_to_root"
    bl_label = "To Root"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}
        item = props.parts[props.active_part_index]
        if item.parent_name == "root":
            return {'CANCELLED'}
        _set_parent(context, item, props.rig_name, "root")
        return {'FINISHED'}


classes = [
    RIGTOOL_OT_add_bone,
    RIGTOOL_OT_create_bone,
    RIGTOOL_OT_template_revolver,
    RIGTOOL_OT_add_cylinder_part,
    RIGTOOL_OT_set_mode,
    RIGTOOL_OT_move_part,
    RIGTOOL_OT_set_parent,
    RIGTOOL_OT_parent_to_root,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
