import bpy

# UI panels for individual part templates, shown in context-specific N-panel tabs.


# Shows capacity and rotate_to_round in the Item N-panel tab when CTRL_cylinder is the active bone.
class VIEW3D_PT_cylinder_props(bpy.types.Panel):
    bl_label = "Cylinder"
    bl_idname = "VIEW3D_PT_cylinder_props"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    # Returns True when the active bone in Pose mode is any cylinder control bone.
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        bone = context.active_pose_bone
        return (obj and obj.type == 'ARMATURE' and obj.mode == 'POSE'
                and bone and bool(bone.cylinder_props.part_name))

    # Draws the capacity and rotate_to_round properties for the cylinder bone.
    def draw(self, context):
        layout = self.layout
        bone = context.active_pose_bone
        layout.prop(bone.cylinder_props, "capacity")
        split = layout.split(factor=0.50)
        split.label(text="Rotate to Round")
        split.prop(bone.cylinder_props, "rotate_to_round", text="")


def register():
    bpy.utils.register_class(VIEW3D_PT_cylinder_props)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_cylinder_props)
