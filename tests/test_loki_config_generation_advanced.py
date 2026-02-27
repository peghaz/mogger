"""
Tests for Loki configuration file generation edge cases and validation.
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from mogger import Mogger


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def cleanup_generated_configs(tmp_path):
    """Clean up any generated config directories after tests."""
    yield tmp_path
    # Cleanup runs after test
    for item in tmp_path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)


class TestLokiConfigGeneratorValidation:
    """Tests for validation and error handling in config generation."""

    def test_generate_config_with_path_object(self, test_config_path, tmp_path):
        """Test generation accepts Path object."""
        mogger = Mogger(test_config_path)
        
        dest = tmp_path / "loki-setup"
        config_path = mogger.generate_loki_config(destination=dest)
        
        assert config_path.exists()
        assert config_path == dest

    def test_generate_config_with_string_path(self, test_config_path, tmp_path):
        """Test generation accepts string path."""
        mogger = Mogger(test_config_path)
        
        dest = str(tmp_path / "loki-setup")
        config_path = mogger.generate_loki_config(destination=dest)
        
        assert config_path.exists()
        assert isinstance(config_path, Path)

    def test_generate_config_creates_nested_dirs(self, test_config_path, tmp_path):
        """Test that deeply nested parent directories are created."""
        mogger = Mogger(test_config_path)
        
        dest = tmp_path / "level1" / "level2" / "level3" / "loki-config"
        config_path = mogger.generate_loki_config(destination=dest)
        
        assert config_path.exists()
        assert (config_path / "docker-compose.yaml").exists()

    def test_generate_config_fails_on_existing_directory(self, test_config_path, tmp_path):
        """Test that generation fails if destination exists."""
        mogger = Mogger(test_config_path)
        
        dest = tmp_path / "loki-config"
        
        # Create first time
        config_path = mogger.generate_loki_config(destination=dest)
        assert config_path.exists()
        
        # Try again - should raise FileExistsError
        with pytest.raises(FileExistsError) as exc_info:
            mogger.generate_loki_config(destination=dest)
        
        assert "already exists" in str(exc_info.value)

    def test_generate_config_fails_on_existing_file(self, test_config_path, tmp_path):
        """Test that generation fails if destination is an existing file."""
        mogger = Mogger(test_config_path)
        
        # Create a file at destination
        dest = tmp_path / "loki-config"
        dest.touch()
        
        # Should fail
        with pytest.raises(FileExistsError):
            mogger.generate_loki_config(destination=dest)


class TestLokiConfigGeneratorContent:
    """Tests for content of generated configuration."""

    def test_generated_config_has_docker_compose(self, test_config_path, tmp_path):
        """Test that docker-compose.yaml is generated."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        docker_compose = config_path / "docker-compose.yaml"
        
        assert docker_compose.exists()
        assert docker_compose.is_file()
        
        # Check file is not empty
        assert docker_compose.stat().st_size > 0

    def test_generated_config_has_env_example(self, test_config_path, tmp_path):
        """Test that .env.example is generated."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        env_example = config_path / ".env.example"
        
        assert env_example.exists()
        assert env_example.is_file()

    def test_generated_config_has_loki_directory(self, test_config_path, tmp_path):
        """Test that loki subdirectory is created."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        loki_dir = config_path / "loki"
        
        assert loki_dir.exists()
        assert loki_dir.is_dir()

    def test_generated_config_has_alloy_directory(self, test_config_path, tmp_path):
        """Test that alloy subdirectory is created."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        alloy_dir = config_path / "alloy"
        
        assert alloy_dir.exists()
        assert alloy_dir.is_dir()

    def test_generated_loki_config_file(self, test_config_path, tmp_path):
        """Test that loki.yaml exists in loki directory."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        loki_yaml = config_path / "loki" / "loki.yaml"
        
        assert loki_yaml.exists()
        assert loki_yaml.is_file()
        assert loki_yaml.stat().st_size > 0

    def test_generated_alloy_config_file(self, test_config_path, tmp_path):
        """Test that config.alloy exists in alloy directory."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        alloy_config = config_path / "alloy" / "config.alloy"
        
        assert alloy_config.exists()
        assert alloy_config.is_file()
        assert alloy_config.stat().st_size > 0

    def test_generated_files_are_readable(self, test_config_path, tmp_path):
        """Test that all generated files are readable."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        # Try to read each file
        docker_compose = config_path / "docker-compose.yaml"
        with open(docker_compose, 'r') as f:
            content = f.read()
            assert len(content) > 0
            assert "version" in content or "services" in content


class TestLokiConfigGeneratorMultipleCalls:
    """Tests for multiple config generation scenarios."""

    def test_generate_multiple_configs_different_locations(self, test_config_path, tmp_path):
        """Test generating configs at different locations."""
        mogger = Mogger(test_config_path)
        
        config1 = mogger.generate_loki_config(destination=tmp_path / "config1")
        config2 = mogger.generate_loki_config(destination=tmp_path / "config2")
        config3 = mogger.generate_loki_config(destination=tmp_path / "config3")
        
        assert config1.exists()
        assert config2.exists()
        assert config3.exists()
        
        assert config1 != config2 != config3

    def test_generate_config_after_mogger_log(self, test_config_path, tmp_path):
        """Test config generation after logging operations."""
        mogger = Mogger(test_config_path)
        
        # Log some messages first
        mogger.info("Test message 1", category="user_actions", user_id="user1", action="test")
        mogger.info("Test message 2", category="user_actions", user_id="user2", action="test")
        
        # Then generate config
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert config_path.exists()


class TestLokiConfigGeneratorWithoutCSV:
    """Tests for config generation when CSV logging is disabled."""

    def test_generate_config_with_disabled_csv(self, test_config_path, tmp_path):
        """Test config generation works with log_to_csv=False."""
        mogger = Mogger(test_config_path, log_to_csv=False)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert config_path.exists()
        assert (config_path / "docker-compose.yaml").exists()

    def test_generate_config_multiple_times_no_csv(self, test_config_path, tmp_path):
        """Test multiple config generations with disabled CSV logging."""
        mogger = Mogger(test_config_path, log_to_csv=False)
        
        config1 = mogger.generate_loki_config(destination=tmp_path / "config1")
        config2 = mogger.generate_loki_config(destination=tmp_path / "config2")
        
        assert config1.exists()
        assert config2.exists()


class TestLokiConfigGeneratorReturnValue:
    """Tests for return value of generate_loki_config."""

    def test_returns_path_object(self, test_config_path, tmp_path):
        """Test that method returns a Path object."""
        mogger = Mogger(test_config_path)
        
        result = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert isinstance(result, Path)

    def test_returned_path_is_absolute(self, test_config_path, tmp_path):
        """Test that returned path is absolute."""
        mogger = Mogger(test_config_path)
        
        result = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert result.is_absolute()

    def test_returned_path_equals_destination(self, test_config_path, tmp_path):
        """Test that returned path matches provided destination."""
        mogger = Mogger(test_config_path)
        
        dest = tmp_path / "my-loki-config"
        result = mogger.generate_loki_config(destination=dest)
        
        assert result == dest


class TestLokiConfigGeneratorPermissions:
    """Tests for file and directory permissions."""

    def test_generated_directories_are_accessible(self, test_config_path, tmp_path):
        """Test that generated directories have appropriate permissions."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        # Check we can list directories
        items = list(config_path.iterdir())
        assert len(items) > 0
        
        # Check subdirectories are accessible
        loki_dir = config_path / "loki"
        loki_items = list(loki_dir.iterdir())
        assert len(loki_items) > 0

    def test_generated_files_are_writable(self, test_config_path, tmp_path):
        """Test that generated files can be modified."""
        mogger = Mogger(test_config_path)
        
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        # Try to append to docker-compose.yaml
        docker_compose = config_path / "docker-compose.yaml"
        with open(docker_compose, 'a') as f:
            f.write("\n# Test comment\n")
        
        # Verify it was written
        with open(docker_compose, 'r') as f:
            content = f.read()
            assert "# Test comment" in content


class TestLokiConfigGeneratorEdgeCases:
    """Tests for edge cases in config generation."""

    def test_generate_config_with_relative_path(self, test_config_path, tmp_path):
        """Test config generation with relative path."""
        mogger = Mogger(test_config_path)
        
        # Use relative path - but it will be converted to absolute by Path
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config_path = mogger.generate_loki_config(destination="loki-config")
            
            assert config_path.exists()
            # Path will be made absolute by generate_loki_config
            assert str(config_path).endswith("loki-config")
        finally:
            os.chdir(original_cwd)

    def test_generate_config_with_special_characters_in_path(self, test_config_path, tmp_path):
        """Test config generation with special characters in path name."""
        mogger = Mogger(test_config_path)
        
        dest = tmp_path / "loki-config_v1.0-test"
        config_path = mogger.generate_loki_config(destination=dest)
        
        assert config_path.exists()
        assert config_path.name == "loki-config_v1.0-test"

    def test_generate_config_preserves_symlinks(self, test_config_path, tmp_path):
        """Test that config generation handles source with symlinks correctly."""
        mogger = Mogger(test_config_path)
        
        # Generate config - should work even if source has symlinks
        config_path = mogger.generate_loki_config(destination=tmp_path / "loki-config")
        
        assert config_path.exists()
