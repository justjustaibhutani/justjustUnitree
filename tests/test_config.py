"""Tests for Config loading."""

import os
import tempfile
import pytest
from jjai_go2.config import Config


def test_defaults():
    config = Config()
    assert config.robot_id == "go2"
    assert config.dashboard_port == 5003


def test_load_from_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("robot_id: testbot\ndashboard_port: 9999\n")
        f.flush()
        config = Config.load(yaml_path=f.name)

    assert config.robot_id == "testbot"
    assert config.dashboard_port == 9999
    os.unlink(f.name)


def test_env_overrides_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("robot_id: from_yaml\n")
        f.flush()

        os.environ["ROBOT_ID"] = "from_env"
        try:
            config = Config.load(yaml_path=f.name)
            assert config.robot_id == "from_env"
        finally:
            del os.environ["ROBOT_ID"]
            os.unlink(f.name)


def test_load_env_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write('export ROBOT_ID="envfile_bot"\n')
        f.write("DASHBOARD_PORT=7777\n")
        f.flush()

        config = Config.load(env_file=f.name)

    assert config.robot_id == "envfile_bot"
    assert config.dashboard_port == 7777
    os.unlink(f.name)
    # Clean up env
    os.environ.pop("ROBOT_ID", None)
    os.environ.pop("DASHBOARD_PORT", None)


def test_missing_yaml():
    config = Config.load(yaml_path="/nonexistent.yaml")
    assert config.robot_id == "go2"  # Falls back to defaults
