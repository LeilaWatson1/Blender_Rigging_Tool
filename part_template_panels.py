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


# Shows the FK/IK blend slider in the Item N-panel tab when a CTRL_IK_FK bone is the active bone.
class VIEW3D_PT_chain_props(bpy.types.Panel):
    bl_label      = "FK / IK"
    bl_idname     = "VIEW3D_PT_chain_props"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category   = "Item"

    # Returns True when the active bone in Pose mode is a chain blend control bone.
    @classmethod
    def poll(cls, context):
        obj  = context.active_object
        bone = context.active_pose_bone
        return (obj and obj.type == 'ARMATURE' and obj.mode == 'POSE'
                and bone and bool(bone.chain_props.base_name))

    # Draws the FK/IK blend slider and the IK pole angle from the chain's IK constraint.
    def draw(self, context):
        bone   = context.active_pose_bone
        layout = self.layout
        layout.prop(bone.chain_props, "fk_ik", text="FK / IK", slider=True)

        rig_name  = bone.chain_props.rig_name
        base_name = bone.chain_props.base_name
        ctrl_obj  = bpy.data.objects.get(f"CTRL_{rig_name}")
        if ctrl_obj and bone.name.startswith("CTRL_IK_Pole_"):
            ik_pbs = sorted(
                (pb for pb in ctrl_obj.pose.bones if pb.name.startswith(f"HIDE_IK_{base_name}_")),
                key=lambda b: b.name
            )
            if ik_pbs:
                ik_con = next((c for c in ik_pbs[-1].constraints if c.type == 'IK'), None)
                if ik_con:
                    layout.prop(ik_con, "pole_angle")


def register():
    bpy.utils.register_class(VIEW3D_PT_cylinder_props)
    bpy.utils.register_class(VIEW3D_PT_chain_props)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_chain_props)
    bpy.utils.unregister_class(VIEW3D_PT_cylinder_props)
