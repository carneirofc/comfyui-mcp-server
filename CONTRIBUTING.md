# Contributing

Thank you for your interest in contributing to ComfyUI MCP Server!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd comfyui-mcp-server
   ```

2. **Install dependencies** (this project uses [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```
   This creates a virtual environment and installs runtime + dev dependencies
   from `pyproject.toml` / `uv.lock`. Prefix commands with `uv run` to run them
   inside that environment.

3. **Start ComfyUI** (if not already running):
   ```bash
   cd <ComfyUI_dir>
   python main.py --port 8188
   ```

4. **Run the server:**
   ```bash
   uv run python server.py
   ```

5. **Test your changes:**
   ```bash
   uv run python test_client.py
   ```

6. **Run the test suite:**
   ```bash
   uv run pytest tests/ -v
   ```

## Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions focused and small

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request with a clear description

## Questions?

- Open an issue for bugs or feature requests
- Check [docs/REFERENCE.md](docs/REFERENCE.md) for API details
- See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions
