import bpy
from .rig_modules import create_base_rig, create_bone

# the Python functions behind your shelf buttons

class RIGTOOL_OT_add_bone(bpy.types.Operator):
    bl_idname = "rig_tool.add_bone"
    bl_label = "Add Bone"
    bl_description = "Show options for adding a bone to the rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        props.show_add_bone_ui = not props.show_add_bone_ui
        return {'FINISHED'}


class RIGTOOL_OT_create_bone(bpy.types.Operator):
    bl_idname = "rig_tool.create_bone"
    bl_label = "Create"
    bl_description = "Create the bone with the specified settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        create_bone(
            context,
            props.rig_name,
            props.bone_name,
            props.is_deforming,
            props.has_control,
        )
        props.show_add_bone_ui = False
        return {'FINISHED'}


classes = [RIGTOOL_OT_add_bone, RIGTOOL_OT_create_bone]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
