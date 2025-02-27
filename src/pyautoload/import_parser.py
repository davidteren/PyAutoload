"""
Import parser for PyAutoload.

This module provides utilities for parsing Python files to extract import statements.
"""
import ast
import sys


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts import statements from Python code."""
    
    def __init__(self):
        """Initialize an empty visitor."""
        self.imports = set()
        
    def visit_Import(self, node):
        """
        Visit an import statement like 'import x.y'.
        
        Args:
            node: The AST node representing the import statement
        """
        for name in node.names:
            self.imports.add(name.name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """
        Visit a from-import statement like 'from x.y import z'.
        
        Args:
            node: The AST node representing the from-import statement
        """
        if node.level > 0:
            # This is a relative import
            return
            
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)


def get_imports_from_code(code, filename='<unknown>'):
    """
    Parse Python code to extract import statements.
    
    Args:
        code (str): Python code to parse
        filename (str, optional): Filename for error reporting
        
    Returns:
        set: Set of imported module names
    """
    try:
        tree = ast.parse(code, filename=filename)
        visitor = ImportVisitor()
        visitor.visit(tree)
        return visitor.imports
    except SyntaxError:
        # Ignore syntax errors in incomplete or invalid Python code
        return set()


def get_imports_from_file(filepath):
    """
    Parse a Python file to extract import statements.
    
    Args:
        filepath (str): Path to the Python file
        
    Returns:
        set: Set of imported module names
    """
    try:
        with open(filepath, 'rb') as f:
            source = f.read()
        return get_imports_from_code(source, filename=filepath)
    except (IOError, OSError):
        # Ignore I/O errors (e.g., file not found, permission denied)
        return set()


def calculate_dependencies(module_name, imported_modules, registry):
    """
    Calculate actual dependencies within the registry based on imported modules.
    
    Args:
        module_name (str): Name of the module being processed
        imported_modules (set): Set of imports extracted from the module
        registry (ModuleRegistry): Registry object to check registered modules
        
    Returns:
        set: Set of dependency module names that are in the registry
    """
    dependencies = set()
    
    # For each imported module, check if it's in our registry
    for imported in imported_modules:
        # Direct match
        if registry.contains(imported):
            dependencies.add(imported)
            continue
            
        # Check if the imported module is a parent of any registered module
        for registered in registry.get_all_modules():
            if registered.startswith(imported + '.'):
                dependencies.add(imported)
                break
                
        # Check if the imported module is a child of any registered module
        parts = imported.split('.')
        for i in range(1, len(parts)):
            prefix = '.'.join(parts[:i])
            if registry.contains(prefix):
                dependencies.add(prefix)
    
    # Always add parent package as a dependency
    parts = module_name.split('.')
    if len(parts) > 1:
        parent = '.'.join(parts[:-1])
        if registry.contains(parent):
            dependencies.add(parent)
    
    return dependencies
