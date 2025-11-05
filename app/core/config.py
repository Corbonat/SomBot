from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheTtlConfig(BaseModel):
    bybit: int = 15
    rapira: int = 30
    grinex: int = 30


class FeatureFlags(BaseModel):
    enable_geo: bool = True
    enable_inline: bool = True
    enable_p2p_source: bool = True
    pred_autopost: bool = True


class Settings(BaseSettings):
    # Resolve env files from the project root (two levels up from this file)
    _env_root = Path(__file__).resolve().parents[2]
    _env_files = (str(_env_root / ".env"))

    model_config = SettingsConfigDict(
        env_file=_env_files, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    bot_token: Optional[SecretStr] = Field(default=None, alias="BOT_TOKEN")
    pred_bot_token: Optional[SecretStr] = Field(default=None, alias="PRED_BOT_TOKEN")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    bybit_endpoint: Optional[str] = Field("", alias="BYBIT_ENDPOINT")
    rapira_endpoint: Optional[str] = Field("", alias="RAPIRA_ENDPOINT")
    grinex_endpoint: Optional[str] = Field("", alias="GRINEX_ENDPOINT")
    usdtusd_source: Optional[str] = Field(None, alias="USDTUSD_SOURCE")
    usdrub_source: Optional[str] = Field(None, alias="USDRUB_SOURCE")

    default_source: Optional[str] = Field("bybit", alias="DEFAULT_SOURCE")
    default_method: Optional[str] = Field("vwap", alias="DEFAULT_METHOD")
    default_geo: Optional[str] = Field("none", alias="DEFAULT_GEO")
    vwap_depth: Optional[int] = Field(5, alias="VWAP_DEPTH")
    bybit_mode: Optional[str] = Field("orderbook", alias="BYBIT_MODE")

    geo_k_rio: Optional[float] = Field(0.0, alias="GEO_K_RIO")
    geo_k_berlin: Optional[float] = Field(0.0, alias="GEO_K_BERLIN")

    cache_ttl_per_source: Optional[CacheTtlConfig] = Field(default_factory=CacheTtlConfig, alias="CACHE_TTL_SEC_PER_SOURCE")
    rate_warn_age_sec: Optional[int] = Field(30, alias="RATE_WARN_AGE_SEC")
    circuit_breaker_open_sec: Optional[int] = Field(60, alias="CIRCUIT_BREAKER_OPEN_SEC")

    feature_flags: Optional[FeatureFlags] = Field(default_factory=FeatureFlags, alias="FEATURE_FLAGS")

    silent_hours: Optional[str] = Field(None, alias="SILENT_HOURS")
    pred_max_per_day: Optional[int] = Field(3, alias="PRED_MAX_PER_DAY")
    pred_min_chat_activity: Optional[int] = Field(10, alias="PRED_MIN_CHAT_ACTIVITY")
    pred_min_interval_min: Optional[int] = Field(30, alias="PRED_MIN_INTERVAL_MIN")

    academy_url: Optional[str] = Field(None, alias="ACADEMY_URL")
    contact_deeplink: Optional[str] = Field(None, alias="CONTACT_DEEPLINK")
    service_chat_id: Optional[int] = Field(None, alias="SERVICE_CHAT_ID")

    otel_endpoint: Optional[str] = Field(None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    privacy_contact_enc_keyref: Optional[str] = Field(None, alias="PRIVACY_CONTACT_ENC_KEYREF")

    # GetBlock configuration
    getblock_api_key: Optional[SecretStr] = Field(default=None, alias="GETBLOCK_API_KEY")
    getblock_base_url: Optional[str] = Field("https://api.getblock.net/rpc/v1/request", alias="GETBLOCK_BASE_URL")
    getblock_blockchain: Optional[str] = Field("eth", alias="GETBLOCK_BLOCKCHAIN")
    getblock_network: Optional[str] = Field("mainnet", alias="GETBLOCK_NETWORK")
    getblock_aml_token: Optional[SecretStr] = Field(default=None, alias="GETBLOCK_AML_TOKEN")
    getblock_evm_probe_order: Optional[str] = Field("ETH,BSC,MATIC,ETC", alias="EVM_PROBE_ORDER")
    getblock_default_evm_chain: Optional[str] = Field("ETH", alias="DEFAULT_EVM_CHAIN")
    getblock_request_timeout_sec: Optional[float] = Field(8.0, alias="REQUEST_TIMEOUT")
    getblock_poll_attempts: Optional[int] = Field(10, alias="POLL_ATTEMPTS")
    getblock_poll_delay_ms: Optional[int] = Field(1500, alias="POLL_DELAY_MS")

    @field_validator("feature_flags", mode="before")
    @classmethod
    def _parse_feature_flags(cls, value: Any) -> FeatureFlags:
        if isinstance(value, FeatureFlags) or value is None:
            return value or FeatureFlags()
        if isinstance(value, str):
            data: Dict[str, Any] = json.loads(value)
        elif isinstance(value, dict):
            data = value
        else:
            raise ValueError("Unsupported feature_flags type")
        return FeatureFlags(**data)

    @field_validator("cache_ttl_per_source", mode="before")
    @classmethod
    def _parse_cache_ttl(cls, value: Any) -> CacheTtlConfig:
        if isinstance(value, CacheTtlConfig) or value is None:
            return value or CacheTtlConfig()
        if isinstance(value, str):
            data: Dict[str, Any] = json.loads(value)
        elif isinstance(value, dict):
            data = value
        else:
            raise ValueError("Unsupported cache ttl type")
        return CacheTtlConfig(**data)

    @field_validator("service_chat_id", mode="before")
    @classmethod
    def _parse_service_chat_id(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            return int(value)
        raise ValueError("Unsupported service_chat_id value")

    @field_validator(
        "bot_token",
        "pred_bot_token",
        "database_url",
        "redis_url",
        "academy_url",
        "contact_deeplink",
        "usdtusd_source",
        "usdrub_source",
        "otel_endpoint",
        "privacy_contact_enc_keyref",
        "silent_hours",
        "getblock_base_url",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, value: Any) -> Any:
        if value is None:
            return None
        # Handle SecretStr that might already be constructed elsewhere
        if isinstance(value, SecretStr):
            secret = value.get_secret_value()
            return None if secret is None or not str(secret).strip() else value
        if isinstance(value, str):
            stripped = value.strip()
            return None if not stripped else value
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()