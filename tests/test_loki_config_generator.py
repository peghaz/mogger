"""
Tests for Loki configuration generator.
"""

import pytest
from pathlib import Path
import shutil

from mogger import Mogger


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def cleanup_loki_config():
    """Clean up loki-config directory after tests."""
    yield
    # Cleanup after test
    loki_config_dir = Path.cwd() / "loki-config"
    if loki_config_dir.exists():
        shutil.rmtree(loki_config_dir)


class TestLokiConfigGenerator:
    """Tests for generate_loki_config method."""

    def test_generate_loki_config_default_location(self, test_config_path, cleanup_loki_config):
        """Test generating Loki config in default location."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config()
        
        # Verify directory was created
        assert config_path.exists()
        assert config_path.is_dir()
        assert config_path.name == "loki-config"
        
        # Verify expected files exist
        assert (config_path / "docker-compose.yaml").exists()
        assert (config_path / ".env.example").exists()
        assert (config_path / "loki").exists()
        assert (config_path / "alloy").exists()

    def test_generate_loki_config_custom_location(self, test_config_path, tmp_path):
        """Test generating Loki config in custom location."""
        mogger = Mogger(test_config_path)
        
        custom_path = tmp_path / "my-loki-setup"
        config_path = mogger.generate_loki_config(destination=custom_path)
        
        # Verify directory was created at custom location
        assert config_path == custom_path
        assert config_path.exists()
        assert config_path.is_dir()
        
        # Verify expected files exist
        assert (config_path / "docker-compose.yaml").exists()
        assert (config_path / ".env.example").exists()

    def test_generate_loki_config_creates_parent_directories(self, test_config_path, tmp_path):
        """Test that parent directories are created if they don't exist."""
        mogger = Mogger(test_config_path)
        
        nested_path = tmp_path / "level1" / "level2" / "loki-config"
        config_path = mogger.generate_loki_config(destination=nested_path)
        
        # Verify nested directory was created
        assert config_path.exists()
        assert config_path.is_dir()
        assert (config_path / "docker-compose.yaml").exists()

    def test_generate_loki_config_fails_if_exists(self, test_config_path, tmp_path):
        """Test that method fails if destination already exists."""
        mogger = Mogger(test_config_path)
        
        # Create directory first time
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        assert config_path.exists()
        
        # Try to create again - should fail
        with pytest.raises(FileExistsError, match="Directory already exists"):
            mogger.generate_loki_config(destination=tmp_path / "loki-config")

    def test_generate_loki_config_returns_path_object(self, test_config_path, tmp_path):
        """Test that method returns a Path object."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert isinstance(config_path, Path)

    def test_generate_loki_config_accepts_string_path(self, test_config_path, tmp_path):
        """Test that method accepts string path as destination."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=str(tmp_path / "loki-config"))
        
        assert config_path.exists()
        assert (config_path / "docker-compose.yaml").exists()

    def test_generate_loki_config_preserves_file_structure(self, test_config_path, tmp_path):
        """Test that all subdirectories and files are copied correctly."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        # Check that subdirectories exist
        loki_dir = config_path / "loki"
        alloy_dir = config_path / "alloy"
        
        assert loki_dir.exists()
        assert loki_dir.is_dir()
        assert alloy_dir.exists()
        assert alloy_dir.is_dir()
        
        # Check for config files in subdirectories
        assert len(list(loki_dir.rglob("*.yaml"))) > 0 or len(list(loki_dir.rglob("*.yml"))) > 0

    def test_generate_loki_config_without_csv(self, test_config_path, tmp_path):
        """Test that config generation works even when CSV logging is disabled."""
        mogger = Mogger(test_config_path, log_to_csv=False)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert config_path.exists()
        assert (config_path / "docker-compose.yaml").exists()
