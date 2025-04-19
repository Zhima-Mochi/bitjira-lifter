import os
import pytest
from utils.field_resolver import resolve_fields

# Patch generate_summary for test
@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    monkeypatch.setattr("ai.generator.generate_summary", lambda ticket: f"AI-summary-for-{ticket}")
    # Mock config paths for testing
    monkeypatch.setattr("utils.field_resolver.DEFAULT_CONFIG", os.path.join("tests", "test_field_resolver.yaml"))
    monkeypatch.setattr("utils.field_resolver.OVERRIDES_DIR", "tests/ticket_overrides")


def test_resolve_fields_basic():
    fields = resolve_fields("TEST-9999")

    assert fields["jira_ticket"] == "TEST-9999"
    assert fields["summary"] == "overridden summary"
    assert fields["custom_field"] == "custom override"
    assert fields["ai_field"] == "AI-summary-for-TEST-9999"
    assert isinstance(fields["manual_field"], str)  # Should default to "" due to non-interactive mode