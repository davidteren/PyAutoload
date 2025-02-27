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
from .import_hooks import PyAutoloadFinder, PyAutoloadLoader, AutoloadError, CircularDependencyError


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
            
        # Get all modules that need to be reloaded using a topological sort
        modules_to_reload = self._get_dependent_modules_in_order(module_name)
        
        # Unload all modules in reverse dependency order
        for mod_name in reversed(modules_to_reload):
            if mod_name in sys.modules:
                # Remove from sys.modules
                del sys.modules[mod_name]
                # Mark as unloaded in registry
                self.registry.mark_unloaded(mod_name)
        
        # Reload the modules in correct dependency order
        for mod_name in modules_to_reload:
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                print(f"Error reloading module {mod_name}: {e}")
    
    def _get_dependent_modules_in_order(self, module_name):
        """
        Get a list of modules that depend on the given module, in topologically sorted order.
        
        Args:
            module_name (str): Name of the module to check
            
        Returns:
            list: Ordered list of modules to reload
        """
        visited = set()
        modules_in_order = []
        
        def visit(name):
            if name in visited:
                return
            visited.add(name)
            for dependent in self.registry.get_dependents(name):
                visit(dependent)
            modules_in_order.append(name)
            
        # Start with the specified module
        visit(module_name)
        
        return modules_in_order
    
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
