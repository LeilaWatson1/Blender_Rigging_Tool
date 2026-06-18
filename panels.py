import bpy

# the shelf/option box UI layout

# Draws each row of the parts list, indenting by two spaces per hierarchy level.
class RIGTOOL_UL_parts_list(bpy.types.UIList):
    # Renders a single list row with indent prefix and part name.
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.label(text=("  " * item.indent) + item.name)


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

        layout.prop(props, "rig_name")

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

        row = layout.row()
        row.prop(props, "show_templates",
                 icon='TRIA_DOWN' if props.show_templates else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_templates:
            box = layout.box()
            box.operator("rig_tool.template_revolver")

        row = layout.row()
        row.prop(props, "show_parts",
                 icon='TRIA_DOWN' if props.show_parts else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_parts:
            box = layout.box()
            box.operator("rig_tool.add_bone", text="Single Bone")
            if props.show_add_bone_ui:
                inner = box.box()
                inner.prop(props, "bone_name")
                inner.prop(props, "is_deforming")
                inner.prop(props, "has_control")
                inner.operator("rig_tool.create_bone")
            box.operator("rig_tool.add_cylinder_part")

        row = layout.row(align=True)
        op = row.operator("rig_tool.set_mode", text="Template Mode", depress=(props.mode == 'TEMPLATE'))
        op.mode = 'TEMPLATE'
        op = row.operator("rig_tool.set_mode", text="Pose Mode", depress=(props.mode == 'POSE'))
        op.mode = 'POSE'


def register():
    bpy.utils.register_class(RIGTOOL_UL_parts_list)
    bpy.utils.register_class(VIEW3D_PT_rig_tool)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_rig_tool)
    bpy.utils.unregister_class(RIGTOOL_UL_parts_list)
