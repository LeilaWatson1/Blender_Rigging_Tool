import bpy

# the variables tool reads from the UI

class RigToolProperties(bpy.types.PropertyGroup):
    rig_name: bpy.props.StringProperty(
        name="Rig Name",
        default="MyRig",
    )

def register():
    bpy.utils.register_class(RigToolProperties)
    bpy.types.Scene.rig_tool = bpy.props.PointerProperty(type=RigToolProperties)

def unregister():
    del bpy.types.Scene.rig_tool
    bpy.utils.unregister_class(RigToolProperties)