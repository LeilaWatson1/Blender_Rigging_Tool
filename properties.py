import bpy

# the variables tool reads from the UI

def _on_part_selected(self, context):
    props = context.scene.rig_tool
    if props.parts and props.active_part_index < len(props.parts):
        props.parent_selector = props.parts[props.active_part_index].parent_name


class RigPartItem(bpy.types.PropertyGroup):
    # name is built into PropertyGroup
    parent_name: bpy.props.StringProperty()
    indent:      bpy.props.IntProperty(default=0)


class RigToolProperties(bpy.types.PropertyGroup):
    rig_name: bpy.props.StringProperty(
        name="Rig Name",
        default="MyRig",
    )
    bone_name: bpy.props.StringProperty(
        name="Bone Name",
        default="Bone",
    )
    is_deforming: bpy.props.BoolProperty(
        name="Is Deforming",
        default=True,
    )
    has_control: bpy.props.BoolProperty(
        name="Has Control",
        default=True,
    )
    show_templates: bpy.props.BoolProperty(
        name="Templates",
        default=False,
    )
    show_add_bone_ui: bpy.props.BoolProperty(
        default=False,
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('TEMPLATE', "Template Mode", ""),
            ('POSE', "Pose Mode", ""),
        ],
        default='TEMPLATE',
    )
    parts:             bpy.props.CollectionProperty(type=RigPartItem)
    active_part_index: bpy.props.IntProperty(default=0, update=_on_part_selected)
    show_parts_list:   bpy.props.BoolProperty(name="Parts List", default=True)
    parent_selector:   bpy.props.StringProperty(name="Parent")

def register():
    bpy.utils.register_class(RigPartItem)
    bpy.utils.register_class(RigToolProperties)
    bpy.types.Scene.rig_tool = bpy.props.PointerProperty(type=RigToolProperties)

def unregister():
    del bpy.types.Scene.rig_tool
    bpy.utils.unregister_class(RigToolProperties)
    bpy.utils.unregister_class(RigPartItem)
