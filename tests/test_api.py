from app.services.llm import LLMError


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_event_creates_completed_report(client):
    response = await client.post("/events", json={"type": "incoming_call", "customer_id": "C-1001"})
    assert response.status_code == 202
    report_id = response.json()["report_id"]

    # Background tasks run before the ASGI response completes in tests.
    report = (await client.get(f"/reports/{report_id}")).json()
    assert report["status"] == "completed"
    assert report["customer_id"] == "C-1001"
    assert "## Summary" in report["content"]
    assert "Claire Martin" in report["content"]
    assert report["error"] is None


async def test_unknown_customer_is_rejected(client):
    response = await client.post("/events", json={"customer_id": "C-9999"})
    report_id = response.json()["report_id"]

    report = (await client.get(f"/reports/{report_id}")).json()
    assert report["status"] == "failed"
    assert "not found" in report["error"]


async def test_llm_failure_is_stored(make_client):
    class BrokenLLM:
        async def generate(self, system_prompt: str, user_content: str) -> str:
            raise LLMError("LLM returned HTTP 503")

    async for client in make_client(BrokenLLM()):
        response = await client.post("/events", json={"customer_id": "C-1001"})
        report = (await client.get(f"/reports/{response.json()['report_id']}")).json()
        assert report["status"] == "failed"
        assert report["error"] == "LLM returned HTTP 503"


async def test_unexpected_error_does_not_leak_details(make_client):
    class CrashingLLM:
        async def generate(self, system_prompt: str, user_content: str) -> str:
            raise RuntimeError("secret internal detail")

    async for client in make_client(CrashingLLM()):
        response = await client.post("/events", json={"customer_id": "C-1001"})
        report = (await client.get(f"/reports/{response.json()['report_id']}")).json()
        assert report["status"] == "failed"
        assert "secret" not in report["error"]


async def test_invalid_event_returns_422(client):
    response = await client.post("/events", json={"type": "unknown", "customer_id": "C-1001"})
    assert response.status_code == 422


async def test_report_not_found(client):
    response = await client.get("/reports/does-not-exist")
    assert response.status_code == 404


async def test_list_reports_filters_by_customer(client):
    await client.post("/events", json={"customer_id": "C-1001"})
    await client.post("/events", json={"customer_id": "C-1002"})
    await client.post("/events", json={"customer_id": "C-1002"})

    reports = (await client.get("/reports", params={"customer_id": "C-1002"})).json()
    assert len(reports) == 2
    assert {r["customer_id"] for r in reports} == {"C-1002"}
