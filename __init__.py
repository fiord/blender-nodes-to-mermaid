"""
Blender Add-on: Node Tree to Diagram Converter

This add-on converts Blender's node trees to Mermaid or PlantUML diagram formats for easy sharing and documentation.
It supports all main node tree types: Shader, Compositor, Texture, and Geometry.
"""

import bpy
import os
import tempfile
import traceback

bl_info = {
    "name": "Node to Diagram Converter",
    "author": "blender-nodes-to-mermaid contributors",
    "version": (1, 5, 0),
    "blender": (5, 0, 0),
    "location": "Node Editor > Sidebar > Diagram",
    "description": "Export node trees to Mermaid or PlantUML diagram formats with parameters",
    "category": "Node",
}

# Try to import optional dependencies
try:
    import pyperclip
    print(f"[{bl_info['name']}] Optional dependency 'pyperclip' found. Clipboard functionality enabled.")
    HAS_PYPERCLIP = True
except ImportError:
    print(f"[{bl_info['name']}] Optional dependency 'pyperclip' not found. Clipboard functionality will be disabled.")
    HAS_PYPERCLIP = False

# Configuration constants
MAX_DISPLAYED_PARAMETERS = 5  # Maximum number of parameters to display in node labels
NOTE_POSITIONS = ['right', 'left', 'top', 'bottom']  # Positions for PlantUML notes

def sanitize_identifier(name):
    """Sanitize node name for use as an identifier in diagrams (class names, state names, etc.)."""
    # For diagrams, identifiers must be valid (no spaces)
    # Replace spaces and special characters with underscores
    sanitized = ''.join(c if c.isalnum() else '_' for c in name)
    # Remove consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = 'Node_' + sanitized
    return sanitized or 'Node'


def get_node_parameters(node):
    """
    Extract important parameters from a node for documentation.
    
    Args:
        node: The Blender node to extract parameters from
        
    Returns:
        Dictionary of parameter names and values
    """
    params = {}
    
    # Common properties to skip (internal or not useful for sharing)
    skip_props = {
        'rna_type', 'name', 'label', 'location', 'width', 'height', 'dimensions',
        'select', 'show_options', 'show_preview', 'show_texture', 'hide',
        'mute', 'parent', 'use_custom_color', 'color', 'inputs', 'outputs',
        'internal_links', 'type', 'bl_idname', 'bl_label', 'bl_rna',
        'bl_description', 'bl_icon', 'bl_static_type', 'bl_width_default',
        'bl_width_max', 'bl_width_min', 'bl_height_default', 'bl_height_max',
        'bl_height_min', 'shading_compatibility', 'width_hidden'
    }
    
    # Try to get all properties
    try:
        for prop_name in dir(node):
            # Skip private and magic methods
            if prop_name.startswith('_'):
                continue
            # Skip methods
            prop_value = getattr(node, prop_name, None)
            if callable(prop_value):
                continue
            # Skip properties in skip list
            if prop_name in skip_props:
                continue
                
            try:
                value = prop_value
                
                # Skip None values and complex objects
                if value is None:
                    continue
                    
                # Handle different value types
                if isinstance(value, (int, float, str, bool)):
                    params[prop_name] = value
                elif isinstance(value, (tuple, list)) and len(value) <= 4:
                    # Include small tuples/lists (like color, vector)
                    if all(isinstance(v, (int, float)) for v in value):
                        params[prop_name] = value
                elif hasattr(value, 'name'):
                    # For objects with name attribute (like materials, images, etc.)
                    params[prop_name] = value.name
                    
            except (AttributeError, TypeError):
                # Skip properties that can't be accessed
                continue
                
    except Exception as e:
        # If something goes wrong, just return what we have
        print(f"Warning: Could not extract all parameters from node: {e}")
    
    return params


def build_class_diagram(node_tree):
    """
    Build Mermaid class diagram from a node tree.
    This format represents nodes with their properties and parameters.
    
    Node parameters are automatically included for complete documentation.
    
    Args:
        node_tree: The Blender node tree to convert
        
    Returns:
        String containing Mermaid class diagram code
    """
    if node_tree is None:
        return ""
    
    mermaid_lines = []
    
    # Create a mapping of nodes to their class IDs
    node_classes = {}
    class_counters = {}
    
    # First pass: Create class definitions for each node
    for node in node_tree.nodes:
        # Create unique class name
        base_class_name = sanitize_identifier(node.name)
        
        # Handle class name collisions
        if base_class_name in class_counters:
            class_counters[base_class_name] += 1
            class_name = f"{base_class_name}_{class_counters[base_class_name]}"
        else:
            class_counters[base_class_name] = 0
            class_name = base_class_name
        
        node_classes[node.name] = class_name
        
        # Get node type name
        node_type = node.bl_idname
        for prefix_to_remove in ['ShaderNode', 'CompositorNode', 'GeometryNode', 'TextureNode', 'Node']:
            if node_type.startswith(prefix_to_remove):
                node_type = node_type[len(prefix_to_remove):]
                break
        
        # Start class definition
        mermaid_lines.append(f"class {class_name}{{")
        
        # Add node type as a property
        mermaid_lines.append(f"    +String type: {node_type}")
        
        # Add parameters
        params = get_node_parameters(node)
        if params:
                # Limit parameters
                important_params = list(params.items())[:MAX_DISPLAYED_PARAMETERS]
                
                for key, value in important_params:
                    # Determine type and format value
                    if isinstance(value, bool):
                        param_type = "Boolean"
                        value_str = str(value)
                    elif isinstance(value, int):
                        param_type = "Integer"
                        value_str = str(value)
                    elif isinstance(value, float):
                        param_type = "Float"
                        value_str = f"{value:.3f}"
                    elif isinstance(value, str):
                        param_type = "String"
                        value_str = f'"{value}"'
                    elif isinstance(value, (tuple, list)):
                        param_type = "Vector"
                        formatted_values = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in value]
                        value_str = f"({', '.join(formatted_values)})"
                    else:
                        param_type = "Object"
                        value_str = str(value)
                    
                    # Add parameter line with type and value
                    mermaid_lines.append(f"    +{param_type} {key}: {value_str}")
        
        # Add input/output socket counts as properties
        if hasattr(node, 'inputs') and len(node.inputs) > 0:
            mermaid_lines.append(f"    +inputs: {len(node.inputs)}")
        if hasattr(node, 'outputs') and len(node.outputs) > 0:
            mermaid_lines.append(f"    +outputs: {len(node.outputs)}")
        
        # Close class definition
        mermaid_lines.append("}")
        mermaid_lines.append("")  # Add blank line for readability
    
    # Second pass: Create relationships (connections between nodes)
    for link in node_tree.links:
        try:
            if not link.is_valid:
                continue
            
            from_node = link.from_node
            to_node = link.to_node
            
            if from_node.name not in node_classes or to_node.name not in node_classes:
                continue
            
            from_class = node_classes[from_node.name]
            to_class = node_classes[to_node.name]
            
            # Get socket names for the relationship label
            from_socket = link.from_socket.name
            to_socket = link.to_socket.name
            
            # Create relationship with label
            if from_socket and to_socket:
                label = f"{from_socket} → {to_socket}"
            elif from_socket:
                label = from_socket
            elif to_socket:
                label = to_socket
            else:
                label = ""
            
            # Use association relationship with label
            if label:
                mermaid_lines.append(f"{from_class} --> {to_class} : {label}")
            else:
                mermaid_lines.append(f"{from_class} --> {to_class}")
                
        except Exception as e:
            print(f"Warning: Skipped link in class diagram: {e}")
            continue
    
    # Third pass: Handle node groups
    # In class diagrams, we can show groups using composition relationships
    for node in node_tree.nodes:
        if hasattr(node, 'node_tree') and node.node_tree is not None:
            node_class = node_classes.get(node.name)
            if node_class:
                # Add a comment about the group content
                mermaid_lines.append("")
                mermaid_lines.append(f"%% {node_class} is a node group containing {len(node.node_tree.nodes)} nodes")
                
                # Optionally create a namespace-like structure by listing contained nodes
                if len(node.node_tree.nodes) <= 3:  # Only show details for small groups
                    mermaid_lines.append(f"%% Group '{node.name}' contains:")
                    for inner_node in node.node_tree.nodes:
                        mermaid_lines.append(f"%%   - {inner_node.name} ({inner_node.bl_idname})")
    
    return "\n".join(mermaid_lines)


def build_plantuml_state_diagram(node_tree):
    """
    Build PlantUML state diagram from a node tree.
    This format represents nodes as states with transitions between them.
    
    Node parameters are automatically included for complete documentation.
    
    Args:
        node_tree: The Blender node tree to convert
        
    Returns:
        String containing PlantUML state diagram code
    """
    if node_tree is None:
        return ""
    
    plantuml_lines = []
    
    # Create a mapping of nodes to their state IDs
    node_states = {}
    state_counters = {}
    
    # First pass: Create state definitions for each node
    for node in node_tree.nodes:
        # Create unique state name
        base_state_name = sanitize_identifier(node.name)
        
        # Handle state name collisions
        if base_state_name in state_counters:
            state_counters[base_state_name] += 1
            state_name = f"{base_state_name}_{state_counters[base_state_name]}"
        else:
            state_counters[base_state_name] = 0
            state_name = base_state_name
        
        node_states[node.name] = state_name
        
        # Get node type name
        node_type = node.bl_idname
        for prefix_to_remove in ['ShaderNode', 'CompositorNode', 'GeometryNode', 'TextureNode', 'Node']:
            if node_type.startswith(prefix_to_remove):
                node_type = node_type[len(prefix_to_remove):]
                break
        
        # Create state definition with description
        state_description_lines = []
        state_description_lines.append(f"Type: {node_type}")
        
        # Add parameters
        params = get_node_parameters(node)
        if params:
            # Limit parameters
            important_params = list(params.items())[:MAX_DISPLAYED_PARAMETERS]
            
            for key, value in important_params:
                # Format value
                if isinstance(value, bool):
                    value_str = str(value)
                elif isinstance(value, int):
                    value_str = str(value)
                elif isinstance(value, float):
                    value_str = f"{value:.3f}"
                elif isinstance(value, str):
                    value_str = f'"{value}"'
                elif isinstance(value, (tuple, list)):
                    formatted_values = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in value]
                    value_str = f"({', '.join(formatted_values)})"
                else:
                    value_str = str(value)
                
                state_description_lines.append(f"{key}: {value_str}")
        
        # Add input/output socket counts
        if hasattr(node, 'inputs') and len(node.inputs) > 0:
            state_description_lines.append(f"Inputs: {len(node.inputs)}")
        if hasattr(node, 'outputs') and len(node.outputs) > 0:
            state_description_lines.append(f"Outputs: {len(node.outputs)}")
        
        # Create state with description (always has at least the Type field)
        plantuml_lines.append(f"state {state_name} {{")
        for desc_line in state_description_lines:
            plantuml_lines.append(f"  {desc_line}")
        plantuml_lines.append("}")
        
        plantuml_lines.append("")  # Add blank line for readability
    
    # Second pass: Create transitions (connections between nodes)
    for link in node_tree.links:
        try:
            if not link.is_valid:
                continue
            
            from_node = link.from_node
            to_node = link.to_node
            
            if from_node.name not in node_states or to_node.name not in node_states:
                continue
            
            from_state = node_states[from_node.name]
            to_state = node_states[to_node.name]
            
            # Get socket names for the transition label
            from_socket = link.from_socket.name
            to_socket = link.to_socket.name
            
            # Create transition with label
            if from_socket and to_socket:
                label = f"{from_socket} → {to_socket}"
            elif from_socket:
                label = from_socket
            elif to_socket:
                label = to_socket
            else:
                label = ""
            
            # Use transition with label
            if label:
                plantuml_lines.append(f"{from_state} --> {to_state} : {label}")
            else:
                plantuml_lines.append(f"{from_state} --> {to_state}")
                
        except Exception as e:
            print(f"Warning: Skipped link in PlantUML diagram: {e}")
            continue
    
    # Third pass: Handle node groups
    note_position_index = 0
    
    for node in node_tree.nodes:
        if hasattr(node, 'node_tree') and node.node_tree is not None:
            node_state = node_states.get(node.name)
            if node_state:
                # Add a note about the group content
                # Cycle through note positions to avoid overlapping
                position = NOTE_POSITIONS[note_position_index % len(NOTE_POSITIONS)]
                note_position_index += 1
                
                plantuml_lines.append("")
                plantuml_lines.append(f"note {position} of {node_state}")
                plantuml_lines.append(f"  Node group containing")
                plantuml_lines.append(f"  {len(node.node_tree.nodes)} nodes")
                plantuml_lines.append("end note")
    
    return "\n".join(plantuml_lines)


class NODE_OT_export_to_mermaid(bpy.types.Operator):
    """Export the current node tree to Mermaid or PlantUML diagram format"""
    bl_idname = "node.export_to_mermaid"
    bl_label = "Export to Diagram"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties for export options
    diagram_format: bpy.props.EnumProperty(
        name="Format",
        description="Choose the diagram format",
        items=[
            ('MERMAID', "Mermaid", "Export as Mermaid class diagram"),
            ('PLANTUML', "PlantUML", "Export as PlantUML state diagram"),
        ],
        default='MERMAID'
    )
    
    export_to_file: bpy.props.BoolProperty(
        name="Save to File",
        description="Save the diagram code to a file",
        default=True
    )
    
    copy_to_clipboard: bpy.props.BoolProperty(
        name="Copy to Clipboard",
        description="Copy the diagram code to clipboard (requires pyperclip)",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        """Check if we're in a node editor with a valid node tree."""
        return (context.space_data is not None and 
                hasattr(context.space_data, 'node_tree') and
                context.space_data.node_tree is not None)
    
    def execute(self, context):
        """Execute the export operation."""
        # Get the current node tree
        node_tree = context.space_data.node_tree
        
        if node_tree is None:
            self.report({'ERROR'}, "No active node tree found")
            return {'CANCELLED'}
        
        # Check if this is a supported node tree type
        supported_types = (
            'ShaderNodeTree', 
            'CompositorNodeTree', 
            'TextureNodeTree', 
            'GeometryNodeTree'
        )
        
        tree_type = type(node_tree).__name__
        if tree_type not in supported_types:
            self.report({'WARNING'}, f"Node tree type '{tree_type}' may not be fully supported")
        
        # Build the diagram based on selected format
        try:
            if self.diagram_format == 'MERMAID':
                diagram_code = "classDiagram\n" + build_class_diagram(node_tree)
                file_extension = "mmd"
                format_name = "Mermaid"
            else:  # PLANTUML
                diagram_code = "@startuml\n" + build_plantuml_state_diagram(node_tree) + "\n@enduml"
                file_extension = "puml"
                format_name = "PlantUML"
            
            # Print to console
            print("\n" + "="*50)
            print(f"{format_name} Diagram Code:")
            print("="*50)
            print(diagram_code)
            print("="*50 + "\n")
            
            # Save to file if requested
            if self.export_to_file:
                # Determine output path
                if bpy.data.filepath:
                    # Save next to the .blend file
                    blend_dir = os.path.dirname(bpy.data.filepath)
                    output_path = os.path.join(blend_dir, f"node_tree.{file_extension}")
                else:
                    # Save to temp directory if blend file is not saved
                    output_path = os.path.join(tempfile.gettempdir(), f"node_tree.{file_extension}")
                
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(diagram_code)
                    self.report({'INFO'}, f"{format_name} code saved to: {output_path}")
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to save file: {e}")
                    return {'CANCELLED'}
            
            # Copy to clipboard if requested (optional feature)
            if self.copy_to_clipboard:
                if HAS_PYPERCLIP:
                    try:
                        pyperclip.copy(diagram_code)
                        self.report({'INFO'}, f"{format_name} code copied to clipboard")
                    except Exception as e:
                        self.report({'WARNING'}, f"Could not copy to clipboard: {e}")
                else:
                    self.report({'WARNING'}, "pyperclip not available. Install it to use clipboard feature.")
            
            self.report({'INFO'}, f"Node tree exported to {format_name} format successfully")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate diagram code: {e}")
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show a dialog before executing."""
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        """Draw the operator properties in the dialog."""
        layout = self.layout
        layout.prop(self, "diagram_format")
        layout.prop(self, "export_to_file")
        layout.prop(self, "copy_to_clipboard")


class NODE_PT_mermaid_panel(bpy.types.Panel):
    """Panel in the Node Editor sidebar for diagram export."""
    bl_label = "Diagram Export"
    bl_idname = "NODE_PT_mermaid_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Diagram'
    
    @classmethod
    def poll(cls, context):
        """Only show panel when we have a node tree."""
        return (context.space_data is not None and 
                hasattr(context.space_data, 'node_tree') and
                context.space_data.node_tree is not None)
    
    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        
        node_tree = context.space_data.node_tree
        if node_tree:
            # Show current node tree info
            box = layout.box()
            box.label(text=f"Current Tree: {node_tree.name}", icon='NODETREE')
            box.label(text=f"Type: {type(node_tree).__name__}")
            box.label(text=f"Nodes: {len(node_tree.nodes)}")
            box.label(text=f"Links: {len(node_tree.links)}")
        
        # Export button
        layout.separator()
        layout.operator("node.export_to_mermaid", icon='EXPORT')
        
        # Info text
        layout.separator()
        box = layout.box()
        box.label(text="Supported Formats:", icon='INFO')
        box.label(text="• Mermaid Class Diagram")
        box.label(text="• PlantUML State Diagram")
        
        layout.separator()
        box = layout.box()
        box.label(text="Supported Node Trees:", icon='INFO')
        box.label(text="• Shader Nodes")
        box.label(text="• Compositor Nodes")
        box.label(text="• Geometry Nodes")
        box.label(text="• Texture Nodes")


# Registration
classes = (
    NODE_OT_export_to_mermaid,
    NODE_PT_mermaid_panel,
)


def register():
    """Register the add-on."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister the add-on."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
