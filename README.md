# Node to Mermaid Converter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Blender](https://img.shields.io/badge/Blender-5.0%2B-orange.svg)](https://www.blender.org/)

A Blender add-on that exports node trees to [Mermaid](https://mermaid.js.org/) diagram format for easy sharing, documentation, and visualization.

## Features

- 🎨 **Export any node tree** to Mermaid class diagram format
- 📊 **Include node parameters** - Export with complete parameter information for full documentation
- 🔄 **Supports all major node types**:
  - Shader Nodes
  - Compositor Nodes
  - Geometry Nodes
  - Texture Nodes
- 📦 **Handles nested node groups** with comments
- 💾 **Multiple export options**:
  - Save to `.mmd` file
  - Print to console
  - Copy to clipboard (optional)
  - Toggle parameter inclusion
- 🚀 **Zero external dependencies** - pure `bpy` implementation
- 🎯 **Simple UI** integration in Node Editor sidebar

## Installation

### Method 1: Install from ZIP

1. Download this repository as a ZIP file
2. Open Blender (5.0 or later)
3. Go to `Edit` → `Preferences` → `Add-ons`
4. Click `Install...` button
5. Select the downloaded ZIP file
6. Enable the add-on by checking the box next to "Node: Node to Mermaid Converter"

### Method 2: Manual Installation

1. Clone or download this repository
2. Copy the entire folder to your Blender addons directory:
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\5.x\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/5.x/scripts/addons/`
   - **Linux**: `~/.config/blender/5.x/scripts/addons/`
3. Restart Blender
4. Enable the add-on in Preferences → Add-ons

## Usage

### Basic Export

1. Open any Node Editor (Shader Editor, Compositor, Geometry Nodes, etc.)
2. Create or open a node tree
3. Open the sidebar in the Node Editor (`N` key)
4. Navigate to the **Mermaid** tab
5. Click the **Export to Mermaid** button
6. Configure export options in the dialog:
   - ✅ **Include Node Parameters**: Include node parameters and values for complete documentation (recommended for sharing)
   - ✅ **Save to File**: Saves `.mmd` file next to your `.blend` file
   - ☐ **Copy to Clipboard**: Copies code to clipboard (requires `pyperclip`)
7. Click **OK** to export

### Export Options Explained

- **Include Node Parameters**: When enabled, exports all important node parameters (values, settings, colors, etc.) needed to recreate the node setup. This is essential for sharing complete node graphs with others.
- **Save to File**: Exports the diagram to a `.mmd` file in the same directory as your `.blend` file
- **Copy to Clipboard**: Copies the Mermaid code to your system clipboard for quick pasting

### Output Example

The add-on exports nodes as a Mermaid class diagram, showing each node with its properties in a structured way:

```mermaid
classDiagram
class Principled_BSDF{
    +String type: Principled
    +Float metallic: 0.000
    +Float roughness: 0.500
    +inputs: 25
    +outputs: 1
}
class Material_Output{
    +String type: Output
    +inputs: 3
    +outputs: 0
}
Principled_BSDF --> Material_Output : BSDF → Surface
```

#### Flowchart Format
}
Principled_BSDF --> Material_Output : BSDF → Surface
```

### Viewing Mermaid Diagrams

You can view the generated Mermaid diagrams using:

- [Mermaid Live Editor](https://mermaid.live/) - Paste your code and see the diagram
- GitHub/GitLab - Markdown files with Mermaid code blocks are automatically rendered
- VS Code - With Mermaid extensions
- Documentation tools - Many support Mermaid (MkDocs, Docusaurus, etc.)

## Examples

### Simple Shader Network

```mermaid
classDiagram
class Principled_BSDF{
    +String type: Principled
}
class Material_Output{
    +String type: Output
}
Principled_BSDF --> Material_Output : BSDF → Surface
```

### With Texture Nodes

### With Texture Nodes

```mermaid
classDiagram
class Image_Texture{
    +String type: TexImage
}
class Principled_BSDF{
    +String type: Principled
}
class Material_Output{
    +String type: Output
}
Image_Texture --> Principled_BSDF : Color → Base Color
Principled_BSDF --> Material_Output : BSDF → Surface
```

### Nested Groups

The add-on automatically handles node groups with comment annotations:

```mermaid
classDiagram
class MyGroup{
    +String type: Group
}
class Material_Output{
    +String type: Output
}
MyGroup --> Material_Output
%% MyGroup is a node group containing 3 nodes
```

## Technical Details

### Supported Node Trees

- `ShaderNodeTree` - Material shading nodes
- `CompositorNodeTree` - Compositing nodes  
- `GeometryNodeTree` - Geometry manipulation nodes
- `TextureNodeTree` - Texture nodes

### How It Works

1. **Traverses** the active node tree in the Node Editor
2. **Extracts** node information (name, type, sockets)
3. **Maps** connections between nodes via links
4. **Generates** Mermaid syntax in `graph TD` (top-down) format
5. **Handles** nested node groups recursively as subgraphs
6. **Sanitizes** node names for valid Mermaid IDs

### File Output

- **Default location**: Same directory as your `.blend` file
- **Filename**: `node_tree.mmd`
- **Fallback**: System temp directory if `.blend` file is not saved
- **Format**: Plain text Mermaid diagram code

## Requirements

- **Blender**: 5.0 or later
- **Python**: Built-in with Blender (no external dependencies)
- **Optional**: `pyperclip` library for clipboard support (not required)

## Limitations

- Very complex node trees may produce large diagrams
- Node positioning from Blender is not preserved in Mermaid
- Some specialized node types may have generic labels

## Development

### Project Structure

```
blender-nodes-to-mermaid/
├── __init__.py          # Main add-on code
├── README.md            # This file
├── LICENSE              # MIT License
└── .gitignore          # Git ignore rules
```

### Code Overview

- `build_mermaid()`: Recursively converts node tree to Mermaid syntax
- `NODE_OT_export_to_mermaid`: Operator for export functionality
- `NODE_PT_mermaid_panel`: UI panel in Node Editor sidebar

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Future Improvements

- [ ] Add node positioning hints for better layouts
- [ ] Support custom node colors/styles
- [ ] Export multiple node trees at once
- [ ] Add preferences panel for default export settings
- [ ] Support for custom node tree types
- [ ] Automated tests for different node configurations
- [ ] Better handling of complex nested groups
- [ ] Export to other diagram formats

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the Blender community
- Uses [Mermaid](https://mermaid.js.org/) diagram syntax
- Inspired by the need to document complex node setups

## Support

If you encounter any issues or have questions:

1. Check existing [Issues](https://github.com/fiord/blender-nodes-to-mermaid/issues)
2. Create a new issue with:
   - Blender version
   - Node tree type
   - Steps to reproduce
   - Error messages (check Blender console)

---

**Made with ❤️ for the Blender community**
