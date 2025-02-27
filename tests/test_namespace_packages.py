"""
Tests for namespace package support in PyAutoload.

This module tests the support for PEP 420 namespace packages, which are
directories without __init__.py files that still act as packages.
"""
import os
import sys
import pytest
import importlib

from pyautoload import AutoLoader
from pyautoload.file_scanner import FileScanner
from pyautoload.module_registry import ModuleRegistry
from pyautoload.inflector import Inflector
from pyautoload.import_hooks import PyAutoloadFinder, PyAutoloadLoader


@pytest.fixture
def namespace_project(temp_dir):
    """
    Create a sample project structure with namespace packages for testing.
    
    Directory structure:
    /namespace_app
      /models  # No __init__.py (namespace package)
        /user.py
      /controllers  # No __init__.py (namespace package)
        /users_controller.py
      /services  # With __init__.py (regular package)
        /__init__.py
        /user_service.py
    """
    project_path = os.path.join(temp_dir, "namespace_app")
    os.makedirs(project_path)
    
    # Create models directory without __init__.py (namespace package)
    models_path = os.path.join(project_path, "models")
    os.makedirs(models_path)
    with open(os.path.join(models_path, "user.py"), "w") as f:
        f.write("class User:\n    pass\n")
    
    # Create controllers directory without __init__.py (namespace package)
    controllers_path = os.path.join(project_path, "controllers")
    os.makedirs(controllers_path)
    with open(os.path.join(controllers_path, "users_controller.py"), "w") as f:
        f.write("class UsersController:\n    pass\n")
    
    # Create services directory with __init__.py (regular package)
    services_path = os.path.join(project_path, "services")
    os.makedirs(services_path)
    with open(os.path.join(services_path, "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(services_path, "user_service.py"), "w") as f:
        f.write("class UserService:\n    pass\n")
    
    return project_path


@pytest.fixture
def clear_sys_modules():
    """Clear relevant modules from sys.modules after each test."""
    to_delete = []
    for mod in list(sys.modules.keys()):
        if mod.startswith('namespace_app'):
            to_delete.append(mod)
    
    for mod in to_delete:
        if mod in sys.modules:
            del sys.modules[mod]
            
    yield
    
    # Clean up again after the test
    for mod in list(sys.modules.keys()):
        if mod.startswith('namespace_app'):
            del sys.modules[mod]


@pytest.fixture
def namespace_autoloader(namespace_project, clear_sys_modules):
    """Create an autoloader for the namespace project."""
    # Register the top-level namespace
    module_registry = ModuleRegistry()
    scanner = FileScanner([namespace_project], module_registry, Inflector())
    scanner.scan()
    
    # Set up the finder
    finder = PyAutoloadFinder([namespace_project], registry=module_registry)
    
    # Create and return the autoloader
    loader = AutoLoader(base_path=namespace_project)
    loader.registry = module_registry
    
    return loader


def test_namespace_package_detection(namespace_project):
    """Test that namespace packages are properly detected."""
    registry = ModuleRegistry()
    scanner = FileScanner([namespace_project], registry, Inflector())
    scanner.scan()
    
    # Verify both namespace packages and regular packages are detected
    assert registry.contains('namespace_app.models')
    assert registry.contains('namespace_app.controllers')
    assert registry.contains('namespace_app.services')
    
    # Verify modules in namespace packages are detected
    assert registry.contains('namespace_app.models.user')
    assert registry.contains('namespace_app.controllers.users_controller')
    assert registry.contains('namespace_app.services.user_service')
    
    # Verify namespace packages are marked correctly
    assert registry.is_package('namespace_app.models')
    assert registry.is_namespace_package('namespace_app.models')
    assert registry.is_package('namespace_app.controllers')
    assert registry.is_namespace_package('namespace_app.controllers')
    
    # Verify regular packages are marked correctly
    assert registry.is_package('namespace_app.services')
    assert not registry.is_namespace_package('namespace_app.services')


def test_namespace_package_importing(namespace_autoloader):
    """Test that modules in namespace packages can be imported."""
    # Import modules from different package types
    import namespace_app.models.user
    import namespace_app.controllers.users_controller
    import namespace_app.services.user_service
    
    # Verify classes are defined correctly
    assert hasattr(namespace_app.models.user, 'User')
    assert hasattr(namespace_app.controllers.users_controller, 'UsersController')
    assert hasattr(namespace_app.services.user_service, 'UserService')


def test_finder_with_namespace_packages(namespace_project):
    """Test that PyAutoloadFinder properly handles namespace packages."""
    registry = ModuleRegistry()
    scanner = FileScanner([namespace_project], registry, Inflector())
    scanner.scan()
    
    finder = PyAutoloadFinder([namespace_project], registry=registry)
    
    # Test finding namespace package
    spec = finder.find_spec('namespace_app.models', None, None)
    assert spec is not None
    assert spec.loader is None  # Namespace packages have no loader
    assert spec.submodule_search_locations is not None
    
    # Test finding module in namespace package
    spec = finder.find_spec('namespace_app.models.user', None, None)
    assert spec is not None
    assert spec.loader is not None
    
    # Test finding regular package
    spec = finder.find_spec('namespace_app.services', None, None)
    assert spec is not None
    assert spec.loader is not None
