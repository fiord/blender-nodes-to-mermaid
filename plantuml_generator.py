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
    Supports Blender frame nodes to group related nodes visually.
    
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
    
    # Identify frame nodes and their children
    frame_nodes = {}  # frame_node -> list of child nodes
    frame_states = {}  # frame_node.name -> state_id
    
    for node in node_tree.nodes:
        # Check if this is a frame node (NodeFrame type)
        if hasattr(node, 'bl_idname') and 'Frame' in node.bl_idname:
            frame_nodes[node.name] = []
            
    # Group nodes by their parent frame
    nodes_by_frame = {None: []}  # None key for nodes without parent
    for frame_name in frame_nodes.keys():
        nodes_by_frame[frame_name] = []
    
    for node in node_tree.nodes:
        # Skip frame nodes themselves in the main node list
        if node.name in frame_nodes:
            continue
            
        # Check if node has a parent frame
        parent_frame = None
        if hasattr(node, 'parent') and node.parent is not None:
            parent_frame = node.parent.name
            
        if parent_frame in nodes_by_frame:
            nodes_by_frame[parent_frame].append(node)
        else:
            nodes_by_frame[None].append(node)
    
    # Helper function to create state definition
    def create_state_definition(node):
        """Create state definition for a node"""
        lines = []
        
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
        state_description_lines.append(f"type: {node_type}")
        
        # Add parameters
        params = get_node_parameters(node)
        if params:
            # Limit parameters
            important_params = list(params.items())[:MAX_DISPLAYED_PARAMETERS]
            
            for key, value in important_params:
                # Determine type and format value (matching Mermaid format)
                param_type, value_str = format_parameter_value(value)
                
                # Add parameter line (without type annotation for PlantUML)
                state_description_lines.append(f"{key}: {value_str}")
        
        # Add input/output socket counts
        if hasattr(node, 'inputs') and len(node.inputs) > 0:
            state_description_lines.append(f"inputs: {len(node.inputs)}")
        if hasattr(node, 'outputs') and len(node.outputs) > 0:
            state_description_lines.append(f"outputs: {len(node.outputs)}")
        
        # Create state with description using PlantUML state syntax
        state_label = node.name.replace('_', ' ')
        lines.append(f"state \"{state_label}\" as {state_name} {{")
        for desc_line in state_description_lines:
            lines.append(f"  {state_name} : {desc_line}")
        lines.append("}")
        
        return lines
    
    # First pass: Create frame states and their child nodes
    for frame_name, child_nodes in nodes_by_frame.items():
        if frame_name is None:
            # Nodes without parent - create normally
            for node in child_nodes:
                plantuml_lines.extend(create_state_definition(node))
                plantuml_lines.append("")
        else:
            # Create frame state
            frame_state_name = sanitize_identifier(frame_name)
            frame_states[frame_name] = frame_state_name
            frame_label = frame_name.replace('_', ' ')
            
            plantuml_lines.append(f"state \"{frame_label}\" as {frame_state_name} {{")
            plantuml_lines.append("")
            
            # Create child nodes inside the frame
            for node in child_nodes:
                child_lines = create_state_definition(node)
                # Indent child state definitions
                for line in child_lines:
                    plantuml_lines.append(f"  {line}")
                plantuml_lines.append("")
            
            plantuml_lines.append("}")
            plantuml_lines.append("")
    
    # Second pass: Create transitions (connections between nodes)
    # Note: Transitions are drawn from nodes, not from frames
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
