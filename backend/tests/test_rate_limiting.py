"""Tests for rate limiting on the builds API."""


import pytest


class TestCreateBuildRateLimit:
    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the rate limiter storage before each test to avoid cross-test contamination."""
        from rate_limiter import limiter
        try:
            limiter.reset()
        except Exception:
            # limiter.reset() may not exist on all backends; clear storage directly
            try:
                limiter._storage.reset()
            except Exception:
                pass
        yield

    @pytest.mark.asyncio
    async def test_rate_limited_after_10_requests(self, client, mock_pipeline):
        """The POST /api/builds endpoint is limited to 10/minute.

        Fire 15 requests; at some point we should get a 429.
        """
        statuses = []
        for i in range(15):
            resp = await client.post(
                "/api/builds",
                json={"prompt": f"Rate limit test app #{i}"},
            )
            statuses.append(resp.status_code)

        # At least one request should have been rate limited
        assert 429 in statuses, f"Expected at least one 429, got: {statuses}"
        # And some should have succeeded
        assert 200 in statuses, f"Expected at least one 200, got: {statuses}"
