import bpy

# the variables tool reads from the UI

# Cached list for the current_rig enum — kept at module level to prevent Blender garbage-collecting it.
_rig_enum_cache = []


# Auto-fills parent_selector with the selected part's current parent when the list selection changes.
# Also refreshes the Widgets panel fields if it is currently open.
def _on_part_selected(self, context):
    props = context.scene.rig_tool
    if props.parts and props.active_part_index < len(props.parts):
        props.parent_selector = props.parts[props.active_part_index].parent_name
    if props.show_edit_widget_ui:
        from .operators import _load_widget_settings
        _load_widget_settings(context)


# Loads the selected bone's widget settings into the edit fields when the Widgets panel is opened.
def _on_show_edit_widget_changed(self, context):
    if self.show_edit_widget_ui:
        from .operators import _load_widget_settings
        _load_widget_settings(context)


# Builds the enum items list from all DEF_ armatures present in the scene.
# Returns: list of (identifier, name, description) tuples for the EnumProperty.
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


# Sets scene unit scale to 0.01 (cm) when checked, restoring to 1.0 when unchecked.
def _on_scale_on_export_changed(self, context):
    context.scene.unit_settings.scale_length = 0.01 if self.scale_on_export else 1.0


# Shared guard check used by all widget edit callbacks.
def _widget_guard(self):
    from .operators import _widget_load_guard
    return _widget_load_guard[0] or not self.current_rig or self.current_rig == 'NONE'

# Rebuilds the widget mesh with only the widget type changed.
def _on_widget_type_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_mesh
    _apply_widget_mesh(context, wtype=self.edit_widget)

# Rebuilds the widget mesh with only the axis changed.
def _on_widget_axis_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_mesh
    _apply_widget_mesh(context, axis=self.edit_ctrl_axis)

# Rebuilds the widget mesh with only the offset changed.
def _on_widget_offset_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_mesh
    _apply_widget_mesh(context, offset=(self.edit_ctrl_offset_x, self.edit_ctrl_offset_y, self.edit_ctrl_offset_z))

# Rebuilds the widget mesh with only the shape rotation changed.
def _on_widget_rotation_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_mesh
    _apply_widget_mesh(context, shape_rotation=self.edit_shape_rotation)

# Rebuilds the widget mesh with only the radius changed.
def _on_widget_radius_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_mesh
    _apply_widget_mesh(context, ctrl_radius=self.edit_ctrl_radius)

# Updates only the bone color without rebuilding the widget mesh.
def _on_widget_color_changed(self, context):
    if _widget_guard(self):
        return
    from .operators import _apply_widget_color
    _apply_widget_color(context)


# Shows or hides the collection for the current rig.
def _on_show_current_rig_changed(self, context):
    rig_name = self.current_rig
    if not rig_name or rig_name == 'NONE':
        return
    col = bpy.data.collections.get(rig_name)
    if col:
        col.hide_viewport = not self.show_current_rig


# Shows or hides collections for all rigs other than the current one.
def _on_show_other_rigs_changed(self, context):
    current = self.current_rig
    hidden  = not self.show_other_rigs
    for obj in bpy.data.objects:
        if obj.name.startswith("DEF_"):
            rig_name = obj.name[4:]
            if rig_name != current:
                col = bpy.data.collections.get(rig_name)
                if col:
                    col.hide_viewport = hidden


# Sets export format to the best default for the selected engine.
def _on_engine_changed(self, context):
    if self.export_engine == 'UNREAL':
        self.export_format = 'FBX'
    elif self.export_engine == 'UNITY':
        self.export_format = 'FBX'
    elif self.export_engine == 'GODOT':
        self.export_format = 'GLTF'


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
        def_pb = def_obj.pose.bones.get(bone.name)
        if def_pb and "chain_part_name" in def_pb:
            item                 = props.parts.add()
            item.name            = str(def_pb["chain_part_name"])
            item.parent_name     = parent_name
            item.indent          = indent
            item.is_fk_ik_chain  = True
            item.chain_base_name = str(def_pb["chain_base_name"])
            return
        part_name        = bone.name[4:]
        item             = props.parts.add()
        item.name        = part_name
        item.parent_name = parent_name
        item.indent      = indent
        item.is_socket   = bone.name.startswith("SKT_")
        for child in bone.children:
            add_recursive(child, part_name, indent + 1)

    root_bone = def_obj.data.bones.get("root")
    if root_bone:
        for child in root_bone.children:
            add_recursive(child, "root", 0)

    col = bpy.data.collections.get(props.current_rig)
    if col:
        props.show_current_rig = not col.hide_viewport

    other_cols = [
        bpy.data.collections.get(obj.name[4:])
        for obj in bpy.data.objects
        if obj.name.startswith("DEF_") and obj.name[4:] != props.current_rig
    ]
    visible_cols = [c for c in other_cols if c]
    props.show_other_rigs = bool(visible_cols) and all(not c.hide_viewport for c in visible_cols)


# Defines the shape of a single item in the parts list: its name, parent, and indent depth.
class PropRigPartItem(bpy.types.PropertyGroup):
    # name is built into PropertyGroup
    parent_name:     bpy.props.StringProperty()
    indent:          bpy.props.IntProperty(default=0)
    is_socket:       bpy.props.BoolProperty(default=False)
    is_fk_ik_chain:  bpy.props.BoolProperty(default=False)
    chain_base_name: bpy.props.StringProperty()


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
    bone_widget: bpy.props.EnumProperty(
        name="Widget",
        items=[
            ('circle',       "Circle",       ""),
            ('arc_arrow',    "Arc Arrow",    ""),
            ('circle_arrow', "Circle Arrow", ""),
            ('double_arrow', "Double Arrow", ""),
        ],
        default='circle',
    )
    show_edit_widget_ui: bpy.props.BoolProperty(name="Widgets", default=False, update=_on_show_edit_widget_changed)
    edit_widget:         bpy.props.EnumProperty(
        name="Widget",
        items=[
            ('circle',       "Circle",       ""),
            ('arc_arrow',    "Arc Arrow",    ""),
            ('circle_arrow', "Circle Arrow", ""),
            ('double_arrow', "Double Arrow", ""),
        ],
        default='circle',
        update=_on_widget_type_changed,
    )
    edit_ctrl_offset_x:  bpy.props.FloatProperty(name="X", default=0.0, update=_on_widget_offset_changed)
    edit_ctrl_offset_y:  bpy.props.FloatProperty(name="Y", default=0.0, update=_on_widget_offset_changed)
    edit_ctrl_offset_z:  bpy.props.FloatProperty(name="Z", default=0.0, update=_on_widget_offset_changed)
    edit_ctrl_axis:      bpy.props.EnumProperty(
        name="Ctrl Axis",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
        default='X',
        update=_on_widget_axis_changed,
    )
    edit_shape_rotation: bpy.props.FloatProperty(name="Shape Rotation", default=0.0, update=_on_widget_rotation_changed)
    edit_ctrl_radius:    bpy.props.FloatProperty(name="Scale", default=0.1, min=0.001, update=_on_widget_radius_changed)
    edit_ctrl_color:     bpy.props.EnumProperty(
        name="Ctrl Color",
        items=[
            ('RED',    "Red",    ""),
            ('ORANGE', "Orange", ""),
            ('YELLOW', "Yellow", ""),
            ('GREEN',  "Green",  ""),
            ('BLUE',   "Blue",   ""),
            ('PURPLE', "Purple", ""),
            ('WHITE',  "White",  ""),
        ],
        default='RED',
        update=_on_widget_color_changed,
    )
    show_current_rig: bpy.props.BoolProperty(
        name="Current Rig",
        default=True,
        description="Changes visibility for current rig.",
        update=_on_show_current_rig_changed,
    )
    show_other_rigs: bpy.props.BoolProperty(
        name="All Rigs",
        default=False,
        description="Changes visibility of all rigs that are not current.",
        update=_on_show_other_rigs_changed,
    )
    show_templates: bpy.props.BoolProperty(
        name="Templates",
        default=False,
    )
    selected_template: bpy.props.EnumProperty(
        name="Template",
        items=[
            ('revolver', "Revolver", "Contains: local, trigger, safety, cylinder_latch, and cylinder parts"),
            ('pistol',   "Pistol",   "Contains: local, trigger, mag, and slide parts"),
        ],
        default='revolver',
    )
    template_prefix: bpy.props.StringProperty(
        name="Name Prefix",
        default="",
    )
    template_grip_socket: bpy.props.BoolProperty(
        name="Grip Socket",
        default=True,
        description="Adds a socket for the grip",
    )
    template_ejector_socket: bpy.props.BoolProperty(
        name="Ejector Socket",
        default=True,
        description="Adds a socket for the ejector",
    )
    template_flash_socket: bpy.props.BoolProperty(
        name="Flash Socket",
        default=True,
        description="Adds a socket for the flash hider",
    )
    selected_part_type: bpy.props.EnumProperty(
        name="Part Type",
        items=[
            ('single_bone', "Single Bone", "A DEF/CTRL bone pair"),
            ('socket_bone', "Socket Bone", "A non-deforming bone in the export skeleton for use as an attachment socket"),
            ('bone_chain',  "Bone Chain",  "A chain of connected bones along the forward axis"),
            ('cylinder',    "Cylinder",    "A multi-bone cylinder part",),
            ('bullet_feed',    "Bullet Feed",    "A chain of bones that loop along a curve.",),
        ],
        default='single_bone',
    )
    socket_name: bpy.props.StringProperty(
        name="Bone Name",
        default="socket",
    )
    socket_has_control: bpy.props.BoolProperty(
        name="Has Control",
        default=True,
    )
    socket_widget: bpy.props.EnumProperty(
        name="Widget",
        items=[
            ('circle',       "Circle",       ""),
            ('arc_arrow',    "Arc Arrow",    ""),
            ('circle_arrow', "Circle Arrow", ""),
            ('double_arrow', "Double Arrow", ""),
        ],
        default='circle',
    )
    chain_name: bpy.props.StringProperty(
        name="Bone Name",
        default="chain",
    )
    chain_is_deforming: bpy.props.BoolProperty(
        name="Is Deforming",
        default=True,
    )
    chain_has_control: bpy.props.BoolProperty(
        name="Has Control",
        default=True,
    )
    chain_widget: bpy.props.EnumProperty(
        name="Widget",
        items=[
            ('circle',       "Circle",       ""),
            ('arc_arrow',    "Arc Arrow",    ""),
            ('circle_arrow', "Circle Arrow", ""),
            ('double_arrow', "Double Arrow", ""),
        ],
        default='circle',
    )
    chain_length: bpy.props.IntProperty(
        name="Chain Length",
        default=2,
        min=2,
    )
    chain_fk_ik: bpy.props.EnumProperty(
        name="FK/IK",
        items=[
            ('BOTH', "Both", ""),
            ('FK',   "FK",   ""),
            ('IK',   "IK",   ""),
        ],
        default='BOTH',
    )
    cylinder_name: bpy.props.StringProperty(
        name="Name",
        default="cylinder",
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('OBJECT', "Object Mode", ""),
            ('TEMPLATE', "Template Mode", ""),
            ('POSE', "Pose Mode", ""),
        ],
        default='OBJECT',
    )
    bone_amount: bpy.props.IntProperty(
        name="Bone Amount",
        default=8,
        min=2,
    )
    curve_length: bpy.props.FloatProperty(
        name="Curve Length",
        default=2,
        min=0.0001,
    )
    show_parts:        bpy.props.BoolProperty(name="Parts", default=False)
    show_weights:      bpy.props.BoolProperty(name="Weights", default=False)
    show_export:       bpy.props.BoolProperty(name="Export", default=False)
    export_engine:     bpy.props.EnumProperty(
                           name="Engine",
                           items=[('UNREAL','Unreal',''), ('UNITY','Unity',''), ('GODOT','Godot','')],
                           default='UNREAL',
                           update=_on_engine_changed,
                       )
    export_format:     bpy.props.EnumProperty(
                           name="Format",
                           items=[('FBX','FBX',''), ('GLTF','glTF','')],
                           default='FBX',
                       )
    scale_on_export:   bpy.props.BoolProperty(
                           name="Scene Scaled to Match Unreal Units",
                           default=True,
                           description="When checked, sets the scene unit scale to 0.01 so 1 Blender unit = 1cm, matching Unreal Engine's scale.",
                           update=_on_scale_on_export_changed,
                       )
    front_axis:        bpy.props.EnumProperty(
                           name="Front Axis",
                           items=[('X', 'X', ''), ('Y', 'Y', '')],
                           default='X',
                       )
    parts:             bpy.props.CollectionProperty(type=PropRigPartItem)
    active_part_index: bpy.props.IntProperty(default=0, update=_on_part_selected)
    show_parts_list:   bpy.props.BoolProperty(name="Parts List", default=True)
    parent_selector:   bpy.props.StringProperty(name="Parent")
    rename_input:      bpy.props.StringProperty(name="")

