"""Pydantic settings — single source of truth for all configuration."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All configuration from .env / environment variables."""

    # --- LLM ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key (free tier)")
    agent_model: str = Field(default="gemini-2.5-flash", description="Model name for the agent")
    agent_max_iterations: int = Field(default=15, description="Max agent loop iterations")

    # --- GitHub ---
    github_token: str = Field(default="", description="GitHub PAT for repo access")

    # --- FalkorDB ---
    falkordb_host: str = Field(default="localhost")
    falkordb_port: int = Field(default=6379)

    # --- FastAPI REST Server ---
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # --- FastMCP Server ---
    mcp_host: str = Field(default="0.0.0.0")
    mcp_port: int = Field(default=8001)
    mcp_auth_token: str = Field(default="chokepoint-dev-token")

    # --- App ---
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[4] / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
