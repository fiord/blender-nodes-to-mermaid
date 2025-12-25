"""
Common utilities for node tree diagram generation.

This module contains shared functions for extracting and formatting node information
that are used by both Mermaid and PlantUML diagram generators.
"""

# Configuration constants
MAX_DISPLAYED_PARAMETERS = 5  # Maximum number of parameters to display in node labels


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


def get_node_type_name(node):
    """
    Extract a clean node type name from a Blender node.
    
    Args:
        node: The Blender node
        
    Returns:
        String containing the cleaned node type name
    """
    node_type = node.bl_idname
    for prefix_to_remove in ['ShaderNode', 'CompositorNode', 'GeometryNode', 'TextureNode', 'Node']:
        if node_type.startswith(prefix_to_remove):
            node_type = node_type[len(prefix_to_remove):]
            break
    return node_type


def format_parameter_value(value):
    """
    Format a parameter value for display in diagrams.
    
    Args:
        value: The parameter value to format
        
    Returns:
        Tuple of (type_name, formatted_value_string)
    """
    if isinstance(value, bool):
        return ("Boolean", str(value))
    elif isinstance(value, int):
        return ("Integer", str(value))
    elif isinstance(value, float):
        return ("Float", f"{value:.3f}")
    elif isinstance(value, str):
        return ("String", f'"{value}"')
    elif isinstance(value, (tuple, list)):
        formatted_values = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in value]
        return ("Vector", f"({', '.join(formatted_values)})")
    else:
        return ("Object", str(value))
