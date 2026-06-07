import bpy
from .rig_modules import create_base_rig

# the Python functions behind your shelf buttons

class RIGTOOL_OT_add_bone(bpy.types.Operator):
    bl_idname = "rig_tool.add_bone"
    bl_label = "Add Bone"
    bl_description = "Add a single bone to the rig, creating the base rig if it does not exist"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        create_base_rig(context, props.rig_name)
        return {'FINISHED'}

classes = [RIGTOOL_OT_add_bone]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)