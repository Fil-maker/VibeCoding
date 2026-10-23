"""Unit test of the schema export."""

import json

import pytest

from app.openapi import main


def test_openapi_prints_json_with_the_health_path(capsys: pytest.CaptureFixture[str]) -> None:
    main()

    schema = json.loads(capsys.readouterr().out)

    assert "/api/v1/health" in schema["paths"]
