* Tasks

1. **Set up project structure**:
   - Create directories, initialize Git, set up virtual environment.
2. **Implement basic autoloading**:
   - Write a function to scan directories for `.py` files.
   - Convert file paths to module names.
   - Use `importlib` to load modules.
3. **Add support for packages**:
   - Handle `__init__.py` files for package initialization.
   - Ensure correct loading order for packages.
4. **Implement eager loading**:
   - Load all modules immediately when `discover()` is called.
5. **Implement lazy loading**:
   - Use import hooks or proxies to load modules on first access.
6. **Add file watching**:
   - Integrate `watchdog` to monitor file changes.
   - Reload modules when changes are detected.
7. **Write tests**:
   - Unit tests for individual components.
   - Integration tests for the autoloading process.
8. **Document the code**:
   - Write docstrings for functions and classes.
   - Create usage examples in documentation.
9. **Package for distribution**:
   - Create `setup.py` or `pyproject.toml`.
   - Publish to PyPI.
