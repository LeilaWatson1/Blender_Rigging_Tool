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
from . import properties, operators, panels

def register():
    properties.register()
    operators.register()
    panels.register()

def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()