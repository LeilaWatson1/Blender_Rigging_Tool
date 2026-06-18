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
    props    = context.scene.rig_tool
    ctrl_obj = bpy.data.objects.get(f"CTRL_{props.rig_name}")
    if not ctrl_obj:
        return

    follow_bone = ctrl_obj.pose.bones.get(f"HIDE_follow_{self.part_name}")
    ctrl_bone   = ctrl_obj.pose.bones.get(f"CTRL_{self.part_name}")
    if not follow_bone or not ctrl_bone:
        return

    axis = None
    for c in follow_bone.constraints:
        if c.type == 'COPY_ROTATION':
            if c.use_x:   axis = 0
            elif c.use_y: axis = 1
            elif c.use_z: axis = 2
            break
    if axis is None:
        return

    angle    = (int(self.rotate_to_round) - 1) / self.capacity * (2 * math.pi)
    axis_map = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    quat     = mathutils.Quaternion(axis_map[axis], angle)
    ctrl_bone.rotation_quaternion = quat


# Clamps rotate_to_round to the new capacity if it was lowered below the current selection.
def _on_capacity_update(self, context):
    current = self.rotate_to_round
    if current and int(current) > self.capacity:
        self.rotate_to_round = str(self.capacity)


# Holds the cylinder's animation properties, registered on PoseBone so they are keyframeable.
class CylinderBoneProps(bpy.types.PropertyGroup):
    part_name: bpy.props.StringProperty()
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


def register():
    bpy.utils.register_class(CylinderBoneProps)
    bpy.types.PoseBone.cylinder_props = bpy.props.PointerProperty(type=CylinderBoneProps)

def unregister():
    del bpy.types.PoseBone.cylinder_props
    bpy.utils.unregister_class(CylinderBoneProps)
