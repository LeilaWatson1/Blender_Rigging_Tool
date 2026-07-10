import bpy

# the shelf/option box UI layout

# Draws each row of the parts list, indenting by two spaces per hierarchy level.
class RIGTOOL_UL_parts_list(bpy.types.UIList):
    # Renders a single list row with indent prefix and part name.
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        prefix = "[SKT] " if item.is_socket else ""
        layout.label(text=("  " * item.indent) + prefix + item.name)


# Main N-panel for the Rig Tool tab, containing the parts list, templates, parts, and mode buttons.
class VIEW3D_PT_rig_tool(bpy.types.Panel):
    bl_label = "Prop Rigging Tool"
    bl_idname = "VIEW3D_PT_rig_tool"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rig Tool"

    # Draws all sections: parts list, templates, parts dropdown, and mode toggle buttons.
    def draw(self, context):
        layout = self.layout
        props = context.scene.rig_tool

        split = layout.split(factor=0.30)
        split.label(text="Current Rig")
        split.prop(props, "current_rig", text="")

        split = layout.split(factor=0.30)
        split.label(text="Visibility")
        row = split.row(align=True)
        row.prop(props, "show_current_rig", text="Current Rig", toggle=True)
        row.prop(props, "show_other_rigs",  text="All Rigs",    toggle=True)

        split = layout.split(factor=0.30)
        split.label(text="Front Axis")
        split.prop(props, "front_axis", text="")

        split = layout.split(factor=0.25)
        split.label(text="New Rig")
        row = split.row(align=True)
        row.prop(props, "rig_name", text="")
        row.operator("rig_tool.create_rig", text="Create")

        layout.operator("rig_tool.delete_rig", text="Delete Rig")

        row = layout.row()
        row.prop(props, "show_parts_list",
                 icon='TRIA_DOWN' if props.show_parts_list else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_parts_list:
            layout.template_list("RIGTOOL_UL_parts_list", "", props, "parts",
                                 props, "active_part_index", rows=5, maxrows=20)

            row = layout.row(align=True)
            row.operator("rig_tool.move_part", text="", icon='TRIA_UP').direction = 'UP'
            row.operator("rig_tool.move_part", text="", icon='TRIA_DOWN').direction = 'DOWN'

            if props.parts and props.active_part_index < len(props.parts):
                selected = props.parts[props.active_part_index]
                box = layout.box()
                box.label(text=f"Part: {selected.name}")
                box.prop_search(props, "parent_selector", props, "parts", text="Parent")
                row = box.row(align=True)
                row.operator("rig_tool.set_parent")
                row.operator("rig_tool.parent_to_root")
                row = box.row(align=True)
                row.prop(props, "rename_input", text="")
                row.operator("rig_tool.rename_part")
                row = box.row()
                row.prop(props, "show_edit_widget_ui",
                         icon='TRIA_DOWN' if props.show_edit_widget_ui else 'TRIA_RIGHT',
                         emboss=False)
                if props.show_edit_widget_ui:
                    wbox = box.box()
                    wbox.prop(props, "edit_widget", text="Widget")
                    split = wbox.split(factor=0.18)
                    split.label(text="Offset:")
                    row2 = split.row(align=True)
                    row2.prop(props, "edit_ctrl_offset_x", text="X")
                    row2.prop(props, "edit_ctrl_offset_y", text="Y")
                    row2.prop(props, "edit_ctrl_offset_z", text="Z")
                    split = wbox.split(factor=0.50)
                    split.label(text="Axis:")
                    split.prop(props, "edit_ctrl_axis", text="")
                    split = wbox.split(factor=0.50)
                    split.label(text="Shape Rotation:")
                    split.prop(props, "edit_shape_rotation", text="")
                    split = wbox.split(factor=0.50)
                    split.label(text="Scale:")
                    split.prop(props, "edit_ctrl_radius", text="")
                    split = wbox.split(factor=0.50)
                    split.label(text="Color:")
                    split.prop(props, "edit_ctrl_color", text="")
                box.operator("rig_tool.delete_part")

        row = layout.row(align=True)
        op = row.operator("rig_tool.set_mode", text="Object Mode", depress=(props.mode == 'OBJECT'))
        op.mode = 'OBJECT'
        op = row.operator("rig_tool.set_mode", text="Template Mode", depress=(props.mode == 'TEMPLATE'))
        op.mode = 'TEMPLATE'
        op = row.operator("rig_tool.set_mode", text="Pose Mode", depress=(props.mode == 'POSE'))
        op.mode = 'POSE'

        row = layout.row()
        row.prop(props, "show_templates",
                 icon='TRIA_DOWN' if props.show_templates else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_templates:
            box = layout.box()
            box.prop(props, "selected_template", text="")
            split = box.split(factor=0.35)
            split.label(text="Name Prefix")
            split.prop(props, "template_prefix", text="")
            box.prop(props, "template_grip_socket")
            box.prop(props, "template_ejector_socket")
            box.prop(props, "template_flash_socket")
            box.operator("rig_tool.create_template", text="Create")

        row = layout.row()
        row.prop(props, "show_parts",
                 icon='TRIA_DOWN' if props.show_parts else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_parts:
            box = layout.box()
            box.prop(props, "selected_part_type", text="")
            inner = box.box()
            if props.selected_part_type == 'single_bone':
                split = inner.split(factor=0.50)
                split.label(text="Bone Name")
                split.prop(props, "bone_name", text="")
                row = inner.row()
                row.prop(props, "is_deforming")
                row.prop(props, "has_control")
                inner.prop(props, "bone_widget", text="Widget")
            elif props.selected_part_type == 'socket_bone':
                split = inner.split(factor=0.50)
                split.label(text="Bone Name")
                split.prop(props, "socket_name", text="")
                inner.prop(props, "socket_has_control")
                inner.prop(props, "socket_widget", text="Widget")
            elif props.selected_part_type == 'bone_chain':
                split = inner.split(factor=0.50)
                split.label(text="Bone Name")
                split.prop(props, "chain_name", text="")
                row = inner.row()
                row.prop(props, "chain_is_deforming")
                row.prop(props, "chain_has_control")
                inner.prop(props, "chain_widget", text="Widget")
                split = inner.split(factor=0.50)
                split.label(text="Chain Length")
                split.prop(props, "chain_length", text="")
                split = inner.split(factor=0.50)
                split.label(text="FK/IK")
                split.prop(props, "chain_fk_ik", text="")
            elif props.selected_part_type == 'cylinder':
                split = inner.split(factor=0.50)
                split.label(text="Name")
                split.prop(props, "cylinder_name", text="")
            box.operator("rig_tool.create_part", text="Create")

        row = layout.row()
        row.prop(props, "show_export",
                 icon='TRIA_DOWN' if props.show_export else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_export:
            box = layout.box()

            split = box.split(factor=0.35)
            split.label(text="Engine")
            split.prop(props, "export_engine", text="")

            split = box.split(factor=0.35)
            split.label(text="Format")
            split.prop(props, "export_format", text="")

            if props.export_engine == 'UNREAL':
                box.prop(props, "scale_on_export")

            box.operator("rig_tool.export", text="Export")


def register():
    bpy.utils.register_class(RIGTOOL_UL_parts_list)
    bpy.utils.register_class(VIEW3D_PT_rig_tool)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_rig_tool)
    bpy.utils.unregister_class(RIGTOOL_UL_parts_list)
