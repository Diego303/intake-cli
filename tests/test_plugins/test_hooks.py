"""Tests for the pipeline hook system."""

from __future__ import annotations

from intake.plugins.hooks import HookEvent, HookManager


class TestHookEvent:
    def test_create_with_name_only(self) -> None:
        event = HookEvent(name="post_parse")
        assert event.name == "post_parse"
        assert event.data == {}

    def test_create_with_data(self) -> None:
        event = HookEvent(name="pre_analyze", data={"source_count": 3})
        assert event.data["source_count"] == 3


class TestHookManager:
    def test_register_and_emit(self) -> None:
        manager = HookManager()
        results: list[str] = []
        manager.register("test_event", lambda e: results.append(e.name))
        manager.emit(HookEvent(name="test_event"))
        assert results == ["test_event"]

    def test_emit_no_listeners_is_noop(self) -> None:
        manager = HookManager()
        # Should not raise
        manager.emit(HookEvent(name="unregistered_event"))

    def test_multiple_callbacks_called_in_order(self) -> None:
        manager = HookManager()
        order: list[int] = []
        manager.register("event", lambda _: order.append(1))
        manager.register("event", lambda _: order.append(2))
        manager.register("event", lambda _: order.append(3))
        manager.emit(HookEvent(name="event"))
        assert order == [1, 2, 3]

    def test_callback_error_does_not_stop_others(self) -> None:
        manager = HookManager()
        results: list[str] = []

        def failing_callback(event: HookEvent) -> None:
            raise RuntimeError("oops")

        manager.register("event", lambda _: results.append("before"))
        manager.register("event", failing_callback)
        manager.register("event", lambda _: results.append("after"))

        manager.emit(HookEvent(name="event"))
        assert results == ["before", "after"]

    def test_registered_events(self) -> None:
        manager = HookManager()
        assert manager.registered_events == []

        manager.register("b_event", lambda _: None)
        manager.register("a_event", lambda _: None)
        assert manager.registered_events == ["a_event", "b_event"]

    def test_event_data_passed_to_callback(self) -> None:
        manager = HookManager()
        captured: list[dict[str, object]] = []
        manager.register("event", lambda e: captured.append(e.data))
        manager.emit(HookEvent(name="event", data={"key": "value"}))
        assert captured == [{"key": "value"}]
