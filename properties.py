import bpy

# the variables tool reads from the UI


# Auto-fills parent_selector with the selected part's current parent when the list selection changes.
def _on_part_selected(self, context):
    props = context.scene.rig_tool
    if props.parts and props.active_part_index < len(props.parts):
        props.parent_selector = props.parts[props.active_part_index].parent_name


# Defines the shape of a single item in the parts list: its name, parent, and indent depth.
class RigPartItem(bpy.types.PropertyGroup):
    # name is built into PropertyGroup
    parent_name: bpy.props.StringProperty()
    indent:      bpy.props.IntProperty(default=0)


# Holds all tool-level state stored on the scene: rig name, UI toggles, mode, and the parts list.
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
    show_add_cylinder_ui: bpy.props.BoolProperty(
        default=False,
    )
    cylinder_name: bpy.props.StringProperty(
        name="Name",
        default="cylinder",
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('TEMPLATE', "Template Mode", ""),
            ('POSE', "Pose Mode", ""),
        ],
        default='TEMPLATE',
    )
    show_parts:        bpy.props.BoolProperty(name="Parts", default=False)
    show_export:       bpy.props.BoolProperty(name="Export", default=False)
    front_axis:        bpy.props.EnumProperty(
                           name="Front Axis",
                           items=[('X', 'X', ''), ('Y', 'Y', '')],
                           default='X',
                       )
    parts:             bpy.props.CollectionProperty(type=RigPartItem)
    active_part_index: bpy.props.IntProperty(default=0, update=_on_part_selected)
    show_parts_list:   bpy.props.BoolProperty(name="Parts List", default=True)
    parent_selector:   bpy.props.StringProperty(name="Parent")
    rename_input:      bpy.props.StringProperty(name="")

def register():
    bpy.utils.register_class(RigPartItem)
    bpy.utils.register_class(RigToolProperties)
    bpy.types.Scene.rig_tool = bpy.props.PointerProperty(type=RigToolProperties)

def unregister():
    del bpy.types.Scene.rig_tool
    bpy.utils.unregister_class(RigToolProperties)
    bpy.utils.unregister_class(RigPartItem)
