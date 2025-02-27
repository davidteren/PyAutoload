# Product Requirements Document (PRD)

## Introduction
PyAutoload is a Python library that provides autoloading functionality similar to Zeitwerk in Ruby. It aims to simplify module loading by automatically discovering and loading modules based on directory structure and naming conventions.

## Features
- **Automatic discovery**: Scans a specified directory for Python modules.
- **Convention-based naming**: Maps file paths to module names following standard conventions.
- **Eager and lazy loading**: Supports both immediate and on-demand module loading.
- **File watching**: Automatically reloads modules during development when files change.
- **Seamless integration**: Works with Python's import system using `importlib`.

## Usage
```python
from pyautoload import AutoLoader

loader = AutoLoader(base_path="myapp", top_level="myapp")
loader.discover()

# Now modules can be imported normally
import myapp.subdir.module
```

## Architecture
PyAutoload scans the specified base directory for `.py` files, converts their paths to module names, and uses Python's `importlib` to load them. It handles package initialization by loading `*__init__.py` files in the correct order.

## Requirements
- **Python Version**: 3.6 or higher (due to reliance on `pathlib`).
- **Dependencies**:
  - `watchdog` for file watching in development mode.

## Roadmap
- Implement basic autoloading functionality.
- Add support for lazy loading.
- Integrate file watching for development mode.
- Write comprehensive tests and documentation.
- Package and publish to PyPI.
