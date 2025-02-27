This file is a merged representation of the selected files.
Generated on: 2025-02-27T14:42:21.239371

# File Summary

## Repository Structure
```
src/pyautoload/__init__.py
src/pyautoload/autoloader.py
src/pyautoload/file_scanner.py
src/pyautoload/file_watcher.py
src/pyautoload/import_hooks.py
src/pyautoload/inflector.py
src/pyautoload/module_registry.py
docs/test_plan.md
docs/technical_design.md
docs/tasks.md
docs/requirements.md
docs/PRD.md
docs/implementation_plan.md
docs/design_challenges.md
tests/__init__.py
tests/conftest.py
tests/test_autoloader.py
tests/test_file_watcher.py
tests/test_import_hooks.py
tests/test_inflector.py
tests/test_integration.py
tests/test_module_registry.py
README.md
setup.py
TASK.md
requirements-dev.txt
```

# Repository Files

## File: src/pyautoload/__init__.py
```py
from pyautoload.autoloader import AutoLoader
from pyautoload.inflector import Inflector
from pyautoload.file_watcher import FileWatcher
from pyautoload.module_registry import ModuleRegistry
from pyautoload.file_scanner import FileScanner
from pyautoload.import_hooks import (
    PyAutoloadFinder,
    PyAutoloadLoader,
    AutoloadError,
    ModuleNotFoundError,
    CircularDependencyError
)

__version__ = '0.1.0'

__all__ = [
    'AutoLoader',
    'Inflector',
    'FileWatcher',
    'ModuleRegistry',
    'FileScanner',
    'PyAutoloadFinder',
    'PyAutoloadLoader',
    'AutoloadError',
    'ModuleNotFoundError',
    'CircularDependencyError',
]
```

## File: src/pyautoload/autoloader.py
```py
"""
AutoLoader implementation.

This module implements the main AutoLoader class that coordinates the entire autoloading system.
"""
import os
import sys
import importlib
import threading
from .inflector import Inflector
from .file_watcher import FileWatcher
from .file_scanner import FileScanner
from .module_registry import ModuleRegistry
from .import_hooks import PyAutoloadFinder, PyAutoloadLoader, AutoloadError


class AutoLoader:
    """
    Main AutoLoader class for PyAutoload.
    
    This class coordinates the entire autoloading system, including:
    - Discovering and registering modules
    - Configuring import hooks
    - Providing eager loading and reloading capabilities
    """
    
    def __init__(self, base_path=None, root_paths=None, top_level=None, inflector=None):
        """
        Initialize the AutoLoader.
        
        Args:
            base_path (str, optional): Base path to search for modules
            root_paths (list, optional): List of root paths to search for modules
            top_level (str, optional): Top-level namespace for modules
            inflector (Inflector, optional): Custom inflector for name conversion
        """
        self.base_paths = []
        if base_path:
            self.base_paths.append(os.path.abspath(base_path))
        if root_paths:
            self.base_paths.extend([os.path.abspath(p) for p in root_paths])
            
        self.top_level = top_level
        self.inflector = inflector or Inflector()
        self.registry = ModuleRegistry()
        self.ignored_patterns = []
        self.custom_inflections = {}
        self.watcher = None
        self.finder = None
        self._lock = threading.RLock()
        self._setup_done = False
    
    def add_root(self, path):
        """
        Add a root path to search for modules.
        
        Args:
            path (str): Path to add
        """
        abs_path = os.path.abspath(path)
        with self._lock:
            if abs_path not in self.base_paths:
                self.base_paths.append(abs_path)
    
    def ignore(self, *patterns):
        """
        Add patterns to ignore when scanning for modules.
        
        Args:
            *patterns: Patterns to ignore
        """
        with self._lock:
            self.ignored_patterns.extend(patterns)
    
    def inflect(self, inflections):
        """
        Add custom inflections for specific module names.
        
        Args:
            inflections (dict): Dictionary mapping file names to module names
        """
        with self._lock:
            self.custom_inflections.update(inflections)
            self.inflector.inflect(inflections)
    
    def setup(self):
        """
        Set up the autoloader.
        
        This method:
        - Scans the base paths for modules
        - Registers them in the registry
        - Sets up the import hooks
        """
        with self._lock:
            if self._setup_done:
                return
                
            # Validate that we have at least one base path
            if not self.base_paths:
                raise ValueError("No base paths provided. Use add_root() or provide a base_path.")
            
            # Scan for modules
            scanner = FileScanner(
                self.base_paths,
                self.registry,
                self.inflector,
                self.ignored_patterns
            )
            scanner.scan()
            
            # Create and register the finder
            self.finder = PyAutoloadFinder(
                self.base_paths,
                self.top_level,
                self.inflector,
                self.registry
            )
            
            self._setup_done = True
    
    def eager_load(self):
        """
        Eagerly load all modules in the registry.
        
        This method imports all modules at once, which can be useful in production
        to ensure all modules are loaded and validated at startup.
        """
        if not self._setup_done:
            self.setup()
            
        for module_name in self.registry.get_all_modules():
            if not self.registry.is_loaded(module_name):
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"Error loading module {module_name}: {e}")
    
    def enable_reloading(self, callback=None):
        """
        Enable reloading of modules when files change.
        
        Args:
            callback (callable, optional): Callback to call when a module is reloaded
        """
        if not self._setup_done:
            self.setup()
            
        # Create a file watcher
        self.watcher = FileWatcher(self.base_paths)
        
        # Set up a callback to reload modules when files change
        def on_file_changed(file_path):
            # Find the module name for this file
            module_name = self._find_module_for_file(file_path)
            if module_name:
                self.reload_module(module_name)
                if callback:
                    callback(module_name)
        
        self.watcher.on_change(on_file_changed)
        self.watcher.start()
    
    def reload_module(self, module_name):
        """
        Reload a specific module and its dependents.
        
        Args:
            module_name (str): Name of the module to reload
        """
        if not self.registry.contains(module_name):
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
                print(f"Error reloading module {mod_name}: {e}")
    
    def reload(self):
        """Reload all modules that have been modified."""
        if not self._setup_done:
            self.setup()
            
        for module_name in self.registry.get_all_modules():
            if self.registry.is_loaded(module_name):
                file_path = self.registry.get_path(module_name)
                current_mtime = os.path.getmtime(file_path)
                loaded_mtime = self.registry.get_mtime(module_name)
                
                if current_mtime > loaded_mtime:
                    self.reload_module(module_name)
    
    def _find_module_for_file(self, file_path):
        """
        Find the module name for a file path.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Module name, or None if not found
        """
        for module_name in self.registry.get_all_modules():
            if self.registry.get_path(module_name) == file_path:
                return module_name
        return None
    
    def __enter__(self):
        """Enter context manager."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.watcher:
            self.watcher.stop()
            
        # Remove our finder from sys.meta_path
        if self.finder and self.finder in sys.meta_path:
            sys.meta_path.remove(self.finder)

```

## File: src/pyautoload/file_scanner.py
```py
"""
File scanner for PyAutoload.

This module implements the file system scanner that discovers modules and packages.
"""
import os
import importlib.util


class FileScanner:
    """
    File system scanner for PyAutoload.
    
    This class is responsible for:
    - Traversing directories to find Python modules and packages
    - Registering modules in the registry
    - Applying naming conventions based on the inflector
    """
    
    def __init__(self, base_paths, registry, inflector, ignored_patterns=None):
        """
        Initialize the scanner.
        
        Args:
            base_paths (list): List of base paths to search for modules
            registry (ModuleRegistry): Registry to populate
            inflector (Inflector): Inflector for name conversion
            ignored_patterns (list, optional): List of patterns to ignore
        """
        self.base_paths = base_paths
        self.registry = registry
        self.inflector = inflector
        self.ignored_patterns = ignored_patterns or []
    
    def scan(self):
        """Scan all base paths and register modules."""
        for base_path in self.base_paths:
            if not os.path.isdir(base_path):
                continue
                
            namespace = self._derive_namespace(base_path)
            
            # Register the top-level package if it doesn't exist
            if namespace:
                top_level_init = os.path.join(base_path, '__init__.py')
                if os.path.exists(top_level_init):
                    self.registry.register(namespace, top_level_init, is_package=True)
                else:
                    # Register as a virtual package
                    self.registry.register(namespace, None, is_package=True)
                    
            # For a clean approach, let's directly scan inside the base path
            # rather than treating the base path as part of the namespace
            for item in os.listdir(base_path):
                path = os.path.join(base_path, item)
                
                if self._should_ignore(path):
                    continue
                
                if os.path.isdir(path):
                    if os.path.exists(os.path.join(path, '__init__.py')):
                        # This is a package
                        # Register as namespace.package
                        package_name = f"{namespace}.{item}" if namespace else item
                        init_path = os.path.join(path, '__init__.py')
                        self.registry.register(package_name, init_path, is_package=True)
                        
                        # Now scan the contents of this directory
                        self._scan_package_directory(path, package_name)
                
                elif item.endswith('.py') and item != '__init__.py':
                    # Handle Python modules at the top level
                    module_name = f"{namespace}.{item[:-3]}" if namespace else item[:-3]
                    self.registry.register(module_name, path, is_package=False)
    
    def _scan_package_directory(self, directory, namespace):
        """
        Recursively scan a directory and register modules.
        
        Args:
            directory (str): Directory to scan
            namespace (str): Namespace for modules in this directory
        """
        if self._should_ignore(directory):
            return
            
        try:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                
                if self._should_ignore(path):
                    continue
                
                if os.path.isdir(path):
                    # Handle directories (potentially packages)
                    if os.path.exists(os.path.join(path, '__init__.py')):
                        # This is a package
                        package_name = f"{namespace}.{item}"
                        init_path = os.path.join(path, '__init__.py')
                        self.registry.register(package_name, init_path, is_package=True)
                        
                        # Scan subdirectory with updated namespace
                        self._scan_package_directory(path, package_name)
                
                elif item.endswith('.py') and item != '__init__.py':
                    # Handle Python modules
                    module_name = f"{namespace}.{item[:-3]}"
                    self.registry.register(module_name, path, is_package=False)
        except (PermissionError, FileNotFoundError):
            # Skip directories we can't read
            pass
    
    def _path_to_module_name(self, path, namespace):
        """
        Convert a file path to a module name.
        
        Args:
            path (str): Path to convert
            namespace (str): Namespace for the module
            
        Returns:
            str: Full module name
        """
        base_path = self._get_base_path(namespace)
        
        # Handle virtual packages (None path)
        if path is None:
            return namespace
            
        rel_path = os.path.relpath(path, os.path.dirname(base_path))
        
        if rel_path.endswith('.py'):
            rel_path = rel_path[:-3]  # Remove .py extension
            
        parts = []
        if namespace:
            parts.append(namespace)
            
        # Split the path and add each part to the module name
        path_parts = rel_path.split(os.path.sep)
        
        # For module files, construct the module name correctly
        if os.path.isfile(path) and path.endswith('.py'):
            # For regular python modules, only add the file path parts as-is
            if path_parts[-1] != '__init__':
                module_parts = path_parts
            else:
                # For __init__.py, exclude the filename
                module_parts = path_parts[:-1]
        else:
            # For directories, keep the original names
            module_parts = path_parts
            
        parts.extend(module_parts)
        
        # Join parts with dots to form the full module name
        return '.'.join(filter(None, parts))
    
    def _derive_namespace(self, base_path):
        """
        Derive a namespace from a base path.
        
        Args:
            base_path (str): Base path to derive namespace from
            
        Returns:
            str: Derived namespace, or None if not applicable
        """
        # If a namespace was provided during initialization, use that
        # Otherwise, try to derive it from the package name
        package_name = os.path.basename(os.path.normpath(base_path))
        return package_name if package_name != '.' else None
    
    def _get_base_path(self, namespace):
        """
        Get the base path for a namespace.
        
        Args:
            namespace (str): Namespace to get base path for
            
        Returns:
            str: Base path for the namespace
        """
        for base_path in self.base_paths:
            if namespace == self._derive_namespace(base_path):
                return base_path
        return self.base_paths[0] if self.base_paths else '.'
    
    def _should_ignore(self, path):
        """
        Check if a path should be ignored.
        
        Args:
            path (str): Path to check
            
        Returns:
            bool: True if the path should be ignored, False otherwise
        """
        basename = os.path.basename(path)
        
        # Always ignore these patterns
        if basename.startswith('.') or basename.startswith('__') or basename == 'setup.py':
            return True
            
        # Check custom ignored patterns
        for pattern in self.ignored_patterns:
            if pattern in path:
                return True
                
        return False

```

## File: src/pyautoload/file_watcher.py
```py
"""
Module that provides file watching functionality for PyAutoload.
"""
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FileWatcher:
    """
    Watches for file changes in specified directories.
    
    This class uses the watchdog library to monitor file changes
    and trigger callbacks when files are modified, created, or deleted.
    """
    
    def __init__(self, dirs, patterns=None):
        """
        Initialize a new FileWatcher.
        
        Args:
            dirs (list): A list of directories to watch
            patterns (list, optional): A list of patterns to match (e.g., ["*.py"])
        
        Raises:
            ValueError: If dirs is None or empty
        """
        if not dirs:
            raise ValueError("dirs must be a non-empty list of directories")
        
        self.dirs = dirs
        self.patterns = patterns or ["*.py"]
        self.observer = None
        self.handlers = []
        self.callbacks = []
    
    def on_change(self, callback):
        """
        Register a callback to be called when files change.
        
        Args:
            callback (callable): A function to call when files change
                                The function should accept an event parameter
        """
        self.callbacks.append(callback)
    
    def _on_any_event(self, event):
        """
        Handle watchdog events.
        
        Args:
            event (watchdog.events.FileSystemEvent): The event to handle
        """
        for callback in self.callbacks:
            callback(event)
    
    def start(self):
        """
        Start watching for file changes.
        """
        if self.observer:
            return
        
        self.observer = Observer()
        
        # Create event handler
        event_handler = PatternMatchingEventHandler(
            patterns=self.patterns,
            ignore_directories=True,
            case_sensitive=False
        )
        event_handler.on_any_event = self._on_any_event
        self.handlers.append(event_handler)
        
        # Schedule the observer
        for directory in self.dirs:
            if os.path.isdir(directory):
                self.observer.schedule(event_handler, directory, recursive=True)
        
        # Start the observer
        self.observer.start()
    
    def stop(self):
        """
        Stop watching for file changes.
        """
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

```

## File: src/pyautoload/import_hooks.py
```py
"""
Import hooks for PyAutoload.

This module implements the custom meta path finder and loader for PyAutoload.
"""
import os
import sys
import importlib.abc
import importlib.machinery
from .inflector import Inflector
from .module_registry import ModuleRegistry


class PyAutoloadFinder(importlib.abc.MetaPathFinder):
    """
    Custom meta path finder for PyAutoload.
    
    This finder is responsible for:
    - Finding module specs based on naming conventions
    - Maintaining the module registry
    - Handling package and module differentiation
    """
    
    def __init__(self, base_paths, namespace=None, inflector=None, registry=None):
        """
        Initialize the finder.
        
        Args:
            base_paths (list): List of base paths to search for modules
            namespace (str, optional): Optional namespace for all modules
            inflector (Inflector, optional): Custom inflector for name conversion
            registry (ModuleRegistry, optional): Custom registry to use
        """
        self.base_paths = base_paths
        self.namespace = namespace
        self.inflector = inflector or Inflector()
        self.registry = registry or ModuleRegistry()
        
        # Register in sys.meta_path
        if self not in sys.meta_path:
            sys.meta_path.insert(0, self)
    
    def find_spec(self, fullname, path=None, target=None):
        """
        Find the spec for a module.
        
        Args:
            fullname (str): Full name of the module
            path (list, optional): List of paths to search (for submodules)
            target (module, optional): Target module
            
        Returns:
            ModuleSpec: Spec for the module, or None if not found
        """
        # Check if this module is in our registry
        if not self.registry.contains(fullname):
            # Check if this is a parent module of a registered module
            # For example, if 'app.models.user' is registered, but 'app' is not,
            # we should still create a spec for 'app'
            parent_module = self._find_parent_module(fullname)
            if parent_module:
                # Create an empty module for the parent
                return self._create_namespace_package_spec(fullname)
            return None
            
        # Get the file path for this module
        try:
            filepath = self.registry.get_path(fullname)
            is_package = self.registry.is_package(fullname)
        except KeyError:
            return None
        
        # Create a loader
        loader = PyAutoloadLoader(fullname, filepath, self.registry)
        
        # Create a spec with our custom loader
        if is_package:
            # This is a package
            spec = importlib.machinery.ModuleSpec(
                name=fullname,
                loader=loader,
                origin=filepath,
            )
            spec.submodule_search_locations = [os.path.dirname(filepath)]
        else:
            # This is a module
            spec = importlib.machinery.ModuleSpec(
                name=fullname,
                loader=loader,
                origin=filepath
            )
            
        return spec
        
    def _find_parent_module(self, fullname):
        """
        Find the parent module for a given module name.
        
        Args:
            fullname (str): Full name of the module
            
        Returns:
            str: Parent module name if any registered module starts with it, None otherwise
        """
        parts = fullname.split('.')
        for i in range(1, len(parts)):
            parent = '.'.join(parts[:i])
            for registered in self.registry.get_all_modules():
                if registered.startswith(parent + '.'):
                    return parent
        return None
        
    def _create_namespace_package_spec(self, fullname):
        """
        Create a namespace package spec for a parent module.
        
        Args:
            fullname (str): Full name of the module
            
        Returns:
            ModuleSpec: Spec for the namespace package
        """
        spec = importlib.machinery.ModuleSpec(
            name=fullname,
            loader=None,
            is_package=True
        )
        
        # Find all possible paths for this namespace package
        paths = []
        parts = fullname.split('.')
        if len(parts) == 1:
            # Top-level package, use base_paths
            for base_path in self.base_paths:
                path = os.path.join(base_path, parts[0])
                if os.path.isdir(path):
                    paths.append(path)
        
        spec.submodule_search_locations = paths if paths else [None]
        return spec
    
    def invalidate_caches(self):
        """Invalidate any caches maintained by the finder."""
        # Nothing to do here since we don't maintain a cache beyond the registry
        pass


class PyAutoloadLoader(importlib.abc.Loader):
    """
    Custom loader for PyAutoload.
    
    This loader is responsible for:
    - Creating module objects
    - Executing module code
    - Updating the registry when modules are loaded
    """
    
    def __init__(self, fullname, filepath, registry):
        """
        Initialize the loader.
        
        Args:
            fullname (str): Full name of the module
            filepath (str): Path to the module's file
            registry (ModuleRegistry): Registry to update
        """
        self.fullname = fullname
        self.filepath = filepath
        self.registry = registry
    
    def create_module(self, spec):
        """
        Create a new module.
        
        Args:
            spec (ModuleSpec): Spec for the module
            
        Returns:
            module: The module object, or None to use Python's default
        """
        # Return None to use Python's default module creation
        return None
    
    def exec_module(self, module):
        """
        Execute a module's code.
        
        Args:
            module (module): Module object to execute
        """
        # Load source code from file
        with open(self.filepath, 'rb') as f:
            source = f.read()
            
        # Compile and execute the module
        code = compile(source, self.filepath, 'exec')
        exec(code, module.__dict__)
        
        # Update the registry
        self.registry.mark_loaded(self.fullname, os.path.getmtime(self.filepath))


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

## File: src/pyautoload/inflector.py
```py
"""
Module that provides inflection functionality for PyAutoload.
"""


class Inflector:
    """
    Handles conversion between file names and module/class names.
    
    This class is responsible for converting:
    - Snake case file names to CamelCase class/module names
    - Supporting custom inflections for special cases like acronyms
    """
    
    def __init__(self):
        """Initialize a new Inflector with empty custom inflections."""
        self.custom_inflections = {}
    
    def camelize(self, basename, _=None):
        """
        Convert a snake_case basename to CamelCase.
        
        Args:
            basename (str): The basename to camelize (e.g., "users_controller")
            _ (any, optional): Placeholder parameter for compatibility with Zeitwerk
            
        Returns:
            str: The camelized name (e.g., "UsersController")
        """
        # Check for custom inflections first
        if basename in self.custom_inflections:
            return self.custom_inflections[basename]
        
        # Otherwise, perform standard camelization
        return ''.join(x.capitalize() or '_' for x in basename.split('_'))
    
    def inflect(self, inflections):
        """
        Add custom inflections to the inflector.
        
        Args:
            inflections (dict): A dictionary mapping from snake_case to CamelCase
                               Example: {"html_parser": "HTMLParser"}
        """
        self.custom_inflections.update(inflections)

```

## File: src/pyautoload/module_registry.py
```py
"""
Module registry for PyAutoload.

This registry tracks modules, their file paths, dependencies, and loading status.
"""
import os
import threading


class ModuleRegistry:
    """
    Registry for tracking modules, their file paths, and loading status.
    
    This class is responsible for:
    - Registering modules and packages
    - Mapping module names to file paths
    - Tracking which modules are loaded
    - Managing dependencies between modules
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._modules = {}
        self._lock = threading.RLock()
    
    def register(self, module_name, filepath, is_package=False):
        """
        Register a module in the registry.
        
        Args:
            module_name (str): Full name of the module (e.g., "app.models.user")
            filepath (str): Absolute path to the module's file
            is_package (bool): Whether this module is a package
        """
        with self._lock:
            self._modules[module_name] = {
                'path': filepath,
                'is_package': is_package,
                'loaded': False,
                'mtime': None,
                'dependencies': set(),
                'dependents': set()
            }
    
    def unregister(self, module_name):
        """
        Remove a module from the registry.
        
        Args:
            module_name (str): Full name of the module to remove
        """
        with self._lock:
            if module_name in self._modules:
                # Remove from dependencies and dependents
                for dep in self._modules[module_name]['dependencies']:
                    if dep in self._modules:
                        self._modules[dep]['dependents'].discard(module_name)
                
                for dep in self._modules[module_name]['dependents']:
                    if dep in self._modules:
                        self._modules[dep]['dependencies'].discard(module_name)
                
                # Remove the module itself
                del self._modules[module_name]
    
    def contains(self, module_name):
        """
        Check if a module is registered.
        
        Args:
            module_name (str): Full name of the module to check
            
        Returns:
            bool: True if the module is registered, False otherwise
        """
        with self._lock:
            return module_name in self._modules
    
    def get_path(self, module_name):
        """
        Get the file path for a module.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            str: Absolute path to the module's file
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return self._modules[module_name]['path']
    
    def is_package(self, module_name):
        """
        Check if a module is a package.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            bool: True if the module is a package, False otherwise
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return self._modules[module_name]['is_package']
    
    def is_loaded(self, module_name):
        """
        Check if a module is loaded.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            bool: True if the module is loaded, False otherwise
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return self._modules[module_name]['loaded']
    
    def mark_loaded(self, module_name, mtime):
        """
        Mark a module as loaded.
        
        Args:
            module_name (str): Full name of the module
            mtime (float): Modification time of the module's file
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            self._modules[module_name]['loaded'] = True
            self._modules[module_name]['mtime'] = mtime
    
    def mark_unloaded(self, module_name):
        """
        Mark a module as unloaded.
        
        Args:
            module_name (str): Full name of the module
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            self._modules[module_name]['loaded'] = False
    
    def get_mtime(self, module_name):
        """
        Get the modification time of a module's file.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            float: Modification time of the module's file, or None if not loaded
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return self._modules[module_name]['mtime']
    
    def add_dependency(self, module_name, dependency):
        """
        Add a dependency between modules.
        
        Args:
            module_name (str): Full name of the dependent module
            dependency (str): Full name of the dependency module
            
        Raises:
            KeyError: If either module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            if dependency not in self._modules:
                raise KeyError(f"Module '{dependency}' is not registered")
            
            self._modules[module_name]['dependencies'].add(dependency)
            self._modules[dependency]['dependents'].add(module_name)
    
    def get_dependencies(self, module_name):
        """
        Get the dependencies of a module.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            list: List of module names that this module depends on
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return list(self._modules[module_name]['dependencies'])
    
    def get_dependents(self, module_name):
        """
        Get the modules that depend on this module.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            list: List of module names that depend on this module
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return list(self._modules[module_name]['dependents'])
    
    def get_all_modules(self):
        """
        Get all registered module names.
        
        Returns:
            list: List of all registered module names
        """
        with self._lock:
            return list(self._modules.keys())

```

## File: docs/test_plan.md
```md
# PyAutoload Test Plan

This document outlines a comprehensive test plan for the PyAutoload library, focusing on testing the integration with Python's import system and ensuring reliability in real-world scenarios.

## Test-Driven Development Approach

We will follow a strict TDD approach:

1. Write failing tests first
2. Implement the minimum code required to pass tests
3. Refactor for clarity and performance
4. Repeat for each component and feature

## Test Hierarchy

### 1. Unit Tests

Test individual components in isolation:

#### 1.1 Inflector Tests

- Test basic camelization
- Test custom inflections
- Test edge cases (numbers, special characters)

#### 1.2 Module Registry Tests

- Test registration of modules
- Test lookup functionality
- Test dependency tracking
- Test concurrency handling

#### 1.3 File Scanner Tests

- Test directory traversal
- Test file path to module name conversion
- Test handling of packages vs. modules
- Test ignored directories and files

#### 1.4 Import Hook Tests

- Test finder functionality
- Test loader functionality
- Test module spec creation
- Test integration with sys.meta_path

### 2. Integration Tests

Test components working together:

#### 2.1 Basic Import Tests

- Test importing simple modules
- Test importing packages
- Test nested packages
- Test relative imports

#### 2.2 Eager Loading Tests

- Test loading all modules
- Test loading specific namespaces
- Test handling of import errors
- Test loading order

#### 2.3 Reloading Tests

- Test file change detection
- Test module reloading
- Test handling of dependent modules
- Test concurrency during reloading

### 3. System Tests

Test the complete system with realistic scenarios:

#### 3.1 Project Structure Tests

- Test with different project structures
- Test with nested namespaces
- Test with circular dependencies
- Test with non-standard naming

#### 3.2 Performance Tests

- Test import time compared to standard imports
- Test memory usage
- Test scalability with large projects
- Test concurrent import scenarios

#### 3.3 Compatibility Tests

- Test with different Python versions
- Test with different operating systems
- Test with popular frameworks
- Test with various import patterns

## Test Fixtures

We will create comprehensive test fixtures:

### 1. Sample Project Structure

```
sample_app/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   └── product.py
├── controllers/
│   ├── __init__.py
│   ├── users_controller.py
│   └── products_controller.py
└── services/
    ├── __init__.py
    ├── authentication.py
    └── authorization.py
```

### 2. Edge Case Fixtures

- Circular dependency examples
- Non-standard naming examples
- Import error examples
- Thread safety test cases

### 3. Mock Import System

Create a controlled environment for testing import hooks:

```python
class MockMetaPath:
    def __init__(self):
        self.finders = []
        
    def find_spec(self, fullname, path=None, target=None):
        for finder in self.finders:
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                return spec
        return None
```

## Test Implementation

### 1. Example Unit Test: Inflector

```python
def test_camelize():
    inflector = Inflector()
    assert inflector.camelize("user") == "User"
    assert inflector.camelize("users_controller") == "UsersController"
    assert inflector.camelize("html_parser") == "HtmlParser"
    
def test_custom_inflections():
    inflector = Inflector()
    inflector.inflect({
        "html_parser": "HTMLParser",
        "json_api": "JSONAPI"
    })
    assert inflector.camelize("html_parser") == "HTMLParser"
    assert inflector.camelize("json_api") == "JSONAPI"
```

### 2. Example Integration Test: Module Loading

```python
def test_module_loading(sample_project):
    # Set up autoloader with sample project
    loader = AutoLoader(base_path=sample_project, top_level="sample_app")
    loader.setup()
    
    # Test importing a module
    import sample_app.models.user
    assert hasattr(sample_app.models.user, "User")
    
    # Test importing a controller
    import sample_app.controllers.users_controller
    assert hasattr(sample_app.controllers.users_controller, "UsersController")
```

### 3. Example System Test: Reloading

```python
def test_module_reloading(sample_project):
    # Set up autoloader with reloading enabled
    loader = AutoLoader(base_path=sample_project, top_level="sample_app")
    loader.setup()
    loader.enable_reloading()
    
    # Import a module
    import sample_app.models.user
    original_user = sample_app.models.user.User
    
    # Modify the module file
    user_path = os.path.join(sample_project, "models", "user.py")
    with open(user_path, "a") as f:
        f.write("\nclass NewClass:\n    pass\n")
    
    # Trigger reloading
    time.sleep(0.1)  # Give the file watcher time to detect changes
    loader.reload()
    
    # Check that the module was reloaded
    import sample_app.models.user
    assert hasattr(sample_app.models.user, "NewClass")
    assert sample_app.models.user.User is not original_user
```

## Test Coverage Goals

We aim for:

- **90%+ line coverage** for core functionality
- **100% coverage** for critical components:
  - Import hooks
  - Module registry
  - Reloading mechanism
- **Edge case coverage** for:
  - Thread safety
  - Error handling
  - Compatibility issues

## Test Automation

We'll set up:

1. **Continuous Integration** via GitHub Actions
2. **Automated test runs** on multiple Python versions
3. **Coverage reporting** in CI
4. **Benchmark tracking** for performance tests

## Test Categories

Our test suite will be organized into categories:

### 1. Fast Tests

- Unit tests and simple integration tests
- Run on every commit
- Should complete in under 10 seconds

### 2. Standard Tests

- Full integration tests
- Run on pull requests
- Should complete in under 2 minutes

### 3. Extended Tests

- System tests, compatibility tests, and benchmarks
- Run before releases
- May take several minutes to complete

## Testing Tools

We'll use:

- **pytest** as the primary test framework
- **pytest-cov** for coverage reporting
- **pytest-benchmark** for performance testing
- **pytest-mock** for mocking
- **pytest-xdist** for parallel test execution

## Mocking Strategy

For testing import hooks without affecting the global import system:

```python
@contextmanager
def isolated_meta_path():
    """Context manager that isolates sys.meta_path changes."""
    original_meta_path = sys.meta_path.copy()
    try:
        yield
    finally:
        sys.meta_path = original_meta_path

def test_finder_integration():
    with isolated_meta_path():
        finder = PyAutoloadFinder(base_paths=["sample"])
        # Test finder functionality
        sys.meta_path.insert(0, finder)
        # ... test imports
```

## Test Implementation Schedule

1. **Week 1**: Core unit tests for Inflector, Registry
2. **Week 2**: Unit tests for Scanner, Import Hooks
3. **Week 3**: Integration tests for basic importing
4. **Week 4**: Integration tests for eager loading
5. **Week 5**: Integration tests for reloading
6. **Week 6**: System tests for real-world scenarios
7. **Week 7**: Performance and compatibility tests
8. **Week 8**: Documentation tests and examples

```

## File: docs/technical_design.md
```md
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

```

## File: docs/tasks.md
```md
# Tasks

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

```

## File: docs/requirements.md
```md
# Requirements

## Runtime Requirements
- **Python**: 3.6 or higher.
- **Dependencies**:
  - `watchdog`: For file watching in development mode.

## Development Requirements
- `pytest`: For running tests.
- `flake8`: For code linting.
- `sphinx`: For generating documentation.

```

## File: docs/PRD.md
```md
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

```

## File: docs/implementation_plan.md
```md
# PyAutoload Implementation Plan

Based on our assessment of the design challenges, this document outlines a revised implementation plan for PyAutoload that addresses the complexities of creating a Zeitwerk-like autoloader for Python.

## Phase 1: Core Import Hook System

### 1.1 Custom MetaPathFinder Implementation

- Create a `PyAutoloadFinder` class that implements `importlib.abc.MetaPathFinder`
- Implement the `find_spec` method to locate modules based on naming conventions
- Add configuration options for root directories and top-level namespaces
- Set up module mapping registry

```python
# Initial structure
class PyAutoloadFinder(MetaPathFinder):
    def __init__(self, base_paths, inflector=None):
        self.base_paths = base_paths
        self.inflector = inflector or Inflector()
        self.module_registry = {}
    
    def find_spec(self, fullname, path, target=None):
        # Implementation to map module names to file paths
        # based on conventions
        pass
```

### 1.2 Custom Loader Implementation

- Create a `PyAutoloadLoader` class that implements `importlib.abc.Loader`
- Implement the `create_module` and `exec_module` methods
- Handle module caching and initialization
- Support package loading via `__init__.py` files

### 1.3 Module Registry

- Design a module registry to track:
  - Module name to file path mappings
  - Loaded vs. discovered modules
  - Parent-child relationships between modules
  - Module dependencies

### 1.4 Integration with Python's Import System

- Register the finder with `sys.meta_path`
- Handle edge cases with existing import mechanisms
- Ensure proper interaction with `sys.modules` cache
- Set up configuration for multiple loaders in the same process

## Phase 2: Directory Scanning and Module Discovery

### 2.1 File System Scanner

- Implement a scanner to traverse directories recursively
- Skip ignored directories and files
- Handle nested packages correctly
- Build initial module registry from file system structure

### 2.2 Naming Convention Support

- Enhance the inflector to handle Python-specific conventions
- Support mapping between file paths and module/class names
- Add configuration options for customization
- Handle special cases (e.g., pluralization, acronyms)

### 2.3 Module Auto-vivification

- Implement module creation for directories without explicit imports
- Handle `__init__.py` file generation or virtual modules
- Support accessing nested modules via parent modules
- Create a mechanism similar to Ruby's constant lookup

## Phase 3: Eager Loading and Reloading

### 3.1 Eager Loading Implementation

- Add a method to load all discovered modules at once
- Ensure proper loading order based on dependencies
- Handle circular dependencies gracefully
- Provide configuration for eager loading specific namespaces

### 3.2 File Watching Mechanism

- Implement file watching using `watchdog`
- Detect changes to Python modules
- Handle file additions, modifications, and deletions
- Provide callbacks for custom reload handling

### 3.3 Module Reloading

- Implement safe module reloading
- Handle dependent module updates
- Clear caches and reset state properly
- Maintain thread safety during reloading

## Phase 4: Thread Safety and Error Handling

### 4.1 Thread Safety Implementation

- Add proper locking mechanisms
- Ensure atomic operations where needed
- Respect Python's import locks
- Document thread safety guarantees and limitations

### 4.2 Error Handling and Debugging

- Implement comprehensive error reporting
- Add debugging tools for import issues
- Include useful error messages for common problems
- Support for logging and tracing import activities

### 4.3 Edge Case Handling

- Handle circular dependencies
- Support for conditional imports
- Deal with dynamically generated modules
- Manage conflicts with other import hooks

## Phase 5: Documentation and Testing

### 5.1 Comprehensive Test Suite

- Unit tests for individual components
- Integration tests for the complete system
- Test cases for all identified edge cases
- Performance benchmarks

### 5.2 Documentation

- API reference documentation
- Usage examples and tutorials
- Troubleshooting guide
- Best practices for project structure

### 5.3 Sample Applications

- Create example applications demonstrating PyAutoload
- Show integration with popular frameworks
- Provide migration guides from manual imports

## Development Approach

We will continue to follow Test-Driven Development:

1. Write tests first for each component and feature
2. Implement the minimum required code to pass the tests
3. Refactor and optimize while maintaining test coverage
4. Address edge cases identified during testing

However, we'll revise our test structure to focus more on:

- Testing actual import behavior, not just class functionality
- Verifying correct interaction with Python's import system
- Testing thread safety and reloading mechanisms
- Handling of edge cases and error conditions

Each phase will include both tests and implementation before proceeding to the next phase to ensure we build on a solid foundation.

## Timeline

- **Phase 1**: Core Import Hook System - 2 weeks
- **Phase 2**: Directory Scanning and Module Discovery - 2 weeks
- **Phase 3**: Eager Loading and Reloading - 2 weeks
- **Phase 4**: Thread Safety and Error Handling - 1 week
- **Phase 5**: Documentation and Testing - 1 week

Total estimated time: 8 weeks

```

## File: docs/design_challenges.md
```md
# Design Challenges: Implementing Zeitwerk-like Autoloading in Python

## Core Challenges

### 1. Fundamental Differences Between Ruby and Python Import Systems

Ruby's constant resolution mechanism differs significantly from Python's import system:

- **Ruby**: Uses a global constant namespace and resolves constants at runtime with an auto-loading mechanism that can be hooked into
- **Python**: Uses explicit imports and a module-based system with a more structured lookup process

Zeitwerk leverages Ruby's constant resolution by intercepting constant lookup and dynamically loading the corresponding file. Python doesn't have an equivalent mechanism for intercepting constant resolution.

### 2. Python's Import System

Python's import system is structured around:

- A module cache (`sys.modules`)
- Import hooks (`sys.meta_path` and `sys.path_hooks`)
- Package initialization via `__init__.py` files
- A hierarchical namespace system

To implement Zeitwerk-like behavior, we'll need to create custom import hooks using the `importlib` machinery:

```python
# Conceptual example of using import hooks
import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_file_location

class PyAutoloadFinder(MetaPathFinder):
    # Implementation to find modules based on naming conventions
    pass

class PyAutoloadLoader(Loader):
    # Implementation to load modules when requested
    pass

# Register our finder in the import system
sys.meta_path.insert(0, PyAutoloadFinder())
```

### 3. Autovivification Challenges

Zeitwerk automatically creates modules for directories. In Python, this requires:

1. Creating module objects for directories
2. Registering these modules in `sys.modules`
3. Handling `__init__.py` files appropriately
4. Managing parent-child relationships between modules

### 4. Thread Safety Requirements

Both lazy loading and module reloading present thread safety challenges:

- Multiple threads may try to load the same module simultaneously
- Reloading a module while it's being used by another thread can cause inconsistencies
- Python's import system has its own locking mechanism we must respect

### 5. Integration with Existing Code

Python projects often use a variety of import styles and patterns:

- Relative imports
- Star imports
- Circular dependencies
- Import-time side effects

Our solution must handle these gracefully without breaking existing code.

## Proposed Architecture

### 1. Custom Import Hooks

Implement a `MetaPathFinder` and `Loader` that:

- Maps file paths to module names based on conventions
- Handles lazy loading via the import system
- Maintains a registry of discovered modules
- Respects package boundaries

### 2. Module Registry

Maintain a mapping between:

- File paths
- Module names
- Loaded module objects
- Dependencies between modules

### 3. File System Scanner

Create a scanner that:

- Traverses directories recursively
- Identifies Python modules and packages
- Builds the module registry
- Understands naming conventions

### 4. Reloading System

Implement a reloading mechanism that:

- Watches for file changes
- Safely reloads modified modules
- Updates dependent modules
- Handles edge cases like deleted files

### 5. Thread Safety

Ensure thread safety through:

- Proper locking mechanisms
- Atomic operations where possible
- Respecting Python's import locks
- Clear documentation about thread-safety guarantees

```

## File: tests/__init__.py
```py

```

## File: tests/conftest.py
```py
"""
PyAutoload test fixtures and configuration.
"""
import os
import sys
import tempfile
import shutil
import pytest

# Add the source directory to the path so tests can import the package
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, src_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_project(temp_dir):
    """
    Create a sample project structure for testing autoloading.
    
    Directory structure:
    /sample_app
      /__init__.py
      /models
        /__init__.py
        /user.py
      /controllers
        /__init__.py
        /users_controller.py
      /services
        /__init__.py
        /user_service.py
        /auth
          /__init__.py
          /authentication_service.py
    """
    project_path = os.path.join(temp_dir, "sample_app")
    os.makedirs(project_path)
    
    # Create __init__.py
    with open(os.path.join(project_path, "__init__.py"), "w") as f:
        f.write("")
    
    # Create models directory
    models_path = os.path.join(project_path, "models")
    os.makedirs(models_path)
    with open(os.path.join(models_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(models_path, "user.py"), "w") as f:
        f.write("class User:\n    pass\n")
    
    # Create controllers directory
    controllers_path = os.path.join(project_path, "controllers")
    os.makedirs(controllers_path)
    with open(os.path.join(controllers_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(controllers_path, "users_controller.py"), "w") as f:
        f.write("class UsersController:\n    pass\n")
    
    # Create services directory
    services_path = os.path.join(project_path, "services")
    os.makedirs(services_path)
    with open(os.path.join(services_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(services_path, "user_service.py"), "w") as f:
        f.write("class UserService:\n    pass\n")
    
    # Create nested auth directory
    auth_path = os.path.join(services_path, "auth")
    os.makedirs(auth_path)
    with open(os.path.join(auth_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(auth_path, "authentication_service.py"), "w") as f:
        f.write("class AuthenticationService:\n    pass\n")
    
    return project_path

```

## File: tests/test_autoloader.py
```py
"""
Tests for the AutoLoader class.
"""
import os
import sys
import pytest

from pyautoload import AutoLoader


class TestAutoLoader:
    """Test suite for the AutoLoader class."""

    def test_autoloader_initialization(self):
        """Test that the autoloader can be initialized with valid parameters."""
        loader = AutoLoader(base_path="dummy", top_level="dummy")
        assert loader is not None
        assert loader.base_path == "dummy"
        assert loader.top_level == "dummy"

    def test_autoloader_validate_parameters(self):
        """Test that the autoloader validates its parameters."""
        with pytest.raises(ValueError):
            AutoLoader(base_path=None, top_level="dummy")
        
        with pytest.raises(ValueError):
            AutoLoader(base_path="dummy", top_level=None)

    def test_discovery(self, sample_project):
        """Test that the autoloader can discover modules."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        loader = AutoLoader(base_path=sample_project, top_level="sample_app")
        loader.discover()
        
        # Check that modules were properly discovered
        import sample_app.models.user
        import sample_app.controllers.users_controller
        import sample_app.services.user_service
        import sample_app.services.auth.authentication_service
        
        assert sample_app.models.user.User
        assert sample_app.controllers.users_controller.UsersController
        assert sample_app.services.user_service.UserService
        assert sample_app.services.auth.authentication_service.AuthenticationService

    def test_eager_loading(self, sample_project):
        """Test that the autoloader can eagerly load modules."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        loader = AutoLoader(base_path=sample_project, top_level="sample_app")
        loader.eager_load()
        
        # Check that modules were properly loaded
        assert "sample_app.models.user" in sys.modules
        assert "sample_app.controllers.users_controller" in sys.modules
        assert "sample_app.services.user_service" in sys.modules
        assert "sample_app.services.auth.authentication_service" in sys.modules
        
    def test_lazy_loading(self, sample_project):
        """Test that the autoloader can lazily load modules."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        loader = AutoLoader(base_path=sample_project, top_level="sample_app")
        loader.discover()
        
        # Before importing, the modules shouldn't be loaded
        assert "sample_app.models.user" not in sys.modules
        
        # After importing, the module should be loaded
        import sample_app.models.user
        assert "sample_app.models.user" in sys.modules

```

## File: tests/test_file_watcher.py
```py
"""
Tests for the FileWatcher class.
"""
import os
import time
import pytest
from pyautoload import FileWatcher


class TestFileWatcher:
    """Test suite for the FileWatcher class."""

    def test_file_watcher_initialization(self):
        """Test that the file watcher can be initialized with valid parameters."""
        watcher = FileWatcher(dirs=["dummy"])
        assert watcher is not None
        assert watcher.dirs == ["dummy"]

    def test_file_watcher_validation(self):
        """Test that the file watcher validates its parameters."""
        with pytest.raises(ValueError):
            FileWatcher(dirs=None)
        
        with pytest.raises(ValueError):
            FileWatcher(dirs=[])

    def test_file_watcher_callback(self, temp_dir):
        """Test that the file watcher calls the callback when files change."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test_file.py")
        with open(test_file, "w") as f:
            f.write("# Test file")
        
        # Create a callback that sets a flag when called
        callback_called = False
        def callback(event):
            nonlocal callback_called
            callback_called = True
        
        # Start the watcher
        watcher = FileWatcher(dirs=[temp_dir])
        watcher.on_change(callback)
        watcher.start()
        
        try:
            # Modify the file
            time.sleep(0.1)  # Give the watcher time to start
            with open(test_file, "a") as f:
                f.write("\n# Modified")
            
            # Wait for the callback to be called
            time.sleep(0.2)
            assert callback_called, "Callback was not called when file changed"
        finally:
            watcher.stop()
            
    def test_file_watcher_filter(self, temp_dir):
        """Test that the file watcher can filter events."""
        # Skip this test until implementation is ready
        pytest.skip("Implementation not ready")
        
        # Create test files
        py_file = os.path.join(temp_dir, "test_file.py")
        with open(py_file, "w") as f:
            f.write("# Test Python file")
            
        txt_file = os.path.join(temp_dir, "test_file.txt")
        with open(txt_file, "w") as f:
            f.write("Test text file")
        
        # Create callbacks that set flags when called
        py_callback_called = False
        def py_callback(event):
            nonlocal py_callback_called
            py_callback_called = True
        
        # Start the watcher with a Python file filter
        watcher = FileWatcher(dirs=[temp_dir], patterns=["*.py"])
        watcher.on_change(py_callback)
        watcher.start()
        
        try:
            # Modify both files
            time.sleep(0.1)  # Give the watcher time to start
            
            with open(py_file, "a") as f:
                f.write("\n# Modified Python file")
            
            with open(txt_file, "a") as f:
                f.write("\nModified text file")
            
            # Wait for callbacks to be called
            time.sleep(0.2)
            assert py_callback_called, "Python callback was not called when Python file changed"
            
        finally:
            watcher.stop()

```

## File: tests/test_import_hooks.py
```py
"""
Tests for the PyAutoload import hooks.
"""
import os
import sys
import pytest
import importlib
from contextlib import contextmanager
from pyautoload import PyAutoloadFinder, PyAutoloadLoader, ModuleRegistry


@contextmanager
def isolated_meta_path():
    """Context manager that isolates sys.meta_path changes."""
    original_meta_path = sys.meta_path.copy()
    try:
        yield
    finally:
        sys.meta_path = original_meta_path


@contextmanager
def isolated_modules():
    """Context manager that preserves the state of sys.modules."""
    original_modules = sys.modules.copy()
    try:
        yield
    finally:
        # Restore only the modules that were there originally
        # to avoid affecting other tests
        for key in list(sys.modules.keys()):
            if key not in original_modules:
                del sys.modules[key]
            else:
                sys.modules[key] = original_modules[key]


class TestPyAutoloadFinder:
    """Test suite for the PyAutoloadFinder class."""
    
    def test_finder_initialization(self):
        """Test that the finder can be initialized with base paths."""
        base_paths = ["/path/to/app"]
        finder = PyAutoloadFinder(base_paths)
        
        assert finder is not None
        assert finder.base_paths == base_paths
        
    def test_find_spec_for_registered_module(self):
        """Test that find_spec returns a spec for registered modules."""
        registry = ModuleRegistry()
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        
        finder = PyAutoloadFinder([], registry=registry)
        
        # Test finding a registered module
        spec = finder.find_spec("app.models.user", None, None)
        
        assert spec is not None
        assert spec.name == "app.models.user"
        assert spec.origin == "/path/to/app/models/user.py"
        assert isinstance(spec.loader, PyAutoloadLoader)
        assert not spec.submodule_search_locations  # Not a package
        
    def test_find_spec_for_registered_package(self):
        """Test that find_spec returns a package spec for registered packages."""
        registry = ModuleRegistry()
        registry.register("app.models", "/path/to/app/models/__init__.py", is_package=True)
        
        finder = PyAutoloadFinder([], registry=registry)
        
        # Test finding a registered package
        spec = finder.find_spec("app.models", None, None)
        
        assert spec is not None
        assert spec.name == "app.models"
        assert spec.origin == "/path/to/app/models/__init__.py"
        assert isinstance(spec.loader, PyAutoloadLoader)
        assert spec.submodule_search_locations == ["/path/to/app/models"]
        
    def test_find_spec_for_unregistered_module(self):
        """Test that find_spec returns None for unregistered modules."""
        registry = ModuleRegistry()
        finder = PyAutoloadFinder([], registry=registry)
        
        # Test finding an unregistered module
        spec = finder.find_spec("unregistered.module", None, None)
        
        assert spec is None
        
    def test_integration_with_meta_path(self):
        """Test integration with sys.meta_path."""
        with isolated_meta_path():
            finder = PyAutoloadFinder([])
            
            # Check that the finder is added to sys.meta_path
            assert finder in sys.meta_path
            
            # It should be at the beginning of the list
            assert sys.meta_path[0] is finder


class TestPyAutoloadLoader:
    """Test suite for the PyAutoloadLoader class."""
    
    def test_loader_initialization(self):
        """Test that the loader can be initialized."""
        registry = ModuleRegistry()
        loader = PyAutoloadLoader("app.models.user", "/path/to/app/models/user.py", registry)
        
        assert loader is not None
        assert loader.fullname == "app.models.user"
        assert loader.filepath == "/path/to/app/models/user.py"
        
    def test_create_module(self, tmp_path):
        """Test that create_module returns None (using default module creation)."""
        registry = ModuleRegistry()
        
        # Create a test module file
        module_dir = tmp_path / "app" / "models"
        module_dir.mkdir(parents=True)
        module_path = module_dir / "user.py"
        module_path.write_text("class User:\n    pass\n")
        
        # Register the module
        registry.register("app.models.user", str(module_path), is_package=False)
        
        # Create a loader and spec
        loader = PyAutoloadLoader("app.models.user", str(module_path), registry)
        spec = importlib.machinery.ModuleSpec(
            name="app.models.user",
            loader=loader,
            origin=str(module_path),
            is_package=False
        )
        
        # Test create_module
        module = loader.create_module(spec)
        assert module is None  # Should return None to use default module creation
        
    def test_exec_module(self, tmp_path):
        """Test that exec_module executes the module code."""
        registry = ModuleRegistry()
        
        # Create a test module file
        module_dir = tmp_path / "app" / "models"
        module_dir.mkdir(parents=True)
        module_path = module_dir / "user.py"
        module_path.write_text("class User:\n    pass\n")
        
        # Register the module
        registry.register("app.models.user", str(module_path), is_package=False)
        
        # Create a loader
        loader = PyAutoloadLoader("app.models.user", str(module_path), registry)
        
        # Create a module object
        module = type(sys)("app.models.user")
        
        # Execute the module
        loader.exec_module(module)
        
        # Check that the module was executed correctly
        assert hasattr(module, "User")
        assert module.User.__name__ == "User"
        
        # Check that the registry was updated
        assert registry.is_loaded("app.models.user")
        
    def test_module_loading_updates_registry(self, tmp_path):
        """Test that loading a module updates the registry."""
        registry = ModuleRegistry()
        
        # Create a test module file
        module_dir = tmp_path / "app" / "models"
        module_dir.mkdir(parents=True)
        module_path = module_dir / "user.py"
        module_path.write_text("class User:\n    pass\n")
        
        # Register the module
        registry.register("app.models.user", str(module_path), is_package=False)
        
        # Create a loader
        loader = PyAutoloadLoader("app.models.user", str(module_path), registry)
        
        # Create a module object
        module = type(sys)("app.models.user")
        
        # Initially, the module should not be loaded in the registry
        assert not registry.is_loaded("app.models.user")
        
        # Execute the module
        loader.exec_module(module)
        
        # Now the module should be marked as loaded
        assert registry.is_loaded("app.models.user")
        
        # And the mtime should be set
        assert registry.get_mtime("app.models.user") is not None

```

## File: tests/test_inflector.py
```py
"""
Tests for the Inflector class.
"""
import pytest
from pyautoload import Inflector


class TestInflector:
    """Test suite for the Inflector class."""

    def test_camelize(self):
        """Test that the inflector can camelize strings correctly."""
        inflector = Inflector()
        
        # Test basic camelization
        assert inflector.camelize("user") == "User"
        assert inflector.camelize("users_controller") == "UsersController"
        
        # Test handling of digits
        assert inflector.camelize("point_3d_value") == "Point3dValue"
        
        # Test acronyms (defaults to simple camelization)
        assert inflector.camelize("html_parser") == "HtmlParser"
        
    def test_custom_inflections(self):
        """Test that the inflector can handle custom inflections."""
        inflector = Inflector()
        
        # Add custom inflections
        inflector.inflect({
            "html_parser": "HTMLParser",
            "csv_controller": "CSVController",
            "mysql_adapter": "MySQLAdapter"
        })
        
        # Test custom inflections
        assert inflector.camelize("html_parser") == "HTMLParser"
        assert inflector.camelize("csv_controller") == "CSVController"
        assert inflector.camelize("mysql_adapter") == "MySQLAdapter"
        
        # Test regular camelization still works
        assert inflector.camelize("users_controller") == "UsersController"

```

## File: tests/test_integration.py
```py
"""
Integration tests for PyAutoload.

These tests verify that all components work together correctly.
"""
import os
import sys
import pytest
import importlib
from contextlib import contextmanager
from pyautoload import AutoLoader


@contextmanager
def isolated_meta_path():
    """Context manager that isolates sys.meta_path changes."""
    original_meta_path = sys.meta_path.copy()
    try:
        yield
    finally:
        sys.meta_path = original_meta_path


@contextmanager
def isolated_modules():
    """Context manager that preserves the state of sys.modules."""
    original_modules = sys.modules.copy()
    try:
        yield
    finally:
        # Restore only the modules that were there originally
        # to avoid affecting other tests
        for key in list(sys.modules.keys()):
            if key not in original_modules:
                del sys.modules[key]
            else:
                sys.modules[key] = original_modules[key]


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure for testing."""
    # Create the project structure
    app_dir = tmp_path / "sample_app"
    app_dir.mkdir()
    
    # Create __init__.py
    init_py = app_dir / "__init__.py"
    init_py.write_text("# Sample app")
    
    # Create models directory and files
    models_dir = app_dir / "models"
    models_dir.mkdir()
    
    models_init = models_dir / "__init__.py"
    models_init.write_text("# Models package")
    
    user_py = models_dir / "user.py"
    user_py.write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        
    def __str__(self):
        return f"{self.name} <{self.email}>"
""")
    
    product_py = models_dir / "product.py"
    product_py.write_text("""
class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        
    def __str__(self):
        return f"{self.name} (${self.price})"
""")
    
    # Create controllers directory and files
    controllers_dir = app_dir / "controllers"
    controllers_dir.mkdir()
    
    controllers_init = controllers_dir / "__init__.py"
    controllers_init.write_text("# Controllers package")
    
    users_controller_py = controllers_dir / "users_controller.py"
    users_controller_py.write_text("""
from sample_app.models.user import User

class UsersController:
    def __init__(self):
        self.users = []
        
    def create_user(self, name, email):
        user = User(name, email)
        self.users.append(user)
        return user
        
    def get_users(self):
        return self.users
""")
    
    products_controller_py = controllers_dir / "products_controller.py"
    products_controller_py.write_text("""
from sample_app.models.product import Product

class ProductsController:
    def __init__(self):
        self.products = []
        
    def create_product(self, name, price):
        product = Product(name, price)
        self.products.append(product)
        return product
        
    def get_products(self):
        return self.products
""")
    
    return str(tmp_path)


class TestIntegration:
    """Integration tests for PyAutoload."""
    
    def test_basic_autoloading(self, sample_project):
        """Test basic autoloading of modules."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Debug: Print the registry contents
                print("Registry contents:")
                for module_name in loader.registry.get_all_modules():
                    print(f"  {module_name} -> {loader.registry.get_path(module_name)}")
                
                # Import a model
                import sample_app.models.user
                assert hasattr(sample_app.models.user, "User")
                
                # Create a user
                user = sample_app.models.user.User("Test User", "test@example.com")
                assert user.name == "Test User"
                assert user.email == "test@example.com"
                
                # Import a controller
                import sample_app.controllers.users_controller
                assert hasattr(sample_app.controllers.users_controller, "UsersController")
                
                # Create a controller
                controller = sample_app.controllers.users_controller.UsersController()
                assert hasattr(controller, "create_user")
                
                # Test controller functionality
                new_user = controller.create_user("New User", "new@example.com")
                assert new_user.name == "New User"
                assert new_user.email == "new@example.com"
                assert len(controller.get_users()) == 1
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_eager_loading(self, sample_project):
        """Test eager loading of all modules."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading and eager load
            loader.setup()
            loader.eager_load()
            
            try:
                # Debug: Print the registry contents
                print("Registry contents:")
                for module_name in loader.registry.get_all_modules():
                    print(f"  {module_name} -> {loader.registry.get_path(module_name)}")
                
                # All modules should be loaded
                assert "sample_app.models.user" in sys.modules
                assert "sample_app.models.product" in sys.modules
                assert "sample_app.controllers.users_controller" in sys.modules
                assert "sample_app.controllers.products_controller" in sys.modules
                
                # Verify functionality
                user_class = sys.modules["sample_app.models.user"].User
                product_class = sys.modules["sample_app.models.product"].Product
                
                assert user_class.__name__ == "User"
                assert product_class.__name__ == "Product"
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_module_reloading(self, sample_project):
        """Test reloading of modules when files change."""
        with isolated_meta_path(), isolated_modules():
            # Initialize autoloader
            loader = AutoLoader(
                base_path=os.path.join(sample_project, "sample_app"),
                top_level="sample_app"
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Debug: Print the registry contents
                print("Registry contents:")
                for module_name in loader.registry.get_all_modules():
                    print(f"  {module_name} -> {loader.registry.get_path(module_name)}")
                
                # Import a module
                import sample_app.models.user
                original_user = sample_app.models.user.User
                
                # Modify the module file
                user_path = os.path.join(sample_project, "sample_app", "models", "user.py")
                with open(user_path, "a") as f:
                    f.write("\nclass Admin(User):\n    pass\n")
                
                # Reload the module
                loader.reload_module("sample_app.models.user")
                
                # Re-import to get the updated module
                importlib.reload(sys.modules["sample_app.models.user"])
                
                # Check that the new class is available
                assert hasattr(sample_app.models.user, "Admin")
                assert issubclass(sample_app.models.user.Admin, sample_app.models.user.User)
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()
    
    def test_multiple_root_paths(self, tmp_path):
        """Test autoloading with multiple root paths."""
        with isolated_meta_path(), isolated_modules():
            # Create two separate app directories
            app1_dir = tmp_path / "app1"
            app1_dir.mkdir()
            (app1_dir / "__init__.py").write_text("# App 1")
            (app1_dir / "module1.py").write_text("class Module1:\n    pass")
            
            app2_dir = tmp_path / "app2"
            app2_dir.mkdir()
            (app2_dir / "__init__.py").write_text("# App 2")
            (app2_dir / "module2.py").write_text("class Module2:\n    pass")
            
            # Initialize autoloader with both roots
            loader = AutoLoader(
                root_paths=[str(app1_dir), str(app2_dir)]
            )
            
            # Set up autoloading
            loader.setup()
            
            try:
                # Debug: Print the registry contents
                print("Registry contents:")
                for module_name in loader.registry.get_all_modules():
                    print(f"  {module_name} -> {loader.registry.get_path(module_name)}")
                
                # Import modules from both apps
                import app1.module1
                import app2.module2
                
                assert hasattr(app1.module1, "Module1")
                assert hasattr(app2.module2, "Module2")
            finally:
                # Clean up
                if loader.watcher:
                    loader.watcher.stop()

```

## File: tests/test_module_registry.py
```py
"""
Tests for the ModuleRegistry class.
"""
import os
import pytest
from pyautoload import ModuleRegistry


class TestModuleRegistry:
    """Test suite for the ModuleRegistry class."""
    
    def test_registry_initialization(self):
        """Test that the registry can be initialized."""
        registry = ModuleRegistry()
        assert registry is not None
        assert len(registry.get_all_modules()) == 0
    
    def test_module_registration(self):
        """Test registering modules in the registry."""
        registry = ModuleRegistry()
        
        # Register a module
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        
        # Check it was registered
        assert "app.models.user" in registry.get_all_modules()
        assert registry.get_path("app.models.user") == "/path/to/app/models/user.py"
        assert not registry.is_package("app.models.user")
        
    def test_package_registration(self):
        """Test registering packages in the registry."""
        registry = ModuleRegistry()
        
        # Register a package
        registry.register("app.models", "/path/to/app/models/__init__.py", is_package=True)
        
        # Check it was registered
        assert "app.models" in registry.get_all_modules()
        assert registry.get_path("app.models") == "/path/to/app/models/__init__.py"
        assert registry.is_package("app.models")
    
    def test_module_lookup(self):
        """Test looking up modules in the registry."""
        registry = ModuleRegistry()
        
        # Register modules
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        registry.register("app.controllers.users_controller", "/path/to/app/controllers/users_controller.py", is_package=False)
        
        # Test contains method
        assert registry.contains("app.models.user")
        assert registry.contains("app.controllers.users_controller")
        assert not registry.contains("app.services.auth")
        
        # Test get_path method
        assert registry.get_path("app.models.user") == "/path/to/app/models/user.py"
        
        # Test handling of non-existent modules
        with pytest.raises(KeyError):
            registry.get_path("non_existent_module")
    
    def test_module_loading_status(self):
        """Test tracking module loading status."""
        registry = ModuleRegistry()
        
        # Register a module
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        
        # Initially, it should not be loaded
        assert not registry.is_loaded("app.models.user")
        
        # Mark it as loaded
        registry.mark_loaded("app.models.user", 1234567890.0)  # Example modification time
        
        # Now it should be loaded
        assert registry.is_loaded("app.models.user")
        assert registry.get_mtime("app.models.user") == 1234567890.0
        
        # Mark it as unloaded
        registry.mark_unloaded("app.models.user")
        
        # Now it should not be loaded again
        assert not registry.is_loaded("app.models.user")
    
    def test_dependency_tracking(self):
        """Test tracking dependencies between modules."""
        registry = ModuleRegistry()
        
        # Register modules
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        registry.register("app.controllers.users_controller", "/path/to/app/controllers/users_controller.py", is_package=False)
        
        # Add dependency: users_controller depends on user
        registry.add_dependency("app.controllers.users_controller", "app.models.user")
        
        # Check dependencies
        assert "app.models.user" in registry.get_dependencies("app.controllers.users_controller")
        
        # Check dependents (reverse dependencies)
        assert "app.controllers.users_controller" in registry.get_dependents("app.models.user")
        
    def test_module_unregistration(self):
        """Test removing modules from the registry."""
        registry = ModuleRegistry()
        
        # Register modules
        registry.register("app.models.user", "/path/to/app/models/user.py", is_package=False)
        registry.register("app.models.product", "/path/to/app/models/product.py", is_package=False)
        
        # Unregister one module
        registry.unregister("app.models.user")
        
        # Check it was removed
        assert not registry.contains("app.models.user")
        assert registry.contains("app.models.product")  # This one should still be there

```

## File: README.md
```md
# PyAutoload

A Python autoloading library inspired by Ruby's Zeitwerk, designed to simplify module importing through convention over configuration.

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

PyAutoload is currently in early development. We're following a test-driven development approach to ensure reliability and correctness.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by [Zeitwerk](https://github.com/fxn/zeitwerk) for Ruby
- Built with love for the Python community

```

## File: setup.py
```py
from setuptools import setup, find_packages

setup(
    name='PyAutoload',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=['watchdog>=3.0.0'],
    author='David Teren',
    author_email='example@example.com',
    description='A Python autoloading library inspired by Zeitwerk.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/user/pyautoload',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.6',
    keywords='autoloading, module, import, zeitwerk',
)

```

## File: TASK.md
```md
My vision for this project "Power Auto-Load" is an attempt to explore the feasibility of providing the Python 
ecosystem with a Zeitwerk type auto-loader. It's really difficult to navigate and carry the cognitive overhead of 
imports and resolving requirements when working in Python, as opposed to modern Ruby and Rails.

I think the first approach should be to look at the provided PRD requirements and tasks, but also do a deep analysis 
and document this of the Zydeback repo at this path /Users/davidteren/Projects/OSS/zeitwerk and to strongly follow 
the Test Driven Development approach so in the PyAutoload implementation first create the tests that replicate the 
features we want in Python and skip them, then take an approach by unskipping and implementing so that we are 
ensuring that nothing breaks as we progress.



@PRD.md#L1-38 @requirements.md#L1-12 @tasks.md#L1-28 
```

## File: requirements-dev.txt
```txt
pytest>=7.0.0
pytest-cov>=4.0.0
flake8>=6.0.0
sphinx>=7.0.0
watchdog>=3.0.0
black>=23.0.0

```

