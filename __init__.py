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
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Node Editor > Sidebar > Mermaid",
    "description": "Export node trees to Mermaid diagram format",
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


def build_mermaid(node_tree, prefix='', indent=0):
    """
    Recursively build Mermaid code from a node tree.
    
    Args:
        node_tree: The Blender node tree to convert
        prefix: Prefix for node IDs (used in subgraphs)
        indent: Current indentation level
        
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
        
        # Create node definition
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
            group_content = build_mermaid(node.node_tree, group_prefix, indent + 1)
            mermaid_lines.append(group_content)
            
            mermaid_lines.append(f"{indent_str}end")
    
    return "\n".join(mermaid_lines)


class NODE_OT_export_to_mermaid(bpy.types.Operator):
    """Export the current node tree to Mermaid diagram format"""
    bl_idname = "node.export_to_mermaid"
    bl_label = "Export to Mermaid"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties for export options
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
            mermaid_code = "graph TD;\n" + build_mermaid(node_tree)
            
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
