# PyAutoload

A Python autoloading library inspired by Ruby's [Zeitwerk](https://github.com/fxn/zeitwerk), designed to simplify module importing through convention over configuration.

## Introduction

PyAutoload aims to eliminate the cognitive overhead of managing imports in Python projects. By following simple naming conventions and directory structures, PyAutoload automatically discovers and loads your modules, allowing you to focus on writing code instead of managing imports.

## Features

- **Automatic module discovery**: Scans your project directories and maps file paths to module names
- **Convention-based naming**: Uses a simple inflector to convert snake_case filenames to CamelCase class names
- **Eager loading**: Loads all modules upfront for production environments
- **Lazy loading**: Only loads modules when they're first accessed, perfect for development
- **File watching**: Automatically reloads modules when files change during development
- **Seamless integration**: Works with Python's import system using `importlib`

## Installation

```bash
pip install pyautoload
```

## Quick Start

```python
from pyautoload import AutoLoader

# Initialize the loader
loader = AutoLoader(base_path="myapp", top_level="myapp")

# Discover modules (lazy loading mode)
loader.discover()

# Now you can import modules without worrying about file locations
import myapp.models.user
import myapp.controllers.users_controller

# Or use eager loading to load everything at once
# loader.eager_load()

# For development, enable file watching to reload modules when files change
# loader.enable_reloading()
```

## Directory Structure Conventions

PyAutoload expects a conventional directory structure where file paths match module names:

```
myapp/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── user.py            # Contains the User class
├── controllers/
│   ├── __init__.py
│   └── users_controller.py # Contains the UsersController class
└── services/
    ├── __init__.py
    ├── user_service.py     # Contains the UserService class
    └── auth/
        ├── __init__.py
        └── authentication_service.py # Contains the AuthenticationService class
```

## Customizing Inflection

The default inflector converts snake_case to CamelCase, but you can customize it for special cases:

```python
from pyautoload import AutoLoader, Inflector

# Create a custom inflector
inflector = Inflector()
inflector.inflect({
    "html_parser": "HTMLParser",
    "csv_controller": "CSVController"
})

# Use the custom inflector with the loader
loader = AutoLoader(base_path="myapp", top_level="myapp", inflector=inflector)
```

## Development Status

PyAutoload is currently in alpha development. We're following a test-driven development approach to ensure reliability and correctness.

### Alpha Release v0.1.0-alpha.1

This alpha release includes:

- Basic autoloading functionality
- Module registry for tracking loaded modules
- Dependency tracking between modules
- Automatic reloading of modules and their dependencies
- File watching during development

We encourage Python developers to try PyAutoload and provide feedback through:
- GitHub issues for bugs and feature requests
- GitHub discussions for general feedback and questions

### Feedback Wanted

We're especially interested in feedback on:

1. Usability of the API
2. Integration with different project structures
3. Performance on larger codebases
4. Compatibility with different Python versions
5. Interactions with other libraries and frameworks

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See our [contribution guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by [Zeitwerk](https://github.com/fxn/zeitwerk) for Ruby
- Built with love for the Python community
