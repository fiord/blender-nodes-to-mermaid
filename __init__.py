"""
Blender Add-on: Node Tree to Diagram Converter

This add-on converts Blender's node trees to Mermaid or PlantUML diagram formats for easy sharing and documentation.
It supports all main node tree types: Shader, Compositor, Texture, and Geometry.
"""

import bpy
import os
import tempfile
import traceback

# Import diagram generators
from . import mermaid_generator
from . import plantuml_generator

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
                diagram_code = "classDiagram\n" + mermaid_generator.build_class_diagram(node_tree)
                file_extension = "mmd"
                format_name = "Mermaid"
            else:  # PLANTUML
                diagram_code = "@startuml\n" + plantuml_generator.build_plantuml_state_diagram(node_tree) + "\n@enduml"
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
