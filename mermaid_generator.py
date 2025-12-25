"""
Mermaid class diagram generator for Blender node trees.

This module handles the conversion of Blender node trees to Mermaid class diagram format.
"""

from .diagram_utils import (
    sanitize_identifier,
    get_node_parameters,
    get_node_type_name,
    format_parameter_value,
    MAX_DISPLAYED_PARAMETERS
)


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
        node_type = get_node_type_name(node)
        
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
                    param_type, value_str = format_parameter_value(value)
                    
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
