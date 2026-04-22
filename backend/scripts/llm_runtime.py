"""
LLM runtime helpers shared by simulation scripts.
"""

from __future__ import annotations

import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse


PLACEHOLDER_ENV_VALUES = {
    "your_api_key_here",
    "your_base_url_here",
    "your_model_name_here",
    "your_zep_api_key_here",
}
LOCAL_LLM_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


@dataclass(frozen=True)
class LLMRuntimeConfig:
    api_key: str
    base_url: str
    model_name: str
    label: str
    timeout: float
    max_retries: int
    semaphore: int


def _normalize_env_value(value: Optional[str]) -> str:
    if not value:
        return ""

    normalized = value.strip()
    if not normalized:
        return ""

    if normalized.lower() in PLACEHOLDER_ENV_VALUES:
        return ""

    return normalized


def _is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_local_base_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.hostname in LOCAL_LLM_HOSTS


def _read_float_env(name: str, default: float) -> float:
    raw = _normalize_env_value(os.environ.get(name))
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _read_int_env(name: str, default: int) -> int:
    raw = _normalize_env_value(os.environ.get(name))
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _preflight_local_endpoint(base_url: str, api_key: str) -> None:
    endpoint = f"{base_url.rstrip('/')}/models"
    request = urllib.request.Request(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    try:
        with urllib.request.urlopen(request, timeout=2.5) as response:
            if response.status >= 500:
                raise ValueError(f"HTTP {response.status}")
    except (
        urllib.error.URLError,
        socket.timeout,
        TimeoutError,
        ValueError,
    ) as exc:
        raise ValueError(
            "로컬 LLM 엔드포인트에 연결할 수 없습니다. "
            f"base_url={base_url} 를 확인하고 프록시/OpenCode 서버를 먼저 실행해 주세요. "
            f"원인: {exc}"
        ) from exc


def resolve_llm_runtime(
    config: Dict[str, Any],
    *,
    use_boost: bool = False,
    logger: Optional[Callable[[str], None]] = None,
) -> LLMRuntimeConfig:
    common_api_key = _normalize_env_value(os.environ.get("LLM_API_KEY"))
    common_base_url = _normalize_env_value(
        os.environ.get("LLM_BASE_URL") or config.get("llm_base_url")
    )
    common_model = _normalize_env_value(
        os.environ.get("LLM_MODEL_NAME") or config.get("llm_model")
    ) or "gpt-4o-mini"

    if not common_api_key:
        raise ValueError(
            "API Key 설정이 누락되었습니다. 프로젝트 루트 .env 에서 LLM_API_KEY 를 설정해 주세요."
        )

    if common_base_url and not _is_valid_http_url(common_base_url):
        raise ValueError(
            "LLM_BASE_URL 형식이 올바르지 않습니다. http:// 또는 https:// 를 포함한 URL 이어야 합니다: "
            f"{common_base_url}"
        )

    selected_api_key = common_api_key
    selected_base_url = common_base_url
    selected_model = common_model
    label = "[공통 LLM]"

    if use_boost:
        boost_api_key = _normalize_env_value(os.environ.get("LLM_BOOST_API_KEY"))
        boost_base_url = _normalize_env_value(os.environ.get("LLM_BOOST_BASE_URL"))
        boost_model = _normalize_env_value(os.environ.get("LLM_BOOST_MODEL_NAME"))

        if boost_api_key and boost_base_url and boost_model:
            if not _is_valid_http_url(boost_base_url):
                if logger:
                    logger(
                        "LLM_BOOST_BASE_URL 형식이 잘못되어 가속 LLM 대신 공통 LLM을 사용합니다: "
                        f"{boost_base_url}"
                    )
            else:
                selected_api_key = boost_api_key
                selected_base_url = boost_base_url
                selected_model = boost_model
                label = "[가속 LLM]"
        elif any((boost_api_key, boost_base_url, boost_model)) and logger:
            logger(
                "LLM_BOOST_* 설정이 불완전하거나 예시값이라 공통 LLM으로 폴백합니다. "
                "병렬 실행 시 두 플랫폼이 같은 LLM 엔드포인트를 공유할 수 있습니다."
            )

    local_endpoint = bool(selected_base_url) and _is_local_base_url(selected_base_url)
    timeout_default = 45.0 if local_endpoint else 180.0
    retries_default = 1 if local_endpoint else 3
    semaphore_default = 4 if local_endpoint else 30

    runtime = LLMRuntimeConfig(
        api_key=selected_api_key,
        base_url=selected_base_url,
        model_name=selected_model,
        label=label,
        timeout=_read_float_env("LLM_REQUEST_TIMEOUT_SECONDS", timeout_default),
        max_retries=_read_int_env("LLM_MAX_RETRIES", retries_default),
        semaphore=_read_int_env("SIMULATION_LLM_SEMAPHORE", semaphore_default),
    )

    if runtime.base_url and _is_local_base_url(runtime.base_url):
        _preflight_local_endpoint(runtime.base_url, runtime.api_key)

    return runtime
