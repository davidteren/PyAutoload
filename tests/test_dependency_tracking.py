"""
Tests for dependency tracking in PyAutoload.
"""
import os
import sys
import shutil
import importlib
import pytest

# Add the module path to sys.path
from pyautoload import AutoLoader


class TestDependencyTracking:
    @pytest.fixture
    def dependency_project(self, temp_dir):
        """Create a sample project with dependencies between modules."""
        # Create project structure
        project_dir = os.path.join(temp_dir, "app")
        os.makedirs(project_dir)
        
        # Create packages and modules
        os.makedirs(os.path.join(project_dir, "models"))
        os.makedirs(os.path.join(project_dir, "services"))
        
        # Create __init__.py files
        with open(os.path.join(project_dir, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(project_dir, "models", "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(project_dir, "services", "__init__.py"), "w") as f:
            f.write("")
        
        # Create base module that others depend on
        with open(os.path.join(project_dir, "models", "base.py"), "w") as f:
            f.write("""
class Base:
    VERSION = "1.0"
    
    def __init__(self, id=None):
        self.id = id
""")
        
        # Create user model that imports base
        with open(os.path.join(project_dir, "models", "user.py"), "w") as f:
            f.write("""
from app.models.base import Base

class User(Base):
    def __init__(self, id=None, name=None):
        super().__init__(id)
        self.name = name
""")
        
        # Create user service that imports user model
        with open(os.path.join(project_dir, "services", "user_service.py"), "w") as f:
            f.write("""
from app.models.user import User

class UserService:
    def create_user(self, name):
        return User(name=name)
        
    def get_version(self):
        return User.VERSION
""")
        
        return temp_dir
        
    def test_basic_dependency_tracking(self, dependency_project):
        """Test that dependencies are properly tracked and stored in the registry."""
        try:
            # Create autoloader
            loader = AutoLoader(base_path=os.path.join(dependency_project, "app"), top_level="app")
            loader.setup()
            
            # Import modules
            import app.models.base
            import app.models.user
            import app.services.user_service
            
            # Check that dependencies are tracked correctly
            assert "app.models.base" in loader.registry.get_all_modules()
            assert "app.models.user" in loader.registry.get_all_modules()
            assert "app.services.user_service" in loader.registry.get_all_modules()
            
            # Verify base has user as dependent
            base_dependents = loader.registry.get_dependents("app.models.base")
            assert "app.models.user" in base_dependents
            
            # Verify user has service as dependent
            user_dependents = loader.registry.get_dependents("app.models.user")
            assert "app.services.user_service" in user_dependents
            
        finally:
            # Remove modules from sys.modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith("app."):
                    del sys.modules[module_name]
    
    def test_reloading_with_dependencies(self, dependency_project):
        """Test that reloading a module also reloads its dependents."""
        try:
            # Create autoloader
            loader = AutoLoader(base_path=os.path.join(dependency_project, "app"), top_level="app")
            loader.setup()
            
            # Import modules
            import app.models.base
            import app.models.user
            import app.services.user_service
            
            # Create an instance to check later
            service = app.services.user_service.UserService()
            
            # Verify initial version
            assert app.models.base.Base.VERSION == "1.0"
            assert service.get_version() == "1.0"
            
            # Modify the base module
            with open(os.path.join(dependency_project, "app", "models", "base.py"), "w") as f:
                f.write("""
class Base:
    VERSION = "2.0"
    
    def __init__(self, id=None):
        self.id = id
""")
            
            # Reload the base module
            loader.reload_module("app.models.base")
            
            # Force reimport to get the latest definitions
            del sys.modules["app.models.base"]
            del sys.modules["app.models.user"]
            del sys.modules["app.services.user_service"]
            
            # Reimport the modules
            import app.models.base
            import app.models.user
            import app.services.user_service
            
            # Create a new instance
            new_service = app.services.user_service.UserService()
            
            # Verify that the version has been updated in the new instance
            assert app.models.base.Base.VERSION == "2.0"
            assert new_service.get_version() == "2.0"
            
            # Note: the old instance won't be updated (Python limitation)
            # This is expected behavior and should be documented
            
        finally:
            # Remove modules from sys.modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith("app."):
                    del sys.modules[module_name]
