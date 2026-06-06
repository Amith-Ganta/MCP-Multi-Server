"""Tests for the shared configuration and server registry."""

import mcp_config


def test_local_servers_are_registered():
    servers = mcp_config.build_servers()
    # The two portable, cross-platform servers must always be present.
    assert "math" in servers
    assert "expense" in servers
    for name in ("math", "expense"):
        assert servers[name]["transport"] == "stdio"
        assert servers[name]["args"]  # a script path is configured


def test_get_model_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert mcp_config.get_model() == mcp_config.DEFAULT_MODEL


def test_get_secret_prefers_environment(monkeypatch):
    monkeypatch.setenv("SOME_TOKEN", "from-env")
    assert mcp_config.get_secret("SOME_TOKEN") == "from-env"
    assert mcp_config.get_secret("DEFINITELY_MISSING", "fallback") == "fallback"
