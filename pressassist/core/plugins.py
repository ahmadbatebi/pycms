"""Plugin loading and management."""

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .hooks import HookManager, hook_manager
from .logging import plugins_logger as logger


@dataclass
class PluginInfo:
    """Plugin metadata from plugin.json."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    entrypoint: str = "plugin.py"
    permissions: list[str] = field(default_factory=list)
    enabled: bool = False
    directory: str = ""


class PluginError(Exception):
    """Plugin loading or execution error."""

    pass


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle.

    Security features:
    - Plugins must have valid plugin.json manifest
    - Permissions declared in manifest
    - Plugins not auto-enabled on install
    - Access to CMS API only, no direct filesystem
    """

    # Allowed permissions for plugins
    VALID_PERMISSIONS = {
        "hook:css_inject",
        "hook:js_inject",
        "hook:page_render",
        "hook:page_save_before",
        "hook:page_save_after",
        "hook:block_render",
        "hook:menu_render",
        "hook:upload_after",
        "hook:auth_success",
        "api:read_pages",
        "api:read_blocks",
        "api:read_config",
    }

    def __init__(
        self,
        plugins_dir: Path,
        disabled_plugins: list[str] | None = None,
        hook_mgr: HookManager | None = None,
    ):
        """Initialize plugin manager.

        Args:
            plugins_dir: Path to plugins directory.
            disabled_plugins: List of disabled plugin names.
            hook_mgr: HookManager instance (uses global if None).
        """
        self.plugins_dir = plugins_dir
        self.disabled_plugins = set(disabled_plugins or [])
        self.hooks = hook_mgr or hook_manager
        self._loaded_plugins: dict[str, PluginInfo] = {}
        self._plugin_modules: dict[str, Any] = {}

    def discover_plugins(self) -> list[PluginInfo]:
        """Discover all plugins in plugins directory.

        Returns:
            List of PluginInfo for each valid plugin.
        """
        plugins = []

        if not self.plugins_dir.exists():
            return plugins

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            # Skip hidden directories
            if plugin_dir.name.startswith("."):
                continue

            info = self._load_plugin_info(plugin_dir)
            if info:
                info.enabled = plugin_dir.name not in self.disabled_plugins
                plugins.append(info)

        return plugins

    def _load_plugin_info(self, plugin_dir: Path) -> PluginInfo | None:
        """Load plugin metadata from plugin.json.

        Args:
            plugin_dir: Plugin directory.

        Returns:
            PluginInfo or None if invalid.
        """
        json_path = plugin_dir / "plugin.json"
        if not json_path.exists():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate required fields
            if "name" not in data:
                return None

            # Validate permissions and warn about invalid ones
            permissions = data.get("permissions", [])
            invalid_permissions = [p for p in permissions if p not in self.VALID_PERMISSIONS]
            if invalid_permissions:
                logger.warning(
                    f"Plugin '{plugin_dir.name}' requested invalid permissions: {invalid_permissions}"
                )
            valid_permissions = [p for p in permissions if p in self.VALID_PERMISSIONS]

            return PluginInfo(
                name=data.get("name", plugin_dir.name),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                author=data.get("author", ""),
                homepage=data.get("homepage", ""),
                entrypoint=data.get("entrypoint", "plugin.py"),
                permissions=valid_permissions,
                directory=plugin_dir.name,
            )
        except (json.JSONDecodeError, OSError):
            return None

    def load_plugin(self, plugin_name: str) -> bool:
        """Load and initialize a plugin.

        Args:
            plugin_name: Plugin directory name.

        Returns:
            True if loaded successfully.

        Raises:
            PluginError: If plugin cannot be loaded.
        """
        plugin_dir = self.plugins_dir / plugin_name

        info = self._load_plugin_info(plugin_dir)
        if not info:
            raise PluginError(f"Invalid plugin: {plugin_name}")

        entrypoint = plugin_dir / info.entrypoint
        if not entrypoint.exists():
            raise PluginError(f"Plugin entrypoint not found: {info.entrypoint}")

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                f"pressassist_plugin_{plugin_name}",
                entrypoint,
            )
            if spec is None or spec.loader is None:
                raise PluginError(f"Cannot load plugin module: {plugin_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Call on_load if exists
            if hasattr(module, "on_load"):
                # Pass limited API
                api = PluginAPI(
                    plugin_name=plugin_name,
                    permissions=set(info.permissions),
                    hooks=self.hooks,
                )
                module.on_load(api)

            self._loaded_plugins[plugin_name] = info
            self._plugin_modules[plugin_name] = module

            return True
        except Exception as e:
            raise PluginError(f"Error loading plugin {plugin_name}: {e}")

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Plugin to unload.

        Returns:
            True if unloaded.
        """
        if plugin_name not in self._loaded_plugins:
            return False

        module = self._plugin_modules.get(plugin_name)
        if module and hasattr(module, "on_unload"):
            try:
                module.on_unload()
            except Exception as e:
                logger.warning(f"Error during unload of plugin '{plugin_name}': {e}")

        # Remove hooks registered by this plugin
        self.hooks.unregister_plugin(plugin_name)

        del self._loaded_plugins[plugin_name]
        if plugin_name in self._plugin_modules:
            del self._plugin_modules[plugin_name]

        return True

    def load_enabled_plugins(self) -> int:
        """Load all enabled plugins.

        Returns:
            Number of plugins loaded.
        """
        loaded = 0
        for plugin in self.discover_plugins():
            if plugin.enabled:
                try:
                    if self.load_plugin(plugin.directory):
                        loaded += 1
                except PluginError as e:
                    # Log but continue loading others
                    logger.error(f"Failed to load plugin '{plugin.directory}': {e}")
        return loaded

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin.

        Args:
            plugin_name: Plugin to enable.

        Returns:
            True if enabled successfully.
        """
        self.disabled_plugins.discard(plugin_name)
        return self.load_plugin(plugin_name)

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin.

        Args:
            plugin_name: Plugin to disable.

        Returns:
            True if disabled.
        """
        self.disabled_plugins.add(plugin_name)
        return self.unload_plugin(plugin_name)

    def get_loaded_plugins(self) -> list[PluginInfo]:
        """Get list of currently loaded plugins.

        Returns:
            List of loaded PluginInfo.
        """
        return list(self._loaded_plugins.values())

    def is_loaded(self, plugin_name: str) -> bool:
        """Check if plugin is loaded.

        Args:
            plugin_name: Plugin to check.

        Returns:
            True if loaded.
        """
        return plugin_name in self._loaded_plugins


class PluginAPI:
    """Limited API exposed to plugins.

    Provides controlled access to CMS functionality based on
    declared permissions.
    """

    def __init__(
        self,
        plugin_name: str,
        permissions: set[str],
        hooks: HookManager,
    ):
        """Initialize plugin API.

        Args:
            plugin_name: Name of the plugin.
            permissions: Set of granted permissions.
            hooks: HookManager instance.
        """
        self.plugin_name = plugin_name
        self.permissions = permissions
        self._hooks = hooks

    def register_hook(
        self,
        event: str,
        callback: Callable,
        priority: int = 50,
    ) -> bool:
        """Register a hook callback.

        Args:
            event: Event name.
            callback: Callback function.
            priority: Execution priority.

        Returns:
            True if registered.

        Raises:
            PermissionError: If plugin lacks permission for this hook.
        """
        permission = f"hook:{event}"
        if permission not in self.permissions:
            logger.warning(
                f"Plugin '{self.plugin_name}' tried to register hook for "
                f"'{event}' without permission '{permission}'"
            )
            raise PermissionError(
                f"Plugin '{self.plugin_name}' lacks permission for hook: {event}"
            )

        self._hooks.register(
            event=event,
            callback=callback,
            priority=priority,
            plugin=self.plugin_name,
        )
        return True

    def has_permission(self, permission: str) -> bool:
        """Check if plugin has a permission.

        Args:
            permission: Permission to check.

        Returns:
            True if granted.
        """
        return permission in self.permissions
