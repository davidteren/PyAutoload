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
