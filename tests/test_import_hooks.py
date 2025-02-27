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
