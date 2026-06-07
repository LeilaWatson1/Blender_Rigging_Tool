import bpy
from .widgets import create_circle_widget


def _get_view3d_override(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return {'window': window, 'area': area, 'region': region}
    return {}


def create_base_rig(context, rig_name):
    if rig_name in bpy.data.collections:
        return (
            bpy.data.objects.get(f"DEF_{rig_name}"),
            bpy.data.objects.get(f"CTRL_{rig_name}"),
        )

    override = _get_view3d_override(context)

    rig_collection = bpy.data.collections.new(rig_name)
    context.scene.collection.children.link(rig_collection)

    wgt_collection = bpy.data.collections.new(f"WGTS_{rig_name}")
    rig_collection.children.link(wgt_collection)
    wgt_collection.hide_viewport = True
    wgt_collection.hide_render = True

    def_armature = bpy.data.armatures.new(f"DEF_{rig_name}")
    def_obj = bpy.data.objects.new(f"DEF_{rig_name}", def_armature)
    rig_collection.objects.link(def_obj)

    ctrl_armature = bpy.data.armatures.new(f"CTRL_{rig_name}")
    ctrl_obj = bpy.data.objects.new(f"CTRL_{rig_name}", ctrl_armature)
    rig_collection.objects.link(ctrl_obj)

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    root_bone = def_armature.edit_bones.new("root")
    root_bone.head = (0.0, 0.0, 0.0)
    root_bone.tail = (0.0, 0.1, 0.0)
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='EDIT')
    ctrl_root = ctrl_armature.edit_bones.new("CTRL_root")
    ctrl_root.head = (0.0, 0.0, 0.0)
    ctrl_root.tail = (0.0, 0.1, 0.0)
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    circle_widget = create_circle_widget(f"WGT_{rig_name}_root", wgt_collection)

    context.view_layer.objects.active = ctrl_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    ctrl_root_pose = ctrl_obj.pose.bones["CTRL_root"]
    ctrl_root_pose.custom_shape = circle_widget
    ctrl_root_pose.use_custom_shape_bone_size = False
    ctrl_root_pose.color.palette = 'CUSTOM'
    ctrl_root_pose.color.custom.normal = (0.8, 0.0, 0.0)
    ctrl_root_pose.color.custom.select = (1.0, 0.4, 0.4)
    ctrl_root_pose.color.custom.active = (1.0, 0.6, 0.6)
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    context.view_layer.objects.active = def_obj
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='POSE')
    root_pose = def_obj.pose.bones["root"]
    copy_transforms = root_pose.constraints.new('COPY_TRANSFORMS')
    copy_transforms.target = ctrl_obj
    copy_transforms.subtarget = "CTRL_root"
    with context.temp_override(**override):
        bpy.ops.object.mode_set(mode='OBJECT')

    return def_obj, ctrl_obj