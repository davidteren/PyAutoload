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
    
    def register(self, module_name, filepath, is_package=False, is_namespace_package=False):
        """
        Register a module in the registry.
        
        Args:
            module_name (str): Full name of the module (e.g., "app.models.user")
            filepath (str): Absolute path to the module's file
            is_package (bool): Whether this module is a package
            is_namespace_package (bool): Whether this is a PEP 420 namespace package
        """
        with self._lock:
            self._modules[module_name] = {
                'path': filepath,
                'is_package': is_package,
                'is_namespace_package': is_namespace_package,
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
    
    def is_namespace_package(self, module_name):
        """
        Check if a module is a PEP 420 namespace package.
        
        Args:
            module_name (str): Full name of the module
            
        Returns:
            bool: True if the module is a namespace package, False otherwise
            
        Raises:
            KeyError: If the module is not registered
        """
        with self._lock:
            if module_name not in self._modules:
                raise KeyError(f"Module '{module_name}' is not registered")
            return self._modules[module_name].get('is_namespace_package', False)
    
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
