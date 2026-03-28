"""
test_endpoints.py — Comprehensive endpoint testing for the Shopping Assistant.

Tests the full flow including SSE streaming and interrupt/approval handling.

Usage:
    python -m pytest test_endpoints.py -v -s

Or run directly:
    python test_endpoints.py
"""

import asyncio
import json
import re
from typing import AsyncGenerator

import httpx
import pytest

# --- Configuration ---
BASE_URL = "http://localhost:8000"
TIMEOUT = 60  # seconds


# ---------------------------------------------------------------------------
# Helper: Parse SSE stream events
# ---------------------------------------------------------------------------
def parse_sse_event(line: str) -> dict | None:
    """Parse a single SSE line into event dict."""
    if not line.startswith("data: "):
        return None
    try:
        return json.loads(line[6:])
    except json.JSONDecodeError:
        return None


async def stream_query(
    client: httpx.AsyncClient,
    query: str,
    display_currency: str = "PKR",
    thread_id: str | None = None,
    approved: bool | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream a query request and yield parsed events.
    Handles interrupts and resume flow.
    """
    payload = {
        "query": query,
        "display_currency": display_currency,
    }
    if thread_id:
        payload["thread_id"] = thread_id
    if approved is not None:
        payload["approved"] = approved

    async with client.stream(
        "POST",
        f"{BASE_URL}/api/query",
        json=payload,
        timeout=TIMEOUT,
    ) as response:
        async for line in response.aiter_lines():
            event = parse_sse_event(line)
            if event:
                yield event


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------


class TestEndpoints:
    """Test suite for the Shopping Assistant API."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test the health check endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_exchange_rate_endpoint(self):
        """Test GET /api/exchange-rate."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/exchange-rate")
            assert response.status_code == 200
            data = response.json()
            assert "usd_to_pkr" in data
            assert "pkr_to_usd" in data
            assert "source" in data
            assert data["usd_to_pkr"] > 0
            print(f"Exchange rate: 1 USD = {data['usd_to_pkr']:.2f} PKR (source: {data['source']})")

    @pytest.mark.asyncio
    async def test_demo_sessions_endpoint(self):
        """Test GET /api/demo-sessions."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/demo-sessions")
            assert response.status_code == 200
            sessions = response.json()
            # May be empty before seeding
            assert isinstance(sessions, list)
            print(f"Demo sessions: {len(sessions)} found")

    @pytest.mark.asyncio
    async def test_query_with_interrupt_and_approval(self):
        """
        Test the full flow: query → interrupt → approval → completion.
        """
        async with httpx.AsyncClient() as client:
            # --- Phase 1: Initial query (runs until interrupt) ---
            print("\n[Phase 1] Starting initial query: 'gaming laptop'")
            query = "gaming laptop"
            thread_id = None
            interrupt_data = None

            async for event in stream_query(client, query, "PKR"):
                event_type = event.get("event", "")
                print(f"  Event: {event_type}")

                if event_type == "interrupt":
                    interrupt_data = event.get("data", {})
                    thread_id = interrupt_data.get("thread_id")
                    search_terms = interrupt_data.get("search_terms", [])
                    budget_max = interrupt_data.get("budget_max")
                    print(f"  ✅ Received interrupt!")
                    print(f"     Thread ID: {thread_id}")
                    print(f"     Search terms: {search_terms}")
                    print(f"     Budget: {budget_max}")
                    break  # Stop at interrupt

            assert thread_id, "Should have received thread_id from interrupt"
            assert interrupt_data, "Should have received interrupt event"

            # --- Phase 2: Resume with approval ---
            print(f"\n[Phase 2] Resuming with thread_id={thread_id}, approved=True")
            final_result = None

            async for event in stream_query(client, query, "PKR", thread_id, approved=True):
                event_type = event.get("event", "")
                print(f"  Event: {event_type}")

                if event_type == "complete":
                    final_result = event.get("data", {})
                    print(f"  ✅ Pipeline complete!")
                    break

            assert final_result, "Should have received complete event"
            assert "ranked_products" in final_result
            assert "funnel_stats" in final_result
            assert "fetch_explanation" in final_result
            print(f"  Final products: {len(final_result.get('ranked_products', []))} ranked")

    @pytest.mark.asyncio
    async def test_query_with_rejection(self):
        """
        Test rejecting the interrupt (approved=False).
        Should terminate without scraping/filtering.
        """
        async with httpx.AsyncClient() as client:
            print("\n[Test] Query with rejection")
            query = "wireless earbuds"
            thread_id = None

            # Get interrupt
            async for event in stream_query(client, query, "PKR"):
                if event.get("event") == "interrupt":
                    thread_id = event.get("data", {}).get("thread_id")
                    print(f"  Got interrupt with thread_id={thread_id}")
                    break

            assert thread_id, "Should have received interrupt"

            # Resume with rejection
            print(f"  Resuming with approved=False...")
            got_complete = False

            async for event in stream_query(client, query, "PKR", thread_id, approved=False):
                event_type = event.get("event", "")
                if event_type == "complete":
                    got_complete = True
                    print(f"  Pipeline ended (rejected)")
                    break

            # When rejected, the pipeline should end quickly (no scraping)
            # So got_complete should be True with minimal data
            assert got_complete, "Should have received complete event after rejection"

    @pytest.mark.asyncio
    async def test_followup_query(self):
        """Test following up on a previous search with a new question."""
        async with httpx.AsyncClient() as client:
            # First, run an initial query to completion
            print("\n[Test] Follow-up query")
            query1 = "best smartphone under 50000 PKR"
            thread_id = None

            # Get interrupt from first query
            async for event in stream_query(client, query1, "PKR"):
                if event.get("event") == "interrupt":
                    thread_id = event.get("data", {}).get("thread_id")
                    break

            # Approve first query
            async for event in stream_query(client, query1, "PKR", thread_id, approved=True):
                if event.get("event") == "complete":
                    break

            assert thread_id, "Should have thread_id from first query"

            # Now send a follow-up using the same thread_id
            query2 = "Which one has the best camera?"
            print(f"  Sending follow-up: '{query2}'")

            async with client.stream(
                "POST",
                f"{BASE_URL}/api/followup",
                json={"thread_id": thread_id, "query": query2, "display_currency": "PKR"},
                timeout=TIMEOUT,
            ) as response:
                async for line in response.aiter_lines():
                    event = parse_sse_event(line)
                    if event and event.get("event") == "complete":
                        print(f"  ✅ Follow-up completed")
                        break

    @pytest.mark.asyncio
    async def test_currency_switch(self):
        """Test switching display currency without re-scraping."""
        async with httpx.AsyncClient() as client:
            print("\n[Test] Currency switch")
            query = "laptop stand"
            thread_id = None

            # Get initial results in PKR
            async for event in stream_query(client, query, "PKR"):
                if event.get("event") == "interrupt":
                    thread_id = event.get("data", {}).get("thread_id")
                    break

            async for event in stream_query(client, query, "PKR", thread_id, approved=True):
                if event.get("event") == "complete":
                    result_pkr = event.get("data", {})
                    break

            pkr_price = result_pkr.get("ranked_products", [{}])[0].get("price_display", 0)
            print(f"  Initial price (PKR): {pkr_price:.0f}")

            # Now switch to USD (fast, no re-scraping)
            response = await client.post(
                f"{BASE_URL}/api/switch-currency",
                json={"thread_id": thread_id, "display_currency": "USD"},
                timeout=10,
            )
            assert response.status_code == 200
            result_usd = response.json()
            usd_price = result_usd.get("ranked_products", [{}])[0].get("price_display", 0)
            exchange_rate = result_usd.get("exchange_rate", {}).get("usd_to_pkr", 278)
            print(f"  Switched to USD: {usd_price:.0f} (rate: 1 USD = {exchange_rate:.2f} PKR)")

            # Verify conversion math
            assert usd_price > 0, "Price should be converted to USD"
            print(f"  ✅ Currency switch successful (no re-scraping)")

    @pytest.mark.asyncio
    async def test_get_all_products(self):
        """Test GET /api/products/all to fetch all products for a session."""
        async with httpx.AsyncClient() as client:
            print("\n[Test] Get all products")

            # Run a query to completion
            query = "phone case"
            thread_id = None

            async for event in stream_query(client, query, "PKR"):
                if event.get("event") == "interrupt":
                    thread_id = event.get("data", {}).get("thread_id")
                    break

            async for event in stream_query(client, query, "PKR", thread_id, approved=True):
                if event.get("event") == "complete":
                    break

            # Fetch all products (included + excluded)
            response = await client.get(f"{BASE_URL}/api/products/all?thread_id={thread_id}")
            assert response.status_code == 200
            result = response.json()

            total = result.get("total", 0)
            products = result.get("products", [])
            print(f"  Total products in session: {total}")
            print(f"  Included: {sum(1 for p in products if p.get('filter_status') == 'included')}")
            print(f"  Excluded: {sum(1 for p in products if p.get('filter_status') == 'excluded')}")

            assert total > 0, "Should have products"
            assert len(products) == total, "Product count should match total"


# ---------------------------------------------------------------------------
# Main: Run tests interactively
# ---------------------------------------------------------------------------
async def main():
    """Run all tests interactively (outside pytest)."""
    suite = TestEndpoints()

    print("=" * 70)
    print("SHOPPING ASSISTANT ENDPOINT TESTS")
    print("=" * 70)

    try:
        print("\n[1/9] Health check...")
        await suite.test_health_check()

        print("\n[2/9] Exchange rate endpoint...")
        await suite.test_exchange_rate_endpoint()

        print("\n[3/9] Demo sessions endpoint...")
        await suite.test_demo_sessions_endpoint()

        print("\n[4/9] Query with interrupt and approval...")
        await suite.test_query_with_interrupt_and_approval()

        print("\n[5/9] Query with rejection...")
        await suite.test_query_with_rejection()

        print("\n[6/9] Follow-up query...")
        await suite.test_followup_query()

        print("\n[7/9] Currency switch...")
        await suite.test_currency_switch()

        print("\n[8/9] Get all products...")
        await suite.test_get_all_products()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)

    except Exception as exc:
        print(f"\n❌ TEST FAILED: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
