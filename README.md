# Automatic Building Generator

An AI-powered system that generates 3D architectural models in SketchUp from 2D images. It uses large language models (like Gemini) with vision capabilities to parse the geometry, dimensions, windows, doors, and roof structures of a building in an image, and then automatically constructs a fully-textured parametric 3D model in SketchUp via the Model Context Protocol (MCP).

## Features
- **AI Vision Parsing**: Extracts detailed building parameters (blocks, roofs, dormers, windows, doors, porches, canopies).
- **SketchUp Integration**: Automatically draws the geometry in SketchUp using custom Ruby tools (`building_tools.rb`).
- **Texture Generation**: Extracts and generates AI textures based on the image style.
- **Parametric Generation**: Uses robust algorithms to construct roofs (gable, hip, shed, flat), walls, columns, doors, and windows with correct proportions.

## Setup

1. **Environment Variables**: Copy `.env.example` to `.env` and fill in your API keys (e.g., `GEMINI_API_KEY`, `MODELSCOPE_API_KEY`).
2. **Dependencies**: Run `pip install -r requirements.txt`.
3. **SketchUp MCP Client**: Ensure SketchUp is running with the Ruby MCP Server active.

## Usage

Run the main broker script to start the analysis and generation process:
```bash
python main.py
```
