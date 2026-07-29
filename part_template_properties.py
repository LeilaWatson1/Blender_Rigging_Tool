import bpy
import math
import mathutils

# Custom animation properties for individual part templates, registered on Blender built-in types.


# Dynamically generates enum items 1..capacity for the rotate_to_round property.
def _get_rotate_items(self, context):
    return [(str(i), str(i), "") for i in range(1, self.capacity + 1)]


# Rotates the cylinder control to the selected round's position by dividing 360 degrees by capacity.
def _on_rotate_to_round_update(self, context):
    if not self.rotate_to_round or not self.part_name:
        return
    ctrl_obj = bpy.data.objects.get(f"CTRL_{self.rig_name}")
    if not ctrl_obj:
        return

    follow_bone = ctrl_obj.pose.bones.get(f"HIDE_follow_{self.part_name}")
    ctrl_bone   = ctrl_obj.pose.bones.get(f"CTRL_{self.part_name}")
    if not follow_bone or not ctrl_bone:
        return

    angle = (int(self.rotate_to_round) - 1) / self.capacity * (2 * math.pi)
    ctrl_bone.rotation_quaternion = mathutils.Quaternion((0.0, 1.0, 0.0), angle)


# Clamps rotate_to_round to the new capacity if it was lowered below the current selection.
def _on_capacity_update(self, context):
    current = self.rotate_to_round
    if current and int(current) > self.capacity:
        self.rotate_to_round = str(self.capacity)


# Holds the cylinder's animation properties, registered on PoseBone so they are keyframeable.
class CylinderBoneProps(bpy.types.PropertyGroup):
    part_name: bpy.props.StringProperty()
    rig_name:  bpy.props.StringProperty()
    capacity: bpy.props.IntProperty(
        name="Capacity",
        default=6,
        min=1,
        description="Number of bullets cylinder can hold.",
        update=_on_capacity_update,
    )
    rotate_to_round: bpy.props.EnumProperty(
        name="Rotate to Round",
        items=_get_rotate_items,
        update=_on_rotate_to_round_update,
    )


# Updates HIDE_follow constraint influences and FK/IK control visibility when the blend slider changes.
def _on_chain_fk_ik_changed(self, context):
    ctrl_obj = bpy.data.objects.get(f"CTRL_{self.rig_name}")
    if not ctrl_obj:
        return
    base_name = self.base_name
    blend     = self.fk_ik
    is_ik     = blend >= 0.5

    for pb in ctrl_obj.pose.bones:
        if pb.name.startswith(f"HIDE_follow_{base_name}_") and len(pb.constraints) >= 2:
            pb.constraints[0].influence = 1.0 - blend
            pb.constraints[1].influence = blend

    for bone in ctrl_obj.data.bones:
        if bone.name.startswith(f"CTRL_FK_{base_name}_"):
            bone.hide = is_ik
        elif bone.name in (f"CTRL_IK_{base_name}", f"CTRL_IK_Pole_{base_name}", f"CTRL_IK_Top_{base_name}"):
            bone.hide = not is_ik



# Holds the FK/IK blend for a bone chain, registered on PoseBone so it is keyframeable.
class ChainBoneProps(bpy.types.PropertyGroup):
    base_name: bpy.props.StringProperty()
    rig_name:  bpy.props.StringProperty()
    fk_ik:     bpy.props.FloatProperty(
        name="FK / IK",
        default=0.0, min=0.0, max=1.0,
        update=_on_chain_fk_ik_changed,
    )


