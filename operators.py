import bpy
from .rig_modules import create_base_rig, add_bone, create_revolver_template, update_rig_visibility, armatures_visible, pose_update

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
        add_bone(
            context,
            props.rig_name,
            props.bone_name,
            props.is_deforming,
            props.has_control,
        )
        props.show_add_bone_ui = False
        return {'FINISHED'}


class RIGTOOL_OT_template_revolver(bpy.types.Operator):
    bl_idname = "rig_tool.template_revolver"
    bl_label = "Revolver"
    bl_description = "Contains: cylinder, cylinder latch, trigger, and safety parts"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.rig_tool
        create_revolver_template(context, props.rig_name)
        return {'FINISHED'}


class RIGTOOL_OT_set_mode(bpy.types.Operator):
    bl_idname = "rig_tool.set_mode"
    bl_label = "Set Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.rig_tool
        props.mode = self.mode
        if self.mode == 'POSE':
            armatures_visible(props.rig_name)
            pose_update(context, props.rig_name)
        update_rig_visibility(context, props.rig_name)
        return {'FINISHED'}


classes = [RIGTOOL_OT_add_bone, RIGTOOL_OT_create_bone, RIGTOOL_OT_template_revolver, RIGTOOL_OT_set_mode]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
