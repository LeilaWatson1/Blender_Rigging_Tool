import bpy

# the variables tool reads from the UI

# Cached list for the current_rig enum — kept at module level to prevent Blender garbage-collecting it.
_rig_enum_cache = []


# Auto-fills parent_selector with the selected part's current parent when the list selection changes.
def _on_part_selected(self, context):
    props = context.scene.rig_tool
    if props.parts and props.active_part_index < len(props.parts):
        props.parent_selector = props.parts[props.active_part_index].parent_name


# Builds the enum items list from all DEF_ armatures present in the scene.
def _get_rig_items(self, context):
    global _rig_enum_cache
    _rig_enum_cache = []
              
    for obj in bpy.data.objects:
        if obj.name.startswith("DEF_"):
            rig_name = obj.name[4:]
            _rig_enum_cache.append((rig_name, rig_name, ""))
    if not _rig_enum_cache:
        _rig_enum_cache = [('NONE', 'None', '')]
    return _rig_enum_cache


# Clears the parts list and rebuilds it from the newly selected rig's armature bones.
def _on_current_rig_changed(self, context):
    props = context.scene.rig_tool
    props.parts.clear()
    props.active_part_index = 0

    if not props.current_rig or props.current_rig == 'NONE':
        return

    def_obj = bpy.data.objects.get(f"DEF_{props.current_rig}")
    if not def_obj:
        return

    def add_recursive(bone, parent_name="root", indent=0):
        part_name = bone.name[4:]
        item = props.parts.add()
        item.name        = part_name
        item.parent_name = parent_name
        item.indent      = indent
        for child in bone.children:
            add_recursive(child, part_name, indent + 1)

    root_bone = def_obj.data.bones.get("root")
    if root_bone:
        for child in root_bone.children:
            add_recursive(child, "root", 0)


# Defines the shape of a single item in the parts list: its name, parent, and indent depth.
class RigPartItem(bpy.types.PropertyGroup):
    # name is built into PropertyGroup
    parent_name: bpy.props.StringProperty()
    indent:      bpy.props.IntProperty(default=0)


# Holds all tool-level state stored on the scene: rig name, UI toggles, mode, and the parts list.
class RigToolProperties(bpy.types.PropertyGroup):
    current_rig: bpy.props.EnumProperty(
        name="Current Rig",
        items=_get_rig_items,
        update=_on_current_rig_changed,
    )
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
