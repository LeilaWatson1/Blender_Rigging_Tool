import bpy
import math
from .build import create_base_rig, armatures_visible, create_bone, update_rig_visibility
from .part_templates import create_cylinder_part


# Creates all bones for the revolver template: local, trigger, safety, cylinder_latch, cylinder,
# and the hidden follow bone for cylinder rotation logic.
# prefix is prepended to every bone name (e.g. "Cattleman" → DEF_Cattleman_trigger).
def create_revolver_template(context, rig_name, prefix=""):
    p = f"{prefix}_" if prefix else ""
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, f"{p}local",   True, True, parent_bone_name="root",       ctrl_radius=0.5,  ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0), bone_tail=(0.1, 0.0, 0.0), widget_type='circle_arrow')
    create_bone(context, rig_name, f"{p}trigger", True, True, parent_bone_name=f"{p}local",  ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.1), bone_tail=(0.1, 0.0, 0.1), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow', ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}safety",  True, True, parent_bone_name=f"{p}local",  ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.3), bone_tail=(0.1, 0.0, 0.3), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow',                               ctrl_color=(0.0, 0.0, 0.8))
    create_cylinder_part(context, rig_name, parent_bone_name=f"{p}local", base_name=f"{p}cylinder")
    update_rig_visibility(context, rig_name)


# Creates all bones for the pistol template: local, trigger, mag, and slide.
# prefix is prepended to every bone name (e.g. "Glock" → DEF_Glock_trigger).
def create_pistol_template(context, rig_name, prefix=""):
    p = f"{prefix}_" if prefix else ""
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, f"{p}local",   True, True, parent_bone_name="root",      ctrl_radius=0.5,  ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0),   bone_tail=(0.1, 0.0, 0.0),  widget_type='circle_arrow')
    create_bone(context, rig_name, f"{p}trigger", True, True, parent_bone_name=f"{p}local", ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.1),   bone_tail=(0.1, 0.0, 0.1),  ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow', ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}mag",   True, True, parent_bone_name=f"{p}local", ctrl_radius=0.1, ctrl_axis='Z', bone_head=(-0.06, 0.0, 0.1), bone_tail=(-0.06, 0.0, 0.0), ctrl_offset=(0.0, 0.05, 0.15), widget_type='double_arrow', ctrl_shape_rotation=math.pi / 2, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}slide", True, True, parent_bone_name=f"{p}local", ctrl_radius=0.1, ctrl_axis='X', bone_head=(0.0, 0.0, 0.2),   bone_tail=(0.1, 0.0, 0.2),   ctrl_offset=(-0.15, 0.05, 0.0), widget_type='double_arrow', ctrl_shape_rotation=0.0,          ctrl_color=(0.0, 0.0, 0.8))
    update_rig_visibility(context, rig_name)
