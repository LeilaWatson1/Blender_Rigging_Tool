import bpy

# the variables tool reads from the UI

class RigToolProperties(bpy.types.PropertyGroup):
    rig_name: bpy.props.StringProperty(
        name="Rig Name",
        default="MyRig",
    )
    bone_name: bpy.props.StringProperty(
        name="Bone Name",
        default="Bone",
    )
    is_deforming: bpy.props.BoolProperty(
        name="Is Deforming",
        default=True,
    )
    has_control: bpy.props.BoolProperty(
        name="Has Control",
        default=True,
    )
    show_templates: bpy.props.BoolProperty(
        name="Templates",
        default=False,
    )
    show_add_bone_ui: bpy.props.BoolProperty(
        default=False,
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('TEMPLATE', "Template Mode", ""),
            ('POSE', "Pose Mode", ""),
        ],
        default='TEMPLATE',
    )

def register():
    bpy.utils.register_class(RigToolProperties)
    bpy.types.Scene.rig_tool = bpy.props.PointerProperty(type=RigToolProperties)

def unregister():
    del bpy.types.Scene.rig_tool
    bpy.utils.unregister_class(RigToolProperties)
