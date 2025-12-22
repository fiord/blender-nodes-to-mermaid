"""
Blender Add-on: Node Tree to Mermaid Converter

This add-on converts Blender's node trees to Mermaid diagram format for easy sharing and documentation.
It supports all main node tree types: Shader, Compositor, Texture, and Geometry.
"""

import bpy
import os
import tempfile
import traceback

bl_info = {
    "name": "Node to Mermaid Converter",
    "author": "blender-nodes-to-mermaid contributors",
    "version": (1, 2, 0),
    "blender": (5, 0, 0),
    "location": "Node Editor > Sidebar > Mermaid",
    "description": "Export node trees to Mermaid diagram format with parameters",
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

def sanitize_id(name, prefix=''):
    """Sanitize node name to create a valid Mermaid ID."""
    # Replace spaces and special characters
    sanitized = name.replace(' ', '_').replace('.', '_').replace('-', '_')
    # Remove any other non-alphanumeric characters except underscore
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
    # Ensure we have a valid ID (not empty)
    if not sanitized:
        sanitized = 'node'
    return prefix + sanitized


def sanitize_class_name(name):
    """Sanitize node name for use as a class name in class diagrams."""
    # For class diagrams, class names must be valid identifiers (no spaces)
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


def format_node_label(node, node_type):
    """
    Format a node label with its type and important parameters.
    
    Args:
        node: The Blender node
        node_type: The simplified node type name
        
    Returns:
        Formatted label string
    """
    # Start with basic node info
    label_parts = [f"{node.name} ({node_type})"]
    
    # Get node parameters
    params = get_node_parameters(node)
    
    # Format parameters for display (limit to most important ones)
    if params:
        param_lines = []
        # Limit to MAX_DISPLAYED_PARAMETERS to avoid overly long labels
        important_params = list(params.items())[:MAX_DISPLAYED_PARAMETERS]
        
        for key, value in important_params:
            # Format the value based on type
            if isinstance(value, float):
                # Round floats to 3 decimal places
                value_str = f"{value:.3f}"
            elif isinstance(value, (tuple, list)):
                # Format tuples/lists nicely
                formatted_values = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in value]
                value_str = f"({', '.join(formatted_values)})"
            else:
                value_str = str(value)
            
            param_lines.append(f"{key}: {value_str}")
        
        if param_lines:
            # Add parameters to label
            label_parts.append("---")
            label_parts.extend(param_lines)
    
    # Join all parts with newline (Mermaid supports multiline labels)
    return "\\n".join(label_parts)


def build_mermaid(node_tree, prefix='', indent=0, include_parameters=True):
    """
    Recursively build Mermaid code from a node tree.
    
    Args:
        node_tree: The Blender node tree to convert
        prefix: Prefix for node IDs (used in subgraphs)
        indent: Current indentation level
        include_parameters: Whether to include node parameters in labels
        
    Returns:
        String containing Mermaid diagram code
    """
    if node_tree is None:
        return ""
    
    mermaid_lines = []
    indent_str = "    " * indent
    
    # Create a mapping of nodes to their IDs
    node_ids = {}
    id_counters = {}  # Track ID usage to handle collisions
    
    # First pass: Create all node definitions
    for node in node_tree.nodes:
        base_id = sanitize_id(node.name, prefix)
        
        # Handle ID collisions by adding a counter suffix
        if base_id in id_counters:
            id_counters[base_id] += 1
            node_id = f"{base_id}_{id_counters[base_id]}"
        else:
            id_counters[base_id] = 0
            node_id = base_id
        
        node_ids[node.name] = node_id
        
        # Get node type name (remove 'ShaderNode', 'CompositorNode' etc prefixes for cleaner display)
        node_type = node.bl_idname
        for prefix_to_remove in ['ShaderNode', 'CompositorNode', 'GeometryNode', 'TextureNode', 'Node']:
            if node_type.startswith(prefix_to_remove):
                node_type = node_type[len(prefix_to_remove):]
                break
        
        # Create node definition with parameters if requested
        if include_parameters:
            node_label = format_node_label(node, node_type)
        else:
            node_label = f"{node.name} ({node_type})"
        
        mermaid_lines.append(f"{indent_str}{node_id}[\"{node_label}\"]")
    
    # Second pass: Create links between nodes
    for link in node_tree.links:
        try:
            # Skip invalid links
            if not link.is_valid:
                continue
                
            from_node = link.from_node
            to_node = link.to_node
            
            # Skip if nodes don't exist in our mapping
            if from_node.name not in node_ids or to_node.name not in node_ids:
                continue
            
            from_id = node_ids[from_node.name]
            to_id = node_ids[to_node.name]
            
            # Get socket names for the link label
            from_socket = link.from_socket.name
            to_socket = link.to_socket.name
            
            # Create link with socket names as label
            if from_socket and to_socket:
                link_label = f"{from_socket} -> {to_socket}"
            elif from_socket:
                link_label = from_socket
            elif to_socket:
                link_label = to_socket
            else:
                link_label = ""
            
            if link_label:
                mermaid_lines.append(f"{indent_str}{from_id} -->|{link_label}| {to_id}")
            else:
                mermaid_lines.append(f"{indent_str}{from_id} --> {to_id}")
                
        except Exception as e:
            # Skip problematic links
            print(f"Warning: Skipped link due to error: {e}")
            continue
    
    # Third pass: Handle group nodes recursively
    for node in node_tree.nodes:
        # Check if this is a group node with a node tree
        if hasattr(node, 'node_tree') and node.node_tree is not None:
            node_id = node_ids[node.name]
            group_name = node.name
            
            # Create subgraph for the group
            mermaid_lines.append(f"{indent_str}subgraph {node_id}[\"Group: {group_name}\"]")
            
            # Recursively process the group's node tree
            group_prefix = node_id + "_"
            group_content = build_mermaid(node.node_tree, group_prefix, indent + 1, include_parameters)
            mermaid_lines.append(group_content)
            
            mermaid_lines.append(f"{indent_str}end")
    
    return "\n".join(mermaid_lines)


def build_class_diagram(node_tree, include_parameters=True):
    """
    Build Mermaid class diagram from a node tree.
    This format better represents nodes with their properties.
    
    Args:
        node_tree: The Blender node tree to convert
        include_parameters: Whether to include node parameters in class definitions
        
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
        base_class_name = sanitize_class_name(node.name)
        
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
        
        # Add parameters if requested
        if include_parameters:
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


class NODE_OT_export_to_mermaid(bpy.types.Operator):
    """Export the current node tree to Mermaid diagram format"""
    bl_idname = "node.export_to_mermaid"
    bl_label = "Export to Mermaid"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties for export options
    diagram_format: bpy.props.EnumProperty(
        name="Diagram Format",
        description="Choose the Mermaid diagram format",
        items=[
            ('FLOWCHART', "Flowchart", "Traditional flowchart (graph TD) - shows node flow"),
            ('CLASS', "Class Diagram", "Class diagram - better for showing properties and structure"),
        ],
        default='CLASS'
    )
    
    export_to_file: bpy.props.BoolProperty(
        name="Save to File",
        description="Save the Mermaid code to a file",
        default=True
    )
    
    copy_to_clipboard: bpy.props.BoolProperty(
        name="Copy to Clipboard",
        description="Copy the Mermaid code to clipboard (requires pyperclip)",
        default=False
    )
    
    include_parameters: bpy.props.BoolProperty(
        name="Include Node Parameters",
        description="Include node parameters and values in the diagram for complete documentation",
        default=True
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
        
        # Build the Mermaid diagram
        try:
            if self.diagram_format == 'CLASS':
                mermaid_code = "classDiagram\n" + build_class_diagram(node_tree, include_parameters=self.include_parameters)
            else:  # FLOWCHART
                mermaid_code = "graph TD;\n" + build_mermaid(node_tree, include_parameters=self.include_parameters)
            
            # Print to console
            print("\n" + "="*50)
            print("Mermaid Diagram Code:")
            print("="*50)
            print(mermaid_code)
            print("="*50 + "\n")
            
            # Save to file if requested
            if self.export_to_file:
                # Determine output path
                if bpy.data.filepath:
                    # Save next to the .blend file
                    blend_dir = os.path.dirname(bpy.data.filepath)
                    output_path = os.path.join(blend_dir, "node_tree.mmd")
                else:
                    # Save to temp directory if blend file is not saved
                    output_path = os.path.join(tempfile.gettempdir(), "node_tree.mmd")
                
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(mermaid_code)
                    self.report({'INFO'}, f"Mermaid code saved to: {output_path}")
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to save file: {e}")
                    return {'CANCELLED'}
            
            # Copy to clipboard if requested (optional feature)
            if self.copy_to_clipboard:
                if HAS_PYPERCLIP:
                    try:
                        pyperclip.copy(mermaid_code)
                        self.report({'INFO'}, "Mermaid code copied to clipboard")
                    except Exception as e:
                        self.report({'WARNING'}, f"Could not copy to clipboard: {e}")
                else:
                    self.report({'WARNING'}, "pyperclip not available. Install it to use clipboard feature.")
            
            self.report({'INFO'}, "Node tree exported to Mermaid format successfully")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate Mermaid code: {e}")
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show a dialog before executing."""
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        """Draw the operator properties in the dialog."""
        layout = self.layout
        layout.prop(self, "diagram_format")
        layout.prop(self, "include_parameters")
        layout.separator()
        layout.prop(self, "export_to_file")
        layout.prop(self, "copy_to_clipboard")


class NODE_PT_mermaid_panel(bpy.types.Panel):
    """Panel in the Node Editor sidebar for Mermaid export."""
    bl_label = "Mermaid Export"
    bl_idname = "NODE_PT_mermaid_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Mermaid'
    
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
