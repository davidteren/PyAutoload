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
