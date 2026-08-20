from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from .models import CloudRequestConfig


class V380CloudClient:
    """
    Small HTTP client for the V380 mapi service.
    """

    def __init__(
        self,
        config: CloudRequestConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else CloudRequestConfig()
        )

        self._client = httpx.Client(
            timeout=self.config.timeout,
            verify=self.config.verify_tls,
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "Content-Type": (
                    "application/json; charset=utf-8"
                ),
            },
        )

    def __enter__(self) -> V380CloudClient:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def build_url(
        self,
        path: str,
    ) -> str:
        cleaned_path = path.lstrip("/")

        return urljoin(
            self.config.base_url.rstrip("/") + "/",
            cleaned_path,
        )

    def post_json(
        self,
        path: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        if not path:
            raise ValueError(
                "Cloud API path cannot be empty."
            )

        url = self.build_url(path)

        try:
            response = self._client.post(
                url,
                content=json.dumps(
                    document,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8"),
            )
        except httpx.TimeoutException as error:
            raise TimeoutError(
                f"Cloud request timed out: {url}"
            ) from error
        except httpx.RequestError as error:
            raise ConnectionError(
                "Could not complete cloud request "
                f"to {url}: {error}"
            ) from error

        if response.status_code >= 400:
            preview = response.text[:500]

            raise ConnectionError(
                "Cloud request failed with HTTP "
                f"{response.status_code}: {preview}"
            )

        try:
            result = response.json()
        except json.JSONDecodeError as error:
            preview = response.text[:500]

            raise ValueError(
                "Cloud response was not valid JSON: "
                f"{preview}"
            ) from error

        if not isinstance(result, dict):
            raise ValueError(
                "Cloud response root is not a JSON object."
            )

        return result