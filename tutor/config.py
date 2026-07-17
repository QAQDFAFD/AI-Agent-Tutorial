"""集中配置：所有组件只依赖 Settings 对象，不直接读环境变量。"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-5.6"
    # "openai"：调用 Embedding API（质量高，需要支持该接口的服务商）；
    # "hash"：本地字符 n-gram 哈希向量（零成本零网络，适合 DeepSeek 等无 embedding 接口的服务商）。
    tutor_embedding_provider: Literal["openai", "hash"] = "openai"
    tutor_embedding_model: str = "text-embedding-3-small"

    docs_dir: Path = Path("docs")
    demos_dir: Path = Path("demos")
    assets_dir: Path = Path("assets")
    cache_dir: Path = Path("var")

    top_k: int = 4
    agent_recursion_limit: int = 10
    request_timeout_seconds: float = 60.0
