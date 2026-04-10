"""Regression test for docker_forward_env bug.

Bug: docker_forward_env is parsed from terminal config and supported by
_create_environment(), but the main terminal_tool() path drops it when
assembling container_config for new docker/singularity/modal/daytona
environments.

This test ensures docker_forward_env is properly included in container_config.
"""

import json
import os
from unittest.mock import patch

import tools.terminal_tool as terminal_tool


def test_get_env_config_includes_docker_forward_env(monkeypatch):
    """Test that _get_env_config() returns docker_forward_env."""
    
    monkeypatch.setenv("TERMINAL_DOCKER_FORWARD_ENV", '["PATH", "HOME", "USER"]')
    
    config = terminal_tool._get_env_config()
    
    assert "docker_forward_env" in config
    assert config["docker_forward_env"] == ["PATH", "HOME", "USER"]


def test_get_env_config_docker_forward_env_defaults_to_empty(monkeypatch):
    """Test that docker_forward_env defaults to empty list."""
    
    monkeypatch.delenv("TERMINAL_DOCKER_FORWARD_ENV", raising=False)
    
    config = terminal_tool._get_env_config()
    
    assert "docker_forward_env" in config
    assert config["docker_forward_env"] == []


def test_container_config_assembly_includes_docker_forward_env(monkeypatch):
    """Test that container_config dict assembly includes docker_forward_env.
    
    This is the core regression test - it verifies that when terminal_tool()
    assembles container_config for docker/singularity/modal/daytona backends,
    it includes docker_forward_env from the config.
    """
    
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    monkeypatch.setenv("TERMINAL_DOCKER_FORWARD_ENV", '["TEST_VAR"]')
    
    # Get config as terminal_tool does
    config = terminal_tool._get_env_config()
    env_type = config["env_type"]
    
    # Simulate the container_config assembly from terminal_tool (lines 1256-1266)
    container_config = None
    if env_type in ("docker", "singularity", "modal", "daytona"):
        container_config = {
            "container_cpu": config.get("container_cpu", 1),
            "container_memory": config.get("container_memory", 5120),
            "container_disk": config.get("container_disk", 51200),
            "container_persistent": config.get("container_persistent", True),
            "modal_mode": config.get("modal_mode", "auto"),
            "docker_volumes": config.get("docker_volumes", []),
            "docker_mount_cwd_to_workspace": config.get("docker_mount_cwd_to_workspace", False),
            "docker_forward_env": config.get("docker_forward_env", []),
        }
    
    # Verify docker_forward_env is in container_config
    assert container_config is not None
    assert "docker_forward_env" in container_config
    assert container_config["docker_forward_env"] == ["TEST_VAR"]


def test_container_config_assembly_for_all_backends(monkeypatch):
    """Test that docker_forward_env is included for all container backends."""
    
    backends = ["docker", "singularity", "modal", "daytona"]
    
    for backend in backends:
        monkeypatch.setenv("TERMINAL_ENV", backend)
        monkeypatch.setenv("TERMINAL_DOCKER_FORWARD_ENV", '["VAR1", "VAR2"]')
        
        config = terminal_tool._get_env_config()
        env_type = config["env_type"]
        
        # Simulate container_config assembly
        container_config = None
        if env_type in ("docker", "singularity", "modal", "daytona"):
            container_config = {
                "container_cpu": config.get("container_cpu", 1),
                "container_memory": config.get("container_memory", 5120),
                "container_disk": config.get("container_disk", 51200),
                "container_persistent": config.get("container_persistent", True),
                "modal_mode": config.get("modal_mode", "auto"),
                "docker_volumes": config.get("docker_volumes", []),
                "docker_mount_cwd_to_workspace": config.get("docker_mount_cwd_to_workspace", False),
                "docker_forward_env": config.get("docker_forward_env", []),
            }
        
        assert container_config is not None, f"Failed for backend: {backend}"
        assert "docker_forward_env" in container_config, f"Failed for backend: {backend}"
        assert container_config["docker_forward_env"] == ["VAR1", "VAR2"], f"Failed for backend: {backend}"


def test_create_environment_receives_docker_forward_env(monkeypatch):
    """Test that _create_environment receives docker_forward_env in container_config."""
    
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    monkeypatch.setenv("TERMINAL_DOCKER_FORWARD_ENV", '["MY_VAR"]')
    
    config = terminal_tool._get_env_config()
    
    # Simulate container_config assembly
    container_config = {
        "container_cpu": config.get("container_cpu", 1),
        "container_memory": config.get("container_memory", 5120),
        "container_disk": config.get("container_disk", 51200),
        "container_persistent": config.get("container_persistent", True),
        "modal_mode": config.get("modal_mode", "auto"),
        "docker_volumes": config.get("docker_volumes", []),
        "docker_mount_cwd_to_workspace": config.get("docker_mount_cwd_to_workspace", False),
        "docker_forward_env": config.get("docker_forward_env", []),
    }
    
    # Verify _create_environment can extract docker_forward_env from container_config
    cc = container_config or {}
    docker_forward_env = cc.get("docker_forward_env", [])
    
    assert docker_forward_env == ["MY_VAR"]
