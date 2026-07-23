"""Shared package smoke tests."""

from atlas_contracts.agents import AgentRequest, AgentResponse
from atlas_contracts.health import HealthStatus
from atlas_core.ids import new_id


def test_new_id_is_uuid_shaped() -> None:
    value = new_id()
    assert isinstance(value, str)
    assert len(value) >= 32


def test_health_status_values() -> None:
    assert HealthStatus.HEALTHY.value == "healthy"


def test_agent_contracts_roundtrip() -> None:
    request = AgentRequest(
        run_id=new_id(),
        context_refs=[],
        instructions="noop",
        constraints={},
    )
    response = AgentResponse(
        status="not_implemented",
        artifacts=[],
        messages=["ok"],
        metadata={},
    )
    assert request.instructions == "noop"
    assert response.status == "not_implemented"
