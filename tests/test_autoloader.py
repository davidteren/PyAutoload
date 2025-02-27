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
        assert os.path.basename(loader.base_paths[0]) == "dummy"
        assert loader.top_level == "dummy"

    def test_autoloader_validate_parameters(self):
        """Test that the autoloader validates its parameters."""
        # We should validate that setup() raises ValueError when no base paths are provided
        loader = AutoLoader()
        with pytest.raises(ValueError):
            loader.setup()

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
