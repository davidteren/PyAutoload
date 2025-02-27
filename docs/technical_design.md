# PyAutoload Technical Design

This document provides detailed technical specifications for the PyAutoload system, focusing on how it will integrate with Python's import machinery.

## Import System Architecture

### Python's Import Mechanism

Python's import system consists of several key components:

1. **Module Cache** (`sys.modules`): Dictionary mapping module names to module objects
2. **Import Hooks**:
   - `sys.meta_path`: List of finder objects consulted when importing modules
   - `sys.path_hooks`: List of callables that convert path entries to path entry finders
3. **Module Specs**: Objects that define how to load a module (from [PEP 451](https://www.python.org/dev/peps/pep-0451/))
4. **Finders and Loaders**: Find and load modules, respectively

PyAutoload will primarily interact with the `sys.meta_path` to insert a custom finder.

### PyAutoload Import Hook Design

```
┌───────────────────┐
│ Python Import     │
│ Statement         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     ┌───────────────────┐
│ PyAutoloadFinder  │◄────┤ Module Registry   │
│ (sys.meta_path)   │     │                   │
└─────────┬─────────┘     └───────────────────┘
          │
          ▼
┌───────────────────┐     ┌───────────────────┐
│ PyAutoloadLoader  │◄────┤ File System       │
│                   │     │ Scanner           │
└─────────┬─────────┘     └───────────────────┘
          │
          ▼
┌───────────────────┐
│ Module Object     │
│ Creation          │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Module Cache      │
│ (sys.modules)     │
└───────────────────┘
```

## Module Registry

The module registry is a central component that maps:

1. **Module names to file paths**:
   ```python
   {
       "myapp.models.user": "/path/to/myapp/models/user.py",
       "myapp.controllers.users_controller": "/path/to/myapp/controllers/users_controller.py"
   }
   ```

2. **Module dependencies**:
   ```python
   {
       "myapp.controllers.users_controller": ["myapp.models.user"]
   }
   ```

3. **Loaded module status**:
   ```python
   {
       "myapp.models.user": {
           "loaded": True,
           "mtime": 1614556800.0
       }
   }
   ```

### Registry Operations

1. **Registration**: Add entries during discovery
2. **Lookup**: Find file paths for module names
3. **Update**: Track module load status and dependencies
4. **Invalidation**: Mark modules for reloading when files change

## Import Hook Implementation

### PyAutoloadFinder

This class implements `importlib.abc.MetaPathFinder` and is responsible for:

1. Finding module specs based on naming conventions
2. Maintaining the module registry
3. Handling package and module differentiation

```python
class PyAutoloadFinder(MetaPathFinder):
    def __init__(self, base_paths, namespace=None, inflector=None):
        self.base_paths = base_paths
        self.namespace = namespace
        self.inflector = inflector or Inflector()
        self.registry = ModuleRegistry()
        self.scanner = FileScanner(self.base_paths, self.registry, self.inflector)
        
        # Perform initial scan
        self.scanner.scan()
        
        # Register in sys.meta_path
        sys.meta_path.insert(0, self)
        
    def find_spec(self, fullname, path=None, target=None):
        # Check if this module is in our registry
        if not self.registry.contains(fullname):
            return None
            
        # Get the file path for this module
        filepath = self.registry.get_path(fullname)
        
        # Create a spec with our custom loader
        if filepath.endswith('__init__.py'):
            # This is a package
            submodule_search_locations = [os.path.dirname(filepath)]
            spec = importlib.machinery.ModuleSpec(
                name=fullname,
                loader=PyAutoloadLoader(fullname, filepath, self.registry),
                origin=filepath,
                is_package=True,
                submodule_search_locations=submodule_search_locations
            )
        else:
            # This is a module
            spec = importlib.machinery.ModuleSpec(
                name=fullname,
                loader=PyAutoloadLoader(fullname, filepath, self.registry),
                origin=filepath,
                is_package=False
            )
            
        return spec
```

### PyAutoloadLoader

This class implements `importlib.abc.Loader` and is responsible for:

1. Creating module objects
2. Executing module code
3. Updating the registry when modules are loaded

```python
class PyAutoloadLoader(Loader):
    def __init__(self, fullname, filepath, registry):
        self.fullname = fullname
        self.filepath = filepath
        self.registry = registry
        
    def create_module(self, spec):
        # Use default module creation (return None)
        return None
        
    def exec_module(self, module):
        # Load source code from file
        with open(self.filepath, 'rb') as f:
            source = f.read()
            
        # Compile and execute the module
        code = compile(source, self.filepath, 'exec')
        exec(code, module.__dict__)
        
        # Update the registry
        self.registry.mark_loaded(self.fullname, os.path.getmtime(self.filepath))
```

## File System Scanner

The file system scanner traverses directories to:

1. Find Python modules and packages
2. Register them in the module registry
3. Apply naming conventions based on the inflector

```python
class FileScanner:
    def __init__(self, base_paths, registry, inflector):
        self.base_paths = base_paths
        self.registry = registry
        self.inflector = inflector
        
    def scan(self):
        """Scan all base paths and register modules."""
        for base_path in self.base_paths:
            self._scan_directory(base_path, self._derive_namespace(base_path))
    
    def _scan_directory(self, directory, namespace):
        """Recursively scan a directory and register modules."""
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            
            if os.path.isdir(path):
                # Handle directories (potentially packages)
                if os.path.exists(os.path.join(path, '__init__.py')):
                    # This is a package
                    package_name = self._path_to_module_name(path, namespace)
                    init_path = os.path.join(path, '__init__.py')
                    self.registry.register(package_name, init_path, is_package=True)
                    
                    # Scan subdirectory with updated namespace
                    self._scan_directory(path, package_name)
            
            elif item.endswith('.py') and item != '__init__.py':
                # Handle Python modules
                module_name = self._path_to_module_name(path, namespace)
                self.registry.register(module_name, path, is_package=False)
    
    def _path_to_module_name(self, path, namespace):
        """Convert a file path to a module name."""
        rel_path = os.path.relpath(path, self._get_base_path(namespace))
        
        if rel_path.endswith('.py'):
            rel_path = rel_path[:-3]  # Remove .py extension
            
        parts = []
        if namespace:
            parts.append(namespace)
            
        parts.extend([self.inflector.camelize(p) if i == len(parts) - 1 else p 
                      for i, p in enumerate(rel_path.split(os.path.sep))])
        
        return '.'.join(parts)
```

## Eager Loading Implementation

For eager loading, we'll add methods to load all modules at once:

```python
def eager_load(self):
    """Load all modules in the registry immediately."""
    for module_name in self.registry.get_all_modules():
        if not self.registry.is_loaded(module_name):
            try:
                importlib.import_module(module_name)
            except Exception as e:
                # Handle loading errors
                logging.error(f"Error loading module {module_name}: {e}")
```

## Reloading Implementation

For reloading, we'll implement a mechanism to:

1. Detect file changes
2. Unload affected modules
3. Reload them with updated code

```python
def reload_module(self, module_name):
    """Reload a specific module and its dependents."""
    if not self.registry.is_loaded(module_name):
        return
        
    # Get all dependent modules that need to be reloaded
    dependents = self.registry.get_dependents(module_name)
    all_modules = [module_name] + dependents
    
    # Unload all modules in reverse dependency order
    for mod_name in reversed(all_modules):
        if mod_name in sys.modules:
            # Remove from sys.modules
            del sys.modules[mod_name]
            # Mark as unloaded in registry
            self.registry.mark_unloaded(mod_name)
    
    # Reload the modules in correct dependency order
    for mod_name in all_modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            logging.error(f"Error reloading module {mod_name}: {e}")
```

## Thread Safety Considerations

To ensure thread safety, we'll need to:

1. Use locks when modifying the registry
2. Handle import locks correctly
3. Ensure atomic operations during module reloading

```python
class ThreadSafeRegistry:
    def __init__(self):
        self._registry = {}
        self._lock = threading.RLock()
        
    def register(self, module_name, filepath, is_package=False):
        with self._lock:
            self._registry[module_name] = {
                'path': filepath,
                'is_package': is_package,
                'loaded': False,
                'mtime': None,
                'dependents': []
            }
```

## Error Handling

We'll implement comprehensive error handling to:

1. Detect and report import errors
2. Provide meaningful error messages
3. Fallback gracefully when autoloading fails

```python
class AutoloadError(Exception):
    """Base exception for PyAutoload errors."""
    pass
    
class ModuleNotFoundError(AutoloadError):
    """Raised when a module is not found in the registry."""
    pass
    
class CircularDependencyError(AutoloadError):
    """Raised when a circular dependency is detected."""
    pass
```

## API Design

The public API will be simple and concise:

```python
# Initialize the autoloader
loader = AutoLoader(base_path="myapp", top_level="myapp")

# Configure the loader
loader.ignore("tmp", "test")
loader.inflect({"html_parser": "HTMLParser"})

# Set up autoloading
loader.setup()

# For production, eager load all modules
loader.eager_load()

# For development, enable reloading
loader.enable_reloading()
```

## Performance Considerations

To maintain good performance, we'll:

1. Minimize file system operations
2. Cache module specs and registry data
3. Use efficient algorithms for dependency resolution
4. Provide benchmarking tools for measuring impact

## Compatibility

We'll ensure compatibility with:

1. Different Python versions (3.6+)
2. Various project structures
3. Common frameworks and libraries
4. Different operating systems
