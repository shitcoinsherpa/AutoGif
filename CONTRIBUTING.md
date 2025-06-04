# Contributing to AutoGIF

First off, thank you for considering contributing to AutoGIF! It's people like you that make AutoGIF such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear and descriptive title**
- **Steps to reproduce** the issue
- **Expected behavior** vs what actually happened
- **Screenshots** if applicable
- **System information** (OS, Python version, etc.)
- **Error messages** or logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear and descriptive title**
- **Detailed description** of the proposed feature
- **Use case** - why this enhancement would be useful
- **Possible implementation** approach (if you have ideas)

### Creating New Effects

AutoGIF's effect system is designed to be extensible. To create a new effect:

1. Create a new file in `autogif/effects/plugins/effect_yourname.py`
2. Inherit from `EffectBase`:

```python
from autogif.effects.effect_base import EffectBase
from PIL import Image, ImageDraw, ImageFont

class YourEffect(EffectBase):
    @property
    def slug(self) -> str:
        return "your-effect"
    
    @property
    def display_name(self) -> str:
        return "Your Effect"
    
    @property
    def default_intensity(self) -> int:
        return 50
    
    def prepare(self, **kwargs) -> None:
        """Initialize any effect-specific variables"""
        pass
    
    def transform(self, frame_image: Image.Image, text: str, 
                  base_position: tuple[int, int], current_frame_index: int,
                  intensity: int, font: ImageFont.FreeTypeFont, 
                  font_color: str, outline_color: str, outline_width: int,
                  text_anchor_x: int, text_anchor_y: int,
                  frame_width: int, frame_height: int, **kwargs) -> Image.Image:
        """Apply your effect to the frame"""
        # Your effect logic here
        return modified_frame
```

3. If your effect draws text (rather than modifying existing text), add it to `text_drawing_effects` in `processing.py`

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Follow the coding style**:
   - Use Black for code formatting (`make format`)
   - Follow PEP 8 guidelines
   - Add docstrings to functions and classes
   - Keep line length under 120 characters
3. **Write tests** if applicable
4. **Update documentation** if you're changing functionality
5. **Ensure all tests pass** (`make test`)
6. **Write a good commit message**:
   - Use the present tense ("Add feature" not "Added feature")
   - Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
   - Limit the first line to 72 characters or less

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Setting Up Your Development Environment

1. Fork and clone the repository:
```bash
git clone https://github.com/shitcoinsherpa/AutoGif.git
cd autogif
```

2. Create a virtual environment:
```bash
# Windows
build.bat

# macOS/Linux
./build.sh
```

3. Install development dependencies:
```bash
make dev-install
```

### Running Tests

```bash
make test
```

### Code Style

We use Black for code formatting and Flake8 for linting:

```bash
# Format code
make format

# Check code style
make lint
```

## Project Structure

```
autogif/
├── autogif/              # Main application code
│   ├── effects/          # Visual effects system
│   │   ├── effect_base.py    # Base class for all effects
│   │   └── plugins/          # Individual effect implementations
│   ├── fonts/            # Bundled fonts
│   ├── config.py         # Configuration settings
│   ├── main.py           # Gradio UI entry point
│   ├── processing.py     # Core video/GIF processing logic
│   └── user_settings.py  # User preferences management
├── resources/            # Platform binaries
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Testing Guidelines

- Write unit tests for new functionality
- Ensure existing tests still pass
- Test on multiple platforms if possible
- Test with various input formats and edge cases

## Documentation

- Update the README.md if you change user-facing functionality
- Add docstrings to all public functions and classes
- Include type hints where possible
- Update effect documentation if adding new effects

## Questions?

Feel free to open an issue with the "question" label or start a discussion in the GitHub Discussions tab.

Thank you for contributing! 🎉 