import bpy
from .rig_modules import create_base_rig, add_bone, create_revolver_template, create_cylinder_part, update_rig_visibility, armatures_visible, pose_update, _get_view3d_override, _unique_part_name

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
        props  = context.scene.rig_tool
        parent = props.parts[props.active_part_index].name if props.parts and props.active_part_index < len(props.parts) else "root"
        add_bone(
            context,
            props.rig_name,
            props.bone_name,
            props.is_deforming,
            props.has_control,
            parent_bone_name=parent,
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


# Toggles the Cylinder UI panel open or closed.
class RIGTOOL_OT_add_cylinder_part(bpy.types.Operator):
    bl_idname = "rig_tool.add_cylinder_part"
    bl_label = "Cylinder"
    bl_description = "Show options for adding a cylinder part to the rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        props.show_add_cylinder_ui = not props.show_add_cylinder_ui
        return {'FINISHED'}


# Creates a cylinder part using the name entered in the Cylinder panel.
class RIGTOOL_OT_create_cylinder_part(bpy.types.Operator):
    bl_idname = "rig_tool.create_cylinder_part"
    bl_label = "Create"
    bl_description = "Create the cylinder part with the specified name"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props  = context.scene.rig_tool
        parent = props.parts[props.active_part_index].name if props.parts and props.active_part_index < len(props.parts) else "root"
        create_cylinder_part(context, props.rig_name, parent_bone_name=parent, base_name=props.cylinder_name)
        props.show_add_cylinder_ui = False
        return {'FINISHED'}


# Switches between Template Mode and Pose Mode, updating armature visibility and applying template positions.
class RIGTOOL_OT_set_mode(bpy.types.Operator):
    bl_idname = "rig_tool.set_mode"
    bl_label = "Set Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty()

    def execute(self, context):
        props    = context.scene.rig_tool
        props.mode = self.mode
        override = _get_view3d_override(context)

        if context.active_object and context.active_object.mode != 'OBJECT':
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        if self.mode == 'POSE':
            armatures_visible(props.rig_name)
            pose_update(context, props.rig_name)
            update_rig_visibility(context, props.rig_name)
            ctrl_obj = bpy.data.objects.get(f"CTRL_{props.rig_name}")
            if ctrl_obj:
                context.view_layer.objects.active = ctrl_obj
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='POSE')
        else:
            update_rig_visibility(context, props.rig_name)
            template_obj = bpy.data.objects.get(f"TEMPLATE_{props.rig_name}")
            if template_obj:
                context.view_layer.objects.active = template_obj
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='EDIT')

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


# Renames the selected part in the parts list and across all three armatures.
class RIGTOOL_OT_rename_part(bpy.types.Operator):
    bl_idname = "rig_tool.rename_part"
    bl_label = "Rename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}

        new_name = props.rename_input.strip()
        if not new_name:
            return {'CANCELLED'}

        item     = props.parts[props.active_part_index]
        old_name = item.name

        if old_name == new_name:
            return {'CANCELLED'}

        new_name = _unique_part_name(props, new_name)
        rig_name = props.rig_name
        override = _get_view3d_override(context)
        armatures_visible(rig_name)

        def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
        ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
        template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")

        if def_obj:
            context.view_layer.objects.active = def_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            bone = def_obj.data.edit_bones.get(f"DEF_{old_name}")
            if bone:
                bone.name = f"DEF_{new_name}"
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        if ctrl_obj:
            context.view_layer.objects.active = ctrl_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = ctrl_obj.data.edit_bones
            ctrl_bone = edit_bones.get(f"CTRL_{old_name}")
            if ctrl_bone:
                ctrl_bone.name = f"CTRL_{new_name}"
            hide_bone = edit_bones.get(f"HIDE_follow_{old_name}")
            if hide_bone:
                hide_bone.name = f"HIDE_follow_{new_name}"
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')
            pose_bone = ctrl_obj.pose.bones.get(f"CTRL_{new_name}")
            if pose_bone and pose_bone.cylinder_props.part_name == old_name:
                pose_bone.cylinder_props.part_name = new_name

        if template_obj:
            context.view_layer.objects.active = template_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = template_obj.data.edit_bones
            temp_bone = edit_bones.get(f"TEMP_{old_name}")
            if temp_bone:
                temp_bone.name = f"TEMP_{new_name}"
            follow_bone = edit_bones.get(f"TEMP_follow_{old_name}")
            if follow_bone:
                follow_bone.name = f"TEMP_follow_{new_name}"
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        item.name = new_name
        for part in props.parts:
            if part.parent_name == old_name:
                part.parent_name = new_name

        update_rig_visibility(context, rig_name)
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
    RIGTOOL_OT_create_cylinder_part,
    RIGTOOL_OT_set_mode,
    RIGTOOL_OT_move_part,
    RIGTOOL_OT_set_parent,
    RIGTOOL_OT_parent_to_root,
    RIGTOOL_OT_rename_part,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
