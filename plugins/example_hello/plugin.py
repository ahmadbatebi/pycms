"""Example Hello World plugin for PressAssistCMS.

This plugin demonstrates how to:
1. Register hooks
2. Inject CSS
3. Modify page content

To enable this plugin, remove "example_hello" from disabled_plugins in config.
"""


def on_load(api):
    """Called when plugin is enabled.

    Args:
        api: PluginAPI instance with limited access to CMS.
    """
    # Register hook to inject CSS
    api.register_hook("css_inject", inject_css, priority=50)

    # Register hook to modify page content
    api.register_hook("page_render", modify_page, priority=50)


def on_unload():
    """Called when plugin is disabled."""
    pass


def inject_css(payload):
    """Inject custom CSS into pages.

    Args:
        payload: Dict with request info.

    Returns:
        CSS string to inject.
    """
    return """
    <style>
        /* Injected by Hello World plugin */
        .hello-plugin-badge {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: #4f46e5;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 9999;
        }
    </style>
    """


def modify_page(payload):
    """Modify page content before rendering.

    Args:
        payload: Dict with 'content', 'page', 'request'.

    Returns:
        Modified payload.
    """
    # Add a badge to the end of content
    badge = '<div class="hello-plugin-badge">Hello Plugin Active</div>'
    payload["content"] = payload.get("content", "") + badge

    return payload
