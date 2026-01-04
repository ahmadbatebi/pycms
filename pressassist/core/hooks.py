"""Event hook system for plugin integration."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Hook:
    """Registered hook callback."""

    name: str
    callback: Callable
    priority: int = 50  # Lower = runs earlier
    plugin: str | None = None


class HookManager:
    """Event-based hook system for extensibility.

    Plugins can register callbacks for events and modify data
    as it passes through the system.

    Events:
    - page_render: Before page content is rendered
    - page_save_before: Before page is saved
    - page_save_after: After page is saved
    - page_delete: Before page is deleted
    - block_render: Before block content is rendered
    - menu_render: Before menu is rendered
    - css_inject: Inject CSS into page head
    - js_inject: Inject JS into page
    - upload_before: Before file upload processed
    - upload_after: After file upload completed
    - auth_success: After successful login
    - auth_failed: After failed login attempt
    - settings_save: Before settings are saved
    """

    # Known events for documentation
    KNOWN_EVENTS = {
        "page_render",
        "page_save_before",
        "page_save_after",
        "page_delete",
        "block_render",
        "menu_render",
        "css_inject",
        "js_inject",
        "upload_before",
        "upload_after",
        "auth_success",
        "auth_failed",
        "settings_save",
        "theme_change",
        "plugin_enable",
        "plugin_disable",
        "backup_before",
        "backup_after",
        "restore_before",
        "restore_after",
    }

    def __init__(self):
        """Initialize hook manager."""
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
        self._sorted: dict[str, bool] = {}

    def register(
        self,
        event: str,
        callback: Callable,
        priority: int = 50,
        plugin: str | None = None,
    ) -> None:
        """Register a hook callback for an event.

        Args:
            event: Event name to listen for.
            callback: Function to call. Should accept and return payload.
            priority: Execution order (lower = earlier). Default 50.
            plugin: Plugin name that registered this hook.
        """
        hook = Hook(
            name=event,
            callback=callback,
            priority=priority,
            plugin=plugin,
        )
        self._hooks[event].append(hook)
        self._sorted[event] = False

    def unregister(self, event: str, callback: Callable) -> bool:
        """Unregister a hook callback.

        Args:
            event: Event name.
            callback: Callback to remove.

        Returns:
            True if callback was found and removed.
        """
        initial_count = len(self._hooks[event])
        self._hooks[event] = [h for h in self._hooks[event] if h.callback != callback]
        return len(self._hooks[event]) < initial_count

    def unregister_plugin(self, plugin: str) -> int:
        """Unregister all hooks from a plugin.

        Args:
            plugin: Plugin name.

        Returns:
            Number of hooks removed.
        """
        removed = 0
        for event in self._hooks:
            initial = len(self._hooks[event])
            self._hooks[event] = [h for h in self._hooks[event] if h.plugin != plugin]
            removed += initial - len(self._hooks[event])
        return removed

    def emit(self, event: str, payload: Any = None) -> Any:
        """Emit an event and pass payload through all hooks.

        Args:
            event: Event name.
            payload: Data to pass through hooks.

        Returns:
            Modified payload after all hooks processed.
        """
        if event not in self._hooks or not self._hooks[event]:
            return payload

        # Sort by priority if needed
        if not self._sorted.get(event, False):
            self._hooks[event].sort(key=lambda h: h.priority)
            self._sorted[event] = True

        # Pass payload through each hook
        for hook in self._hooks[event]:
            try:
                result = hook.callback(payload)
                if result is not None:
                    payload = result
            except Exception as e:
                # Log but don't break the chain
                # In production, this should use proper logging
                print(f"Hook error in {hook.plugin or 'unknown'}:{event}: {e}")

        return payload

    def emit_collect(self, event: str, payload: Any = None) -> list[Any]:
        """Emit event and collect all hook results.

        Unlike emit(), this collects all results instead of chaining.

        Args:
            event: Event name.
            payload: Data to pass to each hook.

        Returns:
            List of all hook return values.
        """
        results = []

        if event not in self._hooks:
            return results

        if not self._sorted.get(event, False):
            self._hooks[event].sort(key=lambda h: h.priority)
            self._sorted[event] = True

        for hook in self._hooks[event]:
            try:
                result = hook.callback(payload)
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Hook error in {hook.plugin or 'unknown'}:{event}: {e}")

        return results

    def has_hooks(self, event: str) -> bool:
        """Check if event has any registered hooks.

        Args:
            event: Event name.

        Returns:
            True if hooks are registered.
        """
        return bool(self._hooks.get(event))

    def get_hooks(self, event: str) -> list[Hook]:
        """Get all hooks for an event.

        Args:
            event: Event name.

        Returns:
            List of registered hooks.
        """
        return list(self._hooks.get(event, []))

    def clear(self, event: str | None = None) -> None:
        """Clear all hooks or hooks for specific event.

        Args:
            event: Event to clear, or None to clear all.
        """
        if event:
            self._hooks[event] = []
            self._sorted[event] = False
        else:
            self._hooks.clear()
            self._sorted.clear()


# Global hook manager instance
hook_manager = HookManager()


def on(event: str, priority: int = 50, plugin: str | None = None):
    """Decorator to register a hook callback.

    Usage:
        @on("page_render")
        def modify_page(payload):
            payload["content"] += "<p>Added by plugin</p>"
            return payload

    Args:
        event: Event name.
        priority: Execution priority.
        plugin: Plugin name.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        hook_manager.register(event, func, priority, plugin)
        return func

    return decorator
