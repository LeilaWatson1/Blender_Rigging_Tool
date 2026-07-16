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
from .properties               import PropRigPartItem, RigToolProperties
from .part_template_properties import CylinderBoneProps, ChainBoneProps
from .operators                import classes as operator_classes
from .panels                   import RIGTOOL_UL_parts_list, VIEW3D_PT_rig_tool
from .part_template_panels     import VIEW3D_PT_cylinder_props, VIEW3D_PT_chain_props


def register():
    for cls in (PropRigPartItem, RigToolProperties):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.rig_tool = bpy.props.PointerProperty(type=RigToolProperties)

    for cls in (CylinderBoneProps, ChainBoneProps):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)
    bpy.types.PoseBone.cylinder_props = bpy.props.PointerProperty(type=CylinderBoneProps)
    bpy.types.PoseBone.chain_props    = bpy.props.PointerProperty(type=ChainBoneProps)

    for cls in operator_classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)

    for cls in (RIGTOOL_UL_parts_list, VIEW3D_PT_rig_tool,
                VIEW3D_PT_cylinder_props, VIEW3D_PT_chain_props):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
        bpy.utils.register_class(cls)


def unregister():
    for cls in (VIEW3D_PT_chain_props, VIEW3D_PT_cylinder_props,
                VIEW3D_PT_rig_tool, RIGTOOL_UL_parts_list):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    for cls in reversed(operator_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    for attr in ("cylinder_props", "chain_props"):
        if hasattr(bpy.types.PoseBone, attr):
            delattr(bpy.types.PoseBone, attr)
    for cls in (ChainBoneProps, CylinderBoneProps):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    if hasattr(bpy.types.Scene, "rig_tool"):
        del bpy.types.Scene.rig_tool
    for cls in (RigToolProperties, PropRigPartItem):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
