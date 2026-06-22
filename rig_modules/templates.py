import bpy
import math
from .build import create_base_rig, armatures_visible, create_bone, update_rig_visibility
from .part_templates import create_cylinder_part


# Creates all bones for the revolver template: local, trigger, safety, cylinder_latch, cylinder,
# and the hidden follow bone for cylinder rotation logic.
def create_revolver_template(context, rig_name):
    def_obj, ctrl_obj, template_obj = create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, "local",   True, True, parent_bone_name="root",  ctrl_radius=0.5,  ctrl_axis='Z', bone_head=(0.0,   0.0, 0.0), bone_tail=(0.1,   0.0, 0.0), widget_type='circle_arrow')
    create_bone(context, rig_name, "trigger", True, True, parent_bone_name="local", ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0,   0.0, 0.1), bone_tail=(0.1,   0.0, 0.1), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow', ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, "safety",  True, True, parent_bone_name="local", ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0,   0.0, 0.3), bone_tail=(0.1,   0.0, 0.3), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow',                               ctrl_color=(0.0, 0.0, 0.8))
    create_cylinder_part(context, rig_name, parent_bone_name="local")
    update_rig_visibility(context, rig_name)
