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
        layout.operator("rig_tool.add_bone")

def register():
    bpy.utils.register_class(VIEW3D_PT_rig_tool)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_rig_tool)