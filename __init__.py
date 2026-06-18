bl_info = {
    "name": "Prop Rigging Tool",
    "author": "Leila Watson",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Rig Tool",
    "description": "Modular rigging tool for game props targeting Unreal Engine",
    "category": "Rigging",
}

import bpy
from . import properties, part_template_properties, operators, panels, part_template_panels

def register():
    properties.register()
    part_template_properties.register()
    operators.register()
    panels.register()
    part_template_panels.register()

def unregister():
    part_template_panels.unregister()
    panels.unregister()
    operators.unregister()
    part_template_properties.unregister()
    properties.unregister()