"""
PlantUML state diagram generator for Blender node trees.

This module handles the conversion of Blender node trees to PlantUML state diagram format.
"""

from .diagram_utils import (
    sanitize_identifier,
    get_node_parameters,
    get_node_type_name,
    format_parameter_value,
    MAX_DISPLAYED_PARAMETERS
)

# Note positions for PlantUML node group annotations
NOTE_POSITIONS = ['right', 'left', 'top', 'bottom']


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
        node_type = get_node_type_name(node)
        
        # Create state definition with description
        state_description_lines = []
        state_description_lines.append(f"+String type: {node_type}")
        
        # Add parameters
        params = get_node_parameters(node)
        if params:
            # Limit parameters
            important_params = list(params.items())[:MAX_DISPLAYED_PARAMETERS]
            
            for key, value in important_params:
                # Determine type and format value (matching Mermaid format)
                param_type, value_str = format_parameter_value(value)
                
                # Add parameter line with type annotation (matching Mermaid output)
                state_description_lines.append(f"+{param_type} {key}: {value_str}")
        
        # Add input/output socket counts
        if hasattr(node, 'inputs') and len(node.inputs) > 0:
            state_description_lines.append(f"+inputs: {len(node.inputs)}")
        if hasattr(node, 'outputs') and len(node.outputs) > 0:
            state_description_lines.append(f"+outputs: {len(node.outputs)}")
        
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
