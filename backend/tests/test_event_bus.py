"""Tests for services/event_bus.py."""

import asyncio

from services.event_bus import _subscribers, publish, subscribe, unsubscribe


class TestEventBus:
    def test_subscribe_adds_subscriber(self):
        """Test that subscribe adds a subscriber."""
        queue = subscribe("test-build-1")

        assert "test-build-1" in _subscribers
        assert queue in _subscribers["test-build-1"]

        # Cleanup
        unsubscribe("test-build-1", queue)

    def test_unsubscribe_removes_subscriber(self):
        """Test that unsubscribe removes a subscriber."""
        queue = subscribe("test-build-2")
        assert "test-build-2" in _subscribers

        unsubscribe("test-build-2", queue)

        # The build_id key should be removed when no more subscribers
        assert "test-build-2" not in _subscribers

    def test_unsubscribe_handles_missing_build(self):
        """Test that unsubscribe doesn't crash for non-existent build."""
        fake_queue = asyncio.Queue()
        # Should not raise
        unsubscribe("nonexistent-build", fake_queue)

    def test_publish_sends_to_subscribers(self):
        """Test that publish sends events to all subscribers."""
        queue1 = subscribe("test-build-3")
        queue2 = subscribe("test-build-3")

        publish("test-build-3", "status", {"status": "coding"})

        # Both queues should have received the event
        assert not queue1.empty()
        assert not queue2.empty()

        event1 = queue1.get_nowait()
        event2 = queue2.get_nowait()

        assert event1["type"] == "status"
        assert event1["status"] == "coding"

        # Cleanup
        unsubscribe("test-build-3", queue1)
        unsubscribe("test-build-3", queue2)

    def test_publish_handles_no_subscribers(self):
        """Test that publish doesn't crash when there are no subscribers."""
        # Should not raise
        publish("no-subscribers-build", "status", {"status": "deployed"})

    def test_subscribe_returns_queue(self):
        """Test that subscribe returns a queue for receiving events."""
        queue = subscribe("test-build-4")

        assert isinstance(queue, asyncio.Queue)

        # Cleanup
        unsubscribe("test-build-4", queue)

    def test_multiple_subscribers_same_build(self):
        """Test multiple subscribers for the same build."""
        queue1 = subscribe("multi-build")
        queue2 = subscribe("multi-build")

        publish("multi-build", "step", {"step": "Building"})

        assert not queue1.empty()
        assert not queue2.empty()

        # Cleanup
        unsubscribe("multi-build", queue1)
        unsubscribe("multi-build", queue2)

    def test_event_has_timestamp(self):
        """Test that published events include a timestamp."""
        import time

        queue = subscribe("timestamp-test")
        before = time.time()
        publish("timestamp-test", "status", {"status": "done"})
        after = time.time()

        event = queue.get_nowait()
        assert "timestamp" in event
        assert before <= event["timestamp"] <= after

        unsubscribe("timestamp-test", queue)
