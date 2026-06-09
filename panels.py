import bpy

# the shelf/option box UI layout

class VIEW3D_PT_rig_tool(bpy.types.Panel):
    bl_label = "Prop Rigging Tool"
    bl_idname = "VIEW3D_PT_rig_tool"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rig Tool"

    def draw(self, context):
        layout = self.layout
        props = context.scene.rig_tool

        layout.prop(props, "rig_name")

        row = layout.row()
        row.prop(props, "show_templates",
                 icon='TRIA_DOWN' if props.show_templates else 'TRIA_RIGHT',
                 emboss=False)
        if props.show_templates:
            box = layout.box()
            box.operator("rig_tool.template_revolver")

        layout.operator("rig_tool.add_bone")

        if props.show_add_bone_ui:
            box = layout.box()
            box.prop(props, "bone_name")
            box.prop(props, "is_deforming")
            box.prop(props, "has_control")
            box.operator("rig_tool.create_bone")

def register():
    bpy.utils.register_class(VIEW3D_PT_rig_tool)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_rig_tool)
