import bpy
import math
from .build import create_base_rig, armatures_visible, create_bone, update_rig_visibility
from .part_templates import create_cylinder_part


# Creates all bones for the revolver template: local, trigger, safety, cylinder_latch, cylinder,
# and the hidden follow bone for cylinder rotation logic.
# prefix is prepended to every bone name (e.g. "Cattleman" → DEF_Cattleman_trigger).
# rig_name: the rig to build the template bones in.
# prefix: string prepended to every bone name; empty string uses bare names.
# grip_socket: True to add a grip attachment SKT_ bone.
# ejector_socket: True to add an ejector attachment SKT_ bone.
# flash_socket: True to add a flash-hider attachment SKT_ bone.
def create_revolver_template(context, rig_name, prefix="", grip_socket=True, ejector_socket=True, flash_socket=True):
    p = f"{prefix}_" if prefix else ""
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, f"{p}local",   True, True, parent_bone_name="root",       ctrl_radius=0.5,  ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0), bone_tail=(0.1, 0.0, 0.0), widget_type='circle_arrow')
    create_bone(context, rig_name, f"{p}trigger", True, True, parent_bone_name=f"{p}local",  ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.1), bone_tail=(0.1, 0.0, 0.1), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow', ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}safety",  True, True, parent_bone_name=f"{p}local",  ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.3), bone_tail=(0.1, 0.0, 0.3), ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow',                               ctrl_color=(0.0, 0.0, 0.8))
    create_cylinder_part(context, rig_name, parent_bone_name=f"{p}local", base_name=f"{p}cylinder")
    if grip_socket or ejector_socket or flash_socket:
        armatures_visible(rig_name)
    if grip_socket:
        create_bone(context, rig_name, f"{p}grip",    True, False, parent_bone_name=f"{p}local",
                    bone_head=(-0.15, 0.0, 0.05), bone_tail=(-0.05, 0.0, 0.05), bone_prefix="SKT")
    if ejector_socket:
        create_bone(context, rig_name, f"{p}ejector", True, False, parent_bone_name=f"{p}local",
                    bone_head=(0.1, 0.0, 0.2), bone_tail=(0.2, 0.0, 0.2), bone_prefix="SKT")
    if flash_socket:
        create_bone(context, rig_name, f"{p}flash",   True, False, parent_bone_name=f"{p}local",
                    bone_head=(0.3, 0.0, 0.2), bone_tail=(0.4, 0.0, 0.2), bone_prefix="SKT")
    update_rig_visibility(context, rig_name)


# Creates all bones for the pistol template: local, trigger, mag, and slide.
# prefix is prepended to every bone name (e.g. "Glock" → DEF_Glock_trigger).
# rig_name: the rig to build the template bones in.
# prefix: string prepended to every bone name; empty string uses bare names.
# grip_socket: True to add a grip attachment SKT_ bone.
# ejector_socket: True to add an ejector attachment SKT_ bone.
# flash_socket: True to add a flash-hider attachment SKT_ bone.
def create_pistol_template(context, rig_name, prefix="", grip_socket=True, ejector_socket=True, flash_socket=True):
    p = f"{prefix}_" if prefix else ""
    create_base_rig(context, rig_name)
    armatures_visible(rig_name)

    create_bone(context, rig_name, f"{p}local",   True, True, parent_bone_name="root",      ctrl_radius=0.5,  ctrl_axis='Z', bone_head=(0.0, 0.0, 0.0),   bone_tail=(0.1, 0.0, 0.0),  widget_type='circle_arrow')
    create_bone(context, rig_name, f"{p}trigger", True, True, parent_bone_name=f"{p}local", ctrl_radius=0.05, ctrl_axis='X', bone_head=(0.0, 0.0, 0.1),   bone_tail=(0.1, 0.0, 0.1),  ctrl_offset=(-0.15, 0.0, 0.0), widget_type='arc_arrow', ctrl_shape_rotation=math.pi, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}mag",     True, True, parent_bone_name=f"{p}local", ctrl_radius=0.1,  ctrl_axis='Z', bone_head=(-0.06, 0.0, 0.1), bone_tail=(-0.06, 0.0, 0.0), ctrl_offset=(0.0, 0.05, 0.15), widget_type='double_arrow', ctrl_shape_rotation=math.pi / 2, ctrl_color=(0.0, 0.0, 0.8))
    create_bone(context, rig_name, f"{p}slide",   True, True, parent_bone_name=f"{p}local", ctrl_radius=0.1,  ctrl_axis='X', bone_head=(0.0, 0.0, 0.2),   bone_tail=(0.1, 0.0, 0.2),   ctrl_offset=(-0.15, 0.05, 0.0), widget_type='double_arrow', ctrl_shape_rotation=0.0, ctrl_color=(0.0, 0.0, 0.8))
    if grip_socket:
        create_bone(context, rig_name, f"{p}grip",    True, False, parent_bone_name=f"{p}local",
                    bone_head=(-0.06, 0.0, 0.05), bone_tail=(0.04, 0.0, 0.05), bone_prefix="SKT")
    if ejector_socket:
        create_bone(context, rig_name, f"{p}ejector", True, False, parent_bone_name=f"{p}local",
                    bone_head=(0.0, 0.0, 0.15), bone_tail=(0.1, 0.0, 0.15), bone_prefix="SKT")
    if flash_socket:
        create_bone(context, rig_name, f"{p}flash",   True, False, parent_bone_name=f"{p}local",
                    bone_head=(0.2, 0.0, 0.15), bone_tail=(0.3, 0.0, 0.15), bone_prefix="SKT")
    update_rig_visibility(context, rig_name)
