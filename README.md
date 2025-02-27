# PyAutoload

A Python autoloading library inspired by Zeitwerk.

## Introduction

PyAutoload simplifies module loading in Python by providing an autoloading mechanism that automatically discovers and loads modules based on directory structure and naming conventions.

## Features

- Automatic module discovery
- Convention-based naming
- Eager and lazy loading modes
- File watching for development

## Usage

```python
from pyautoload import AutoLoader

loader = AutoLoader(base_path="myapp", top_level="myapp")
loader.discover()

# Modules can now be imported normally
import myapp.subdir.module
```

For more details, see the [documentation](docs/).
