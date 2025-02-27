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
                    has_init = os.path.exists(os.path.join(path, '__init__.py'))
                    # This is a package (either regular or namespace)
                    # Register as namespace.package
                    package_name = f"{namespace}.{item}" if namespace else item
                    
                    if has_init:
                        # Regular package with __init__.py
                        init_path = os.path.join(path, '__init__.py')
                        self.registry.register(package_name, init_path, is_package=True)
                    else:
                        # Check if it should be a namespace package (has .py files or subdirectories)
                        if self._is_valid_namespace_package(path):
                            # Namespace package without __init__.py
                            self.registry.register(package_name, path, is_package=True, is_namespace_package=True)
                        else:
                            # Not a valid package or namespace package
                            continue
                    
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
                    has_init = os.path.exists(os.path.join(path, '__init__.py'))
                    
                    if has_init:
                        # This is a regular package with __init__.py
                        package_name = f"{namespace}.{item}"
                        init_path = os.path.join(path, '__init__.py')
                        self.registry.register(package_name, init_path, is_package=True)
                    else:
                        # Check if it should be a namespace package (has .py files)
                        if self._is_valid_namespace_package(path):
                            # This is a namespace package without __init__.py
                            package_name = f"{namespace}.{item}"
                            self.registry.register(package_name, path, is_package=True, is_namespace_package=True)
                        else:
                            # Not a valid package or namespace package
                            continue
                    
                    # Scan subdirectory with updated namespace
                    self._scan_package_directory(path, f"{namespace}.{item}")
                
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
    
    def _is_valid_namespace_package(self, directory):
        """
        Check if a directory should be considered a namespace package.
        
        A directory is a valid namespace package if it:
        1. Has at least one .py file inside, or
        2. Has at least one subdirectory that contains Python modules
        
        Args:
            directory (str): Directory to check
            
        Returns:
            bool: True if the directory should be a namespace package
        """
        try:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                
                if self._should_ignore(path):
                    continue
                
                # If it has Python files, it's a valid namespace package
                if item.endswith('.py'):
                    return True
                
                # If it has subdirectories with Python files, it's a valid namespace package
                if os.path.isdir(path):
                    for subitem in os.listdir(path):
                        if subitem.endswith('.py') or subitem == '__init__.py':
                            return True
            
            return False
        except (PermissionError, FileNotFoundError):
            return False
