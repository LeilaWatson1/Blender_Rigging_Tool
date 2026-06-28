import bpy
import math
import mathutils
from .rig_modules import create_base_rig, add_bone, create_revolver_template, create_pistol_template, create_cylinder_part, update_rig_visibility, restore_mode, armatures_visible, pose_update, _get_view3d_override, _unique_name, _apply_front_axis

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


# Returns "DEF_" or "SKT_" for a part's bone in the DEF armature (object mode safe).
def _get_def_prefix(bone_name, def_obj):
    for prefix in ("SKT_", "DEF_"):
        if def_obj.data.bones.get(f"{prefix}{bone_name}"):
            return prefix
    return "DEF_"


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
        def_bone       = def_obj.data.edit_bones.get(f"{_get_def_prefix(bone_name, def_obj)}{bone_name}")
        new_def_parent = def_obj.data.edit_bones.get("root" if new_parent == "root" else f"{_get_def_prefix(new_parent, def_obj)}{new_parent}")
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


# Recursively removes all objects and sub-collections in a collection, then removes the collection itself.
def _delete_collection(collection):
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for child in list(collection.children):
        _delete_collection(child)
    bpy.data.collections.remove(collection)


# Deletes the current rig's collection and all its contents after user confirmation.
class RIGTOOL_OT_delete_rig(bpy.types.Operator):
    bl_idname     = "rig_tool.delete_rig"
    bl_label      = "Delete Rig"
    bl_description = "Delete the current rig"
    bl_options    = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        collection = bpy.data.collections.get(rig_name)
        if collection:
            _delete_collection(collection)
        props.parts.clear()
        props.active_part_index = 0
        return {'FINISHED'}


# Creates a new base rig with a unique name and sets it as the current rig.
class RIGTOOL_OT_create_rig(bpy.types.Operator):
    bl_idname = "rig_tool.create_rig"
    bl_label = "Create"
    bl_description = "Create a new empty rig and set it as the current rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = _unique_name('rig', props.rig_name)
        create_base_rig(context, rig_name)
        props.current_rig      = rig_name
        props.current_rig_axis = props.front_axis
        return {'FINISHED'}


# Creates the part type selected in the Parts panel with the relevant settings.
class RIGTOOL_OT_create_part(bpy.types.Operator):
    bl_idname     = "rig_tool.create_part"
    bl_label      = "Create"
    bl_description = "Create the selected part type with the specified settings"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        parent = props.parts[props.active_part_index].name if props.parts and props.active_part_index < len(props.parts) else "root"
        if props.selected_part_type == 'single_bone':
            add_bone(context, rig_name, props.bone_name, props.is_deforming, props.has_control,
                     parent_bone_name=parent, widget_type=props.bone_widget)
        elif props.selected_part_type == 'socket_bone':
            add_bone(context, rig_name, props.socket_name, True, props.socket_has_control,
                     parent_bone_name=parent, widget_type=props.socket_widget, bone_prefix="SKT")
        elif props.selected_part_type == 'cylinder':
            create_cylinder_part(context, rig_name, parent_bone_name=parent, base_name=props.cylinder_name)
        restore_mode(context, rig_name)
        return {'FINISHED'}


# Creates the template selected in the Templates panel using the shared name prefix.
class RIGTOOL_OT_create_template(bpy.types.Operator):
    bl_idname     = "rig_tool.create_template"
    bl_label      = "Create"
    bl_description = "Create the selected template with the specified name prefix"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        prefix = props.template_prefix
        grip_socket    = props.template_grip_socket
        ejector_socket = props.template_ejector_socket
        flash_socket   = props.template_flash_socket
        if props.selected_template == 'revolver':
            create_revolver_template(context, rig_name, prefix=prefix, grip_socket=grip_socket, ejector_socket=ejector_socket, flash_socket=flash_socket)
        elif props.selected_template == 'pistol':
            create_pistol_template(context, rig_name, prefix=prefix, grip_socket=grip_socket, ejector_socket=ejector_socket, flash_socket=flash_socket)
        restore_mode(context, rig_name)
        return {'FINISHED'}




# Switches between Template Mode and Pose Mode, updating armature visibility and applying template positions.
class RIGTOOL_OT_set_mode(bpy.types.Operator):
    bl_idname = "rig_tool.set_mode"
    bl_label = "Set Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.mode == 'OBJECT':
            return "Exit edit/pose mode and return to Object Mode"
        if properties.mode == 'TEMPLATE':
            return "Switch to Template Mode to edit bone positions using the template armature"
        return "Switch to Pose Mode to animate and pose the rig using control bones"

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        props.mode = self.mode
        override = _get_view3d_override(context)

        if context.active_object and context.active_object.mode != 'OBJECT':
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        if self.mode == 'POSE':
            armatures_visible(rig_name)
            pose_update(context, rig_name)
            update_rig_visibility(context, rig_name)
            ctrl_obj = bpy.data.objects.get(f"CTRL_{rig_name}")
            if ctrl_obj:
                context.view_layer.objects.active = ctrl_obj
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='POSE')
        elif self.mode == 'TEMPLATE':
            update_rig_visibility(context, rig_name)
            template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")
            if template_obj:
                context.view_layer.objects.active = template_obj
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='EDIT')
        else:  # OBJECT
            update_rig_visibility(context, rig_name)

        return {'FINISHED'}


# Moves the selected part up or down in the list and updates its parent to match its new position.
class RIGTOOL_OT_move_part(bpy.types.Operator):
    bl_idname = "rig_tool.move_part"
    bl_label = "Move Part"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    @classmethod
    def description(cls, context, properties):
        if properties.direction == 'UP':
            return "Move the selected part up in the list"
        return "Move the selected part down in the list"

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
            _reparent_bones(context, item.name, props.current_rig, new_parent)
            restore_mode(context, props.current_rig)

        return {'FINISHED'}


# Sets the parent of the selected part to the value chosen in the Parent search field.
class RIGTOOL_OT_set_parent(bpy.types.Operator):
    bl_idname     = "rig_tool.set_parent"
    bl_label      = "Set Parent"
    bl_description = "Set the selected part's parent to the part chosen in the Parent field"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}
        item = props.parts[props.active_part_index]
        new_parent = props.parent_selector
        if not new_parent or new_parent == item.name:
            return {'CANCELLED'}
        _set_parent(context, item, props.current_rig, new_parent)
        restore_mode(context, props.current_rig)
        return {'FINISHED'}


# Deletes the selected part from the list and all three armatures, re-parenting its children to its former parent.
class RIGTOOL_OT_delete_part(bpy.types.Operator):
    bl_idname     = "rig_tool.delete_part"
    bl_label      = "Delete"
    bl_description = "Delete the selected part and its bones from the rig, re-parenting any children to its former parent"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}

        item       = props.parts[props.active_part_index]
        old_name   = item.name
        old_parent = item.parent_name
        rig_name   = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        override   = _get_view3d_override(context)
        armatures_visible(rig_name)

        for part in props.parts:
            if part.parent_name == old_name:
                part.parent_name = old_parent
        _recalculate_indents(props)

        def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
        ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
        template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")

        if def_obj:
            context.view_layer.objects.active = def_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            bone = def_obj.data.edit_bones.get(f"{_get_def_prefix(old_name, def_obj)}{old_name}")
            if bone:
                def_obj.data.edit_bones.remove(bone)
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        if ctrl_obj:
            context.view_layer.objects.active = ctrl_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = ctrl_obj.data.edit_bones
            ctrl_bone = edit_bones.get(f"CTRL_{old_name}")
            if ctrl_bone:
                edit_bones.remove(ctrl_bone)
            hide_bone = edit_bones.get(f"HIDE_follow_{old_name}")
            if hide_bone:
                edit_bones.remove(hide_bone)
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        if template_obj:
            context.view_layer.objects.active = template_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = template_obj.data.edit_bones
            temp_bone = edit_bones.get(f"TEMP_{old_name}")
            if temp_bone:
                edit_bones.remove(temp_bone)
            follow_bone = edit_bones.get(f"TEMP_follow_{old_name}")
            if follow_bone:
                edit_bones.remove(follow_bone)
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='OBJECT')

        props.parts.remove(props.active_part_index)
        props.active_part_index = min(props.active_part_index, len(props.parts) - 1)

        update_rig_visibility(context, rig_name)
        restore_mode(context, rig_name)
        return {'FINISHED'}


# Renames the selected part in the parts list and across all three armatures.
class RIGTOOL_OT_rename_part(bpy.types.Operator):
    bl_idname     = "rig_tool.rename_part"
    bl_label      = "Rename"
    bl_description = "Rename the selected part using the text entered in the name field"
    bl_options    = {'REGISTER', 'UNDO'}

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

        new_name = _unique_name('part', new_name, props)
        rig_name = props.current_rig
        if not rig_name or rig_name == 'NONE':
            return {'CANCELLED'}
        override = _get_view3d_override(context)
        armatures_visible(rig_name)

        def_obj      = bpy.data.objects.get(f"DEF_{rig_name}")
        ctrl_obj     = bpy.data.objects.get(f"CTRL_{rig_name}")
        template_obj = bpy.data.objects.get(f"TEMPLATE_{rig_name}")

        if def_obj:
            context.view_layer.objects.active = def_obj
            with context.temp_override(**override):
                bpy.ops.object.mode_set(mode='EDIT')
            prefix = _get_def_prefix(old_name, def_obj)
            bone   = def_obj.data.edit_bones.get(f"{prefix}{old_name}")
            if bone:
                bone.name = f"{prefix}{new_name}"
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
        restore_mode(context, rig_name)
        return {'FINISHED'}


# Returns the canonical 4x4 rotation from X-native space to the given front axis.
def _axis_matrix(axis):
    if axis == 'X':
        return mathutils.Matrix.Identity(4)
    else:  # 'Y'
        return mathutils.Matrix.Rotation(math.pi / 2, 4, 'Z')


# Rotates the current rig to match props.front_axis, using current_rig_axis to track applied state.
class RIGTOOL_OT_apply_front_axis(bpy.types.Operator):
    bl_idname     = "rig_tool.apply_front_axis"
    bl_label      = "Apply"
    bl_description = "Rotate the current rig to face the selected front axis"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props       = context.scene.rig_tool
        target_axis = props.front_axis
        if props.current_rig_axis == target_axis:
            return {'FINISHED'}
        rig_name = props.current_rig
        if rig_name and rig_name != 'NONE':
            rotation = _axis_matrix(target_axis) @ _axis_matrix(props.current_rig_axis).inverted()
            override  = _get_view3d_override(context)
            armatures_visible(rig_name)
            for prefix in ("DEF_", "CTRL_", "TEMPLATE_"):
                obj = bpy.data.objects.get(f"{prefix}{rig_name}")
                if not obj:
                    continue
                context.view_layer.objects.active = obj
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='EDIT')
                for bone in obj.data.edit_bones:
                    bone.head = rotation @ bone.head
                    bone.tail = rotation @ bone.tail
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode='OBJECT')
            update_rig_visibility(context, rig_name)
        props.current_rig_axis = target_axis
        restore_mode(context, rig_name)
        return {'FINISHED'}


# Opens a file browser and exports only the DEF armature, rotating to export_front_axis if needed then restoring.
class RIGTOOL_OT_export(bpy.types.Operator):
    bl_idname     = "rig_tool.export"
    bl_label      = "Export Rig"
    bl_description = "Export the current rig's DEF armature using the selected engine and format settings"
    bl_options    = {'REGISTER'}

    def execute(self, context):
        props    = context.scene.rig_tool
        rig_name = props.current_rig

        if not rig_name or rig_name == 'NONE':
            self.report({'ERROR'}, "No rig selected")
            return {'CANCELLED'}

        def_obj = bpy.data.objects.get(f"DEF_{rig_name}")
        if not def_obj:
            self.report({'ERROR'}, f"DEF_{rig_name} not found")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        def_obj.select_set(True)
        context.view_layer.objects.active = def_obj

        if props.export_format == 'FBX':
            if props.export_engine == 'UNITY':
                bpy.ops.export_scene.fbx('INVOKE_DEFAULT', use_selection=True,
                                         axis_forward='-Y', axis_up='Z')
            else:
                bpy.ops.export_scene.fbx('INVOKE_DEFAULT', use_selection=True)
        else:
            bpy.ops.export_scene.gltf('INVOKE_DEFAULT', use_selection=True)

        return {'FINISHED'}


# Parents the selected part directly to root, removing it from any sub-hierarchy.
class RIGTOOL_OT_parent_to_root(bpy.types.Operator):
    bl_idname = "rig_tool.parent_to_root"
    bl_label      = "To Root"
    bl_description = "Remove the selected part from its current parent and attach it directly to the rig root"
    bl_options    = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        if not props.parts or props.active_part_index >= len(props.parts):
            return {'CANCELLED'}
        item = props.parts[props.active_part_index]
        if item.parent_name == "root":
            return {'CANCELLED'}
        _set_parent(context, item, props.current_rig, "root")
        restore_mode(context, props.current_rig)
        return {'FINISHED'}


# Mutable flag — checked by _on_widget_edit_changed in properties.py to suppress
# re-entrant apply calls while _load_widget_settings is bulk-setting the edit fields.
_widget_load_guard = [False]


# Reads the selected bone's current widget metadata and populates the Widgets
# panel edit fields without triggering the apply callback.
def _load_widget_settings(context):
    props    = context.scene.rig_tool
    rig_name = props.current_rig
    if not rig_name or rig_name == 'NONE':
        return
    if not props.parts or props.active_part_index >= len(props.parts):
        return

    bone_name = props.parts[props.active_part_index].name
    wgt       = bpy.data.objects.get(f"WGT_{rig_name}_{bone_name}")

    _widget_load_guard[0] = True
    try:
        if wgt:
            props.edit_widget         = wgt.get("widget_type", "circle")
            props.edit_ctrl_axis      = wgt.get("ctrl_axis", "Z")
            offset                    = wgt.get("ctrl_offset", [0.0, 0.0, 0.0])
            props.edit_ctrl_offset_x  = float(offset[0])
            props.edit_ctrl_offset_y  = float(offset[1])
            props.edit_ctrl_offset_z  = float(offset[2])
            props.edit_shape_rotation = float(wgt.get("shape_rotation", 0.0))
            props.edit_ctrl_radius    = float(wgt.get("ctrl_radius", 0.1))
            stored                    = tuple(float(c) for c in wgt.get("ctrl_color", [0.8, 0.0, 0.0]))
            props.edit_ctrl_color     = min(_WIDGET_COLOR_MAP, key=lambda k: sum((a - b) ** 2 for a, b in zip(_WIDGET_COLOR_MAP[k], stored)))
    finally:
        _widget_load_guard[0] = False


_WIDGET_COLOR_MAP = {
    'RED':    (0.8, 0.0, 0.0),
    'ORANGE': (0.8, 0.4, 0.0),
    'YELLOW': (0.8, 0.8, 0.0),
    'GREEN':  (0.0, 0.8, 0.0),
    'BLUE':   (0.0, 0.0, 0.8),
    'PURPLE': (0.5, 0.0, 0.8),
    'WHITE':  (1.0, 1.0, 1.0),
}


# Applies all Widgets panel values to the selected bone's control widget, positions, and color.
# Called automatically by property update callbacks whenever any edit field changes.
def _apply_widget_settings(context):
    from .rig_modules.widgets import (
        create_circle_widget, create_arc_arrow_widget,
        create_circle_arrow_widget, create_double_arrow_widget,
    )
    props    = context.scene.rig_tool
    rig_name = props.current_rig
    if not rig_name or rig_name == 'NONE':
        return
    if not props.parts or props.active_part_index >= len(props.parts):
        return

    bone_name      = props.parts[props.active_part_index].name
    ctrl_bone_name = f"CTRL_{bone_name}"

    offset         = (props.edit_ctrl_offset_x, props.edit_ctrl_offset_y, props.edit_ctrl_offset_z)
    shape_rotation = props.edit_shape_rotation
    ctrl_color     = _WIDGET_COLOR_MAP[props.edit_ctrl_color]
    override       = _get_view3d_override(context)
    armatures_visible(rig_name)

    ctrl_obj       = bpy.data.objects.get(f"CTRL_{rig_name}")
    wgt_collection = bpy.data.collections.get(f"WGTS_{rig_name}")

    if not ctrl_obj:
        update_rig_visibility(context, rig_name)
        restore_mode(context, rig_name)
        return

    wgt_name    = f"WGT_{rig_name}_{bone_name}"
    old_wgt     = bpy.data.objects.get(wgt_name)
    ctrl_radius = props.edit_ctrl_radius

    # Replace widget mesh with new settings.
    if wgt_collection:
        if old_wgt:
            bpy.data.objects.remove(old_wgt, do_unlink=True)
        axis  = props.edit_ctrl_axis
        wtype = props.edit_widget
        if wtype == 'arc_arrow':
            new_wgt = create_arc_arrow_widget(wgt_name, wgt_collection, radius=ctrl_radius, axis=axis, offset=offset, shape_rotation=shape_rotation)
        elif wtype == 'circle_arrow':
            new_wgt = create_circle_arrow_widget(wgt_name, wgt_collection, radius=ctrl_radius, axis=axis, offset=offset, shape_rotation=shape_rotation)
        elif wtype == 'double_arrow':
            new_wgt = create_double_arrow_widget(wgt_name, wgt_collection, length=ctrl_radius, axis=axis, offset=offset, shape_rotation=shape_rotation)
        else:
            new_wgt = create_circle_widget(wgt_name, wgt_collection, radius=ctrl_radius, axis=axis, offset=offset, shape_rotation=shape_rotation)

        new_wgt["widget_type"]    = wtype
        new_wgt["ctrl_axis"]      = axis
        new_wgt["ctrl_offset"]    = list(offset)
        new_wgt["shape_rotation"] = shape_rotation
        new_wgt["ctrl_color"]     = list(ctrl_color)
        new_wgt["ctrl_radius"]    = ctrl_radius

        context.view_layer.objects.active = ctrl_obj
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='POSE')
        if ctrl_bone_name in ctrl_obj.pose.bones:
            pb = ctrl_obj.pose.bones[ctrl_bone_name]
            pb.custom_shape = new_wgt
            pb.color.palette = 'CUSTOM'
            pb.color.custom.normal = ctrl_color
            pb.color.custom.select = tuple(min(1.0, c + 0.4) for c in ctrl_color)
            pb.color.custom.active = tuple(min(1.0, c + 0.6) for c in ctrl_color)
        with context.temp_override(**override):
            bpy.ops.object.mode_set(mode='OBJECT')

    update_rig_visibility(context, rig_name)
    restore_mode(context, rig_name)




classes = [
    RIGTOOL_OT_create_rig,
    RIGTOOL_OT_create_part,
    RIGTOOL_OT_set_mode,
    RIGTOOL_OT_move_part,
    RIGTOOL_OT_set_parent,
    RIGTOOL_OT_apply_front_axis,
    RIGTOOL_OT_export,
    RIGTOOL_OT_parent_to_root,
    RIGTOOL_OT_delete_part,
    RIGTOOL_OT_rename_part,
    RIGTOOL_OT_create_template,
    RIGTOOL_OT_delete_rig,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
