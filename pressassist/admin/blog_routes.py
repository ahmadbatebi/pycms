"""Blog admin routes for ChelCheleh."""

import html as _html
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import quote as _quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..core.i18n import t
from ..core.models import Role
from ..core.blog_models import PostStatus, CommentStatus
from .routes import (
    get_admin_lang_context,
    get_admin_html_attrs,
    get_admin_language_switcher_html,
    get_admin_rtl_styles,
    get_admin_footer,
    get_admin_nav,
    get_admin_header_right,
    get_admin_common_css,
    get_csrf_token,
    get_wysiwyg_head,
    get_wysiwyg_scripts,
    require_auth,
    require_csrf,
    get_post_options_for_association,
    get_category_options_for_association,
)

blog_router = APIRouter(prefix="/admin/blog", tags=["admin-blog"])


# ============================================================================
# Blog Dashboard
# ============================================================================


@blog_router.get("", response_class=HTMLResponse)
async def blog_dashboard(
    request: Request,
    session=Depends(require_auth()),
):
    """Render blog dashboard with stats."""
    from ..main import storage

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""

    posts = storage.get("blog_posts", {})
    categories = storage.get("blog_categories", {})
    comments = storage.get("blog_comments", {})

    # Count stats
    total_posts = len(posts)
    published_posts = sum(1 for p in posts.values() if p.get("status") == "published")
    draft_posts = sum(1 for p in posts.values() if p.get("status") == "draft")
    total_categories = len(categories)
    total_comments = len(comments)
    pending_comments = sum(1 for c in comments.values() if c.get("status") == "pending")

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                position: relative;
                overflow: hidden;
            }}
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
            }}
            .stat-card.purple::before {{ background: linear-gradient(135deg, #7c3aed, #a855f7); }}
            .stat-card.green::before {{ background: linear-gradient(135deg, #059669, #34d399); }}
            .stat-card.orange::before {{ background: linear-gradient(135deg, #d97706, #fbbf24); }}
            .stat-icon {{
                width: 48px;
                height: 48px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 1rem;
            }}
            .stat-icon.purple {{ background: linear-gradient(135deg, #7c3aed, #a855f7); }}
            .stat-icon.green {{ background: linear-gradient(135deg, #059669, #34d399); }}
            .stat-icon.orange {{ background: linear-gradient(135deg, #d97706, #fbbf24); }}
            .stat-icon svg {{ color: white; }}
            .stat-label {{ font-size: 0.875rem; color: #64748b; text-transform: uppercase; margin-bottom: 0.25rem; }}
            .stat-value {{ font-size: 2.5rem; font-weight: 700; color: #1e293b; line-height: 1; }}
            .stat-sub {{ font-size: 0.875rem; color: #64748b; margin-top: 0.5rem; }}
            .quick-actions {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1rem;
            }}
            .action-card {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 1rem;
                text-decoration: none;
                color: inherit;
                transition: all 0.2s;
                border: 2px solid transparent;
            }}
            .action-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                border-color: #7c3aed;
            }}
            .action-icon {{
                width: 56px;
                height: 56px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            .action-icon.purple {{ background: linear-gradient(135deg, #7c3aed, #a855f7); }}
            .action-icon.green {{ background: linear-gradient(135deg, #059669, #34d399); }}
            .action-icon.blue {{ background: linear-gradient(135deg, #3b82f6, #60a5fa); }}
            .action-icon.orange {{ background: linear-gradient(135deg, #d97706, #fbbf24); }}
            .action-icon svg {{ color: white; }}
            .action-content h3 {{ margin: 0 0 0.25rem; color: #1e293b; font-size: 1.125rem; }}
            .action-content p {{ margin: 0; color: #64748b; font-size: 0.875rem; }}
            .badge {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: #ef4444;
                color: white;
                min-width: 20px;
                height: 20px;
                padding: 0 6px;
                border-radius: 10px;
                font-size: 0.75rem;
                font-weight: 600;
                margin-inline-start: 0.5rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <h1 class="page-title">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                {t('admin.blog.title')}
            </h1>

            <div class="stats-grid">
                <div class="stat-card purple">
                    <div class="stat-icon purple">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                    </div>
                    <div class="stat-label">{t('admin.blog.posts')}</div>
                    <div class="stat-value">{total_posts}</div>
                    <div class="stat-sub">{published_posts} {t('admin.blog.published')} / {draft_posts} {t('admin.blog.draft')}</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-icon green">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>
                    <div class="stat-label">{t('admin.blog.categories')}</div>
                    <div class="stat-value">{total_categories}</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-icon orange">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>
                    <div class="stat-label">{t('admin.blog.comments')}</div>
                    <div class="stat-value">{total_comments}</div>
                    <div class="stat-sub">{pending_comments} {t('admin.blog.pending')}</div>
                </div>
            </div>

            <h2 style="font-size:1.25rem;color:#1e293b;margin-bottom:1rem;">{t('admin.quick_actions')}</h2>
            <div class="quick-actions">
                <a href="/admin/blog/posts" class="action-card">
                    <div class="action-icon purple">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="8" y1="6" x2="21" y2="6"/>
                            <line x1="8" y1="12" x2="21" y2="12"/>
                            <line x1="8" y1="18" x2="21" y2="18"/>
                            <line x1="3" y1="6" x2="3.01" y2="6"/>
                            <line x1="3" y1="12" x2="3.01" y2="12"/>
                            <line x1="3" y1="18" x2="3.01" y2="18"/>
                        </svg>
                    </div>
                    <div class="action-content">
                        <h3>{t('admin.blog.posts')}</h3>
                        <p>{t('admin.blog.manage_posts')}</p>
                    </div>
                </a>
                <a href="/admin/blog/posts/new" class="action-card">
                    <div class="action-icon green">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 20h9"/>
                            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                        </svg>
                    </div>
                    <div class="action-content">
                        <h3>{t('admin.blog.new_post')}</h3>
                        <p>{t('admin.blog.create_new_post')}</p>
                    </div>
                </a>
                <a href="/admin/blog/categories" class="action-card">
                    <div class="action-icon blue">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>
                    <div class="action-content">
                        <h3>{t('admin.blog.categories')}</h3>
                        <p>{t('admin.blog.manage_categories')}</p>
                    </div>
                </a>
                <a href="/admin/blog/comments" class="action-card">
                    <div class="action-icon orange">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>
                    <div class="action-content">
                        <h3>{t('admin.blog.comments')}{f'<span class="badge">{pending_comments}</span>' if pending_comments > 0 else ''}</h3>
                        <p>{t('admin.blog.manage_comments')}</p>
                    </div>
                </a>
            </div>
        </div>
        {get_admin_footer()}
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================================
# Posts Management
# ============================================================================


@blog_router.get("/posts", response_class=HTMLResponse)
async def posts_list(
    request: Request,
    session=Depends(require_auth()),
):
    """Render posts list."""
    from ..main import storage

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    token, needs_cookie = get_csrf_token(request)

    posts = storage.get("blog_posts", {})
    categories = storage.get("blog_categories", {})

    # Sort posts by created_at descending
    sorted_posts = sorted(
        posts.values(),
        key=lambda p: p.get("created_at", ""),
        reverse=True,
    )

    def get_category_name(cat_slug):
        cat = categories.get(cat_slug, {})
        return cat.get("name", cat_slug) if cat_slug else "-"

    def get_status_badge(status):
        colors = {
            "published": "#059669",
            "draft": "#64748b",
            "scheduled": "#d97706",
        }
        labels = {
            "published": t('admin.blog.published'),
            "draft": t('admin.blog.draft'),
            "scheduled": t('admin.blog.scheduled'),
        }
        color = colors.get(status, "#64748b")
        label = labels.get(status, status)
        return f'<span class="status-badge" style="background:{color};">{label}</span>'

    rows = "\n".join(
        f"""<tr data-slug="{_html.escape(p.get('slug',''))}">
            <td>
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span style="font-weight:500;">{_html.escape(p.get('title',''))}</span>
                </div>
            </td>
            <td>{get_category_name(p.get('category'))}</td>
            <td>{get_status_badge(p.get('status', 'draft'))}</td>
            <td>{_html.escape(p.get('author', ''))}</td>
            <td>{p.get('created_at', '')[:10] if p.get('created_at') else '-'}</td>
            <td>
                <div class="action-btns">
                    <a href="/admin/blog/posts/edit/{_quote(p.get('slug',''))}" class="btn-icon edit" title="{t('common.edit')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </a>
                    <button class="btn-icon delete delete-btn" data-slug="{_html.escape(p.get('slug',''))}" title="{t('common.delete')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>"""
        for p in sorted_posts
    )

    empty_state = f'''
    <tr>
        <td colspan="6">
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                <p style="margin:0.5rem 0;color:#64748b;">{t('admin.blog.no_posts')}</p>
                <a href="/admin/blog/posts/new" class="btn btn-primary" style="margin-top:0.5rem;">{t('admin.blog.new_post')}</a>
            </div>
        </td>
    </tr>
    '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.posts')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .page-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
                gap: 1rem;
            }}
            .status-badge {{
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 500;
                color: white;
            }}
            .action-btns {{
                display: flex;
                gap: 0.5rem;
            }}
            .btn-icon {{
                width: 32px;
                height: 32px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .btn-icon.edit {{
                background: #ede9fe;
                color: #7c3aed;
            }}
            .btn-icon.edit:hover {{
                background: #7c3aed;
                color: white;
            }}
            .btn-icon.delete {{
                background: #fee2e2;
                color: #dc2626;
            }}
            .btn-icon.delete:hover {{
                background: #dc2626;
                color: white;
            }}
            .empty-state {{
                text-align: center;
                padding: 3rem 1rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <div class="page-header">
                <h1 class="page-title" style="margin:0;">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    {t('admin.blog.posts')}
                </h1>
                <a class="btn btn-primary" href="/admin/blog/posts/new">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-inline-end:0.5rem;">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    {t('admin.blog.new_post')}
                </a>
            </div>
            <div id="msg" class="alert" style="display:none;"></div>
            <div class="card card-static">
                <div class="card-header primary">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6"/>
                        <line x1="8" y1="12" x2="21" y2="12"/>
                        <line x1="8" y1="18" x2="21" y2="18"/>
                        <line x1="3" y1="6" x2="3.01" y2="6"/>
                        <line x1="3" y1="12" x2="3.01" y2="12"/>
                        <line x1="3" y1="18" x2="3.01" y2="18"/>
                    </svg>
                    {t('admin.blog.posts')}
                </div>
                <div class="card-body" style="padding:0;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>{t('common.title')}</th>
                                <th>{t('admin.blog.category')}</th>
                                <th>{t('common.status')}</th>
                                <th>{t('admin.blog.author')}</th>
                                <th>{t('admin.blog.created_at')}</th>
                                <th style="width:100px;">{t('common.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else empty_state}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {get_admin_footer()}
        <script>
            const csrfToken = {token!r};
            function showMsg(type, text) {{
                const msg = document.getElementById('msg');
                msg.className = 'alert alert-' + type;
                msg.textContent = text;
                msg.style.display = 'block';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }}
            document.querySelectorAll('.delete-btn').forEach(btn => {{
                btn.addEventListener('click', async (e) => {{
                    const slug = e.currentTarget.dataset.slug;
                    if (!confirm('{t("admin.blog.delete_confirm")}')) return;

                    const res = await fetch('/admin/blog/api/posts/' + slug, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }}
                    }});

                    if (res.ok) {{
                        e.currentTarget.closest('tr').remove();
                        showMsg('success', '{t("messages.deleted")}');
                    }} else {{
                        const data = await res.json();
                        showMsg('error', data.detail || 'Error');
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@blog_router.get("/posts/new", response_class=HTMLResponse)
async def post_new(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render new post form."""
    from ..main import storage

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    csrf_token, needs_cookie = get_csrf_token(request)
    wysiwyg_head = get_wysiwyg_head()
    wysiwyg_scripts = get_wysiwyg_scripts(csrf_token)

    categories = storage.get("blog_categories", {})
    pages = storage.get("pages", {})

    cat_options = "\n".join(
        f'<option value="{_html.escape(c["slug"])}">{_html.escape(c["name"])}</option>'
        for c in sorted(categories.values(), key=lambda x: x.get("order", 0))
    )

    page_checkboxes = "\n".join(
        f'''<label style="display:block;margin:0.25rem 0;">
            <input type="checkbox" name="display_pages" value="{_html.escape(p["slug"])}">
            {_html.escape(p.get("title", p["slug"]))}
        </label>'''
        for p in pages.values()
        if p.get("visibility") != "system"
    )

    uploads = storage.get("uploads", {})
    image_uploads = [u for u in uploads.values() if u.get("mime_type", "").startswith("image/")]
    image_options = "\n".join(
        f'<option value="{_html.escape(u["uuid"])}">{_html.escape(u["original_name"])}</option>'
        for u in sorted(image_uploads, key=lambda x: x.get("uploaded_at", ""), reverse=True)
    )

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.new_post')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; min-height: 100vh; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .header-right {{ display: flex; align-items: center; gap: 1rem; }}
            .page-wrapper {{ display: flex; justify-content: center; width: 100%; padding: 2rem 1rem; }}
            .container {{ width: 100%; max-width: 1200px; margin-left: auto !important; margin-right: auto !important; }}
            .form-grid {{ display: grid; grid-template-columns: 1fr; gap: 2rem; }}
            @media (min-width: 992px) {{ .form-grid {{ grid-template-columns: 2fr 1fr; }} }}
            @media (min-width: 768px) and (max-width: 991px) {{ .form-grid {{ grid-template-columns: 1.5fr 1fr; }} }}
            .main-content {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 0; overflow: hidden; }}
            .sidebar {{ display: flex; flex-direction: column; gap: 1rem; min-width: 0; }}
            .sidebar-card {{ background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .sidebar-card h4 {{ margin: 0 0 1rem; color: #475569; font-size: 0.875rem; text-transform: uppercase; }}
            label {{ display: block; margin: 0.75rem 0 0.25rem; font-weight: 500; color: #334155; }}
            input, select, textarea {{ width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 1rem; box-sizing: border-box; }}
            input:focus, select:focus, textarea:focus {{ outline: none; border-color: #7c3aed; }}
            .btn {{ padding: 0.75rem 1.5rem; background: #7c3aed; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; }}
            .btn:hover {{ background: #6d28d9; }}
            .error {{ color: #b91c1c; padding: 0.75rem; background: #fee2e2; border-radius: 6px; margin-bottom: 1rem; }}
            .tag-input {{ display: flex; flex-wrap: wrap; gap: 0.25rem; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; min-height: 2.5rem; }}
            .tag {{ display: inline-flex; align-items: center; background: #e0e7ff; color: #4338ca; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.875rem; }}
            .tag button {{ background: none; border: none; color: #4338ca; cursor: pointer; margin-left: 0.25rem; }}
            .tag-input input {{ flex: 1; border: none; outline: none; min-width: 100px; }}
            h2 {{ text-align: center; color: #1e293b; margin-bottom: 1.5rem; }}
            .ck-editor-container, .ck-editor-wrapper {{ max-width: 100% !important; overflow: hidden; }}
            @media (max-width: 480px) {{
                .page-wrapper {{ padding: 1rem 0.5rem; }}
                .main-content, .sidebar-card {{ padding: 1rem; }}
            }}
        </style>
        {rtl_styles}
        {wysiwyg_head}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-weight:600;">{t('cms.name_short')}</a>
            <div class="header-right">{get_admin_header_right(lang_switcher, session.user_id)}</div>
        </div>
        {get_admin_nav()}
        <div class="page-wrapper">
        <div class="container">
            <h2>{t('admin.blog.new_post')}</h2>
            <div id="msg"></div>
            <form id="post-form">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <div class="form-grid">
                    <div class="main-content">
                        <label>{t('common.title')}</label>
                        <input name="title" required>

                        <label>{t('admin.blog.excerpt')}</label>
                        <textarea name="excerpt" rows="3"></textarea>

                        <label>{t('common.content')}</label>
                        <textarea name="content" id="editor-content"></textarea>
                    </div>
                    <div class="sidebar">
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.publish')}</h4>
                            <label>{t('common.status')}</label>
                            <select name="status">
                                <option value="draft">{t('admin.blog.draft')}</option>
                                <option value="published">{t('admin.blog.published')}</option>
                                <option value="scheduled">{t('admin.blog.scheduled')}</option>
                            </select>
                            <label>{t('admin.blog.publish_date')}</label>
                            <input type="datetime-local" name="published_at">
                            <button type="submit" class="btn" style="width:100%;margin-top:1rem;">{t('admin.blog.save_post')}</button>
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.category')}</h4>
                            <select name="category">
                                <option value="">{t('admin.blog.no_category')}</option>
                                {cat_options}
                            </select>
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.tags')}</h4>
                            <div class="tag-input" id="tag-container">
                                <input type="text" id="tag-input" placeholder="{t('admin.blog.add_tag')}">
                            </div>
                            <input type="hidden" name="tags" id="tags-hidden">
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.featured_image')}</h4>
                            <select name="featured_image">
                                <option value="">{t('admin.blog.no_image')}</option>
                                {image_options}
                            </select>
                            <div id="image-preview" style="margin-top:0.5rem;"></div>
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.display_pages')}</h4>
                            {page_checkboxes if page_checkboxes else f'<p style="color:#64748b;font-size:0.875rem;">{t("admin.blog.no_pages")}</p>'}
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.comments')}</h4>
                            <label style="display:flex;align-items:center;gap:0.5rem;">
                                <input type="checkbox" name="comments_enabled" checked style="width:auto;">
                                {t('admin.blog.comments_enabled')}
                            </label>
                            <label style="display:flex;align-items:center;gap:0.5rem;margin-top:0.5rem;">
                                <input type="checkbox" name="auto_approve_comments" style="width:auto;">
                                {t('admin.blog.auto_approve_comments')}
                            </label>
                        </div>
                        <div class="sidebar-card">
                            <h4>{t('admin.blog.language')}</h4>
                            <select name="language">
                                <option value="both">{t('admin.blog.lang_both')}</option>
                                <option value="en">{t('admin.blog.lang_en')}</option>
                                <option value="fa">{t('admin.blog.lang_fa')}</option>
                            </select>
                            <label style="margin-top:0.75rem;">{t('admin.blog.associated_post')}</label>
                            <select name="associated_post">
                                <option value="">{t('admin.blog.no_association')}</option>
                                {get_post_options_for_association(storage, "", None)}
                            </select>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        </div>
        {get_admin_footer()}
        {wysiwyg_scripts}
        <script>
            // Tags handling
            const tags = [];
            const tagContainer = document.getElementById('tag-container');
            const tagInput = document.getElementById('tag-input');
            const tagsHidden = document.getElementById('tags-hidden');

            function renderTags() {{
                const tagEls = tagContainer.querySelectorAll('.tag');
                tagEls.forEach(el => el.remove());
                tags.forEach((tag, i) => {{
                    const tagEl = document.createElement('span');
                    tagEl.className = 'tag';
                    tagEl.innerHTML = tag + '<button type="button" data-index="' + i + '">&times;</button>';
                    tagContainer.insertBefore(tagEl, tagInput);
                }});
                tagsHidden.value = JSON.stringify(tags);
            }}

            tagInput.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter' || e.key === ',') {{
                    e.preventDefault();
                    const val = tagInput.value.trim();
                    if (val && !tags.includes(val)) {{
                        tags.push(val);
                        renderTags();
                    }}
                    tagInput.value = '';
                }}
            }});

            tagContainer.addEventListener('click', (e) => {{
                if (e.target.tagName === 'BUTTON') {{
                    const index = parseInt(e.target.dataset.index);
                    tags.splice(index, 1);
                    renderTags();
                }}
            }});

            // Image preview
            document.querySelector('select[name="featured_image"]').addEventListener('change', (e) => {{
                const uuid = e.target.value;
                const preview = document.getElementById('image-preview');
                if (uuid) {{
                    preview.innerHTML = '<img src="/uploads/' + uuid + '" style="max-width:100%;border-radius:4px;">';
                }} else {{
                    preview.innerHTML = '';
                }}
            }});

            // Form submit
            document.getElementById('post-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);

                // Get editor content
                if (window.editorInstance) {{
                    formData.set('content', window.editorInstance.getData());
                }}

                // Get display_pages
                const displayPages = [];
                form.querySelectorAll('input[name="display_pages"]:checked').forEach(cb => {{
                    displayPages.push(cb.value);
                }});

                const data = {{
                    title: formData.get('title'),
                    excerpt: formData.get('excerpt'),
                    content: formData.get('content'),
                    status: formData.get('status'),
                    published_at: formData.get('published_at') || null,
                    category: formData.get('category') || null,
                    tags: tags,
                    featured_image: formData.get('featured_image') || null,
                    display_pages: displayPages,
                    comments_enabled: formData.get('comments_enabled') === 'on',
                    auto_approve_comments: formData.get('auto_approve_comments') === 'on',
                    language: formData.get('language') || 'both',
                    associated_post: formData.get('associated_post') || null,
                }};

                const res = await fetch('/admin/blog/api/posts', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': formData.get('csrf_token'),
                    }},
                    body: JSON.stringify(data),
                }});

                if (res.ok) {{
                    const post = await res.json();
                    window.location.href = '/admin/blog/posts/edit/' + post.slug + '?created=1';
                }} else {{
                    const err = await res.json();
                    document.getElementById('msg').className = 'error';
                    document.getElementById('msg').textContent = err.detail || 'Error';
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@blog_router.get("/posts/edit/{slug}", response_class=HTMLResponse)
async def post_edit(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render edit post form."""
    from ..main import storage

    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    csrf_token, needs_cookie = get_csrf_token(request)
    wysiwyg_head = get_wysiwyg_head()
    wysiwyg_scripts = get_wysiwyg_scripts(csrf_token)

    categories = storage.get("blog_categories", {})
    pages = storage.get("pages", {})

    title = _html.escape(post.get("title", ""))
    excerpt = _html.escape(post.get("excerpt", ""))
    content = _html.escape(post.get("content", ""))
    current_status = post.get("status", "draft")
    current_category = post.get("category", "")
    current_tags = post.get("tags", [])
    current_featured_image = post.get("featured_image", "")
    current_display_pages = post.get("display_pages", [])
    comments_enabled = post.get("comments_enabled", True)
    auto_approve_comments = post.get("auto_approve_comments", False)
    published_at = post.get("published_at", "")
    current_language = post.get("language", "both")
    current_associated_post = post.get("associated_post")
    if published_at:
        # Convert to datetime-local format
        published_at = published_at[:16] if len(published_at) >= 16 else ""

    cat_options = "\n".join(
        f'<option value="{_html.escape(c["slug"])}" {"selected" if c["slug"] == current_category else ""}>{_html.escape(c["name"])}</option>'
        for c in sorted(categories.values(), key=lambda x: x.get("order", 0))
    )

    page_checkboxes = "\n".join(
        f'''<label style="display:block;margin:0.25rem 0;">
            <input type="checkbox" name="display_pages" value="{_html.escape(p["slug"])}" {"checked" if p["slug"] in current_display_pages else ""}>
            {_html.escape(p.get("title", p["slug"]))}
        </label>'''
        for p in pages.values()
        if p.get("visibility") != "system"
    )

    uploads = storage.get("uploads", {})
    image_uploads = [u for u in uploads.values() if u.get("mime_type", "").startswith("image/")]
    image_options = "\n".join(
        f'<option value="{_html.escape(u["uuid"])}" {"selected" if u["uuid"] == current_featured_image else ""}>{_html.escape(u["original_name"])}</option>'
        for u in sorted(image_uploads, key=lambda x: x.get("uploaded_at", ""), reverse=True)
    )

    created_msg = t('admin.blog.created_success') if request.query_params.get("created") == "1" else ""
    tags_json = _html.escape(str(current_tags).replace("'", '"'))

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.edit_post')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            .tag-input-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                padding: 0.75rem;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                min-height: 48px;
                background: #f8fafc;
                transition: all 0.2s;
                align-items: center;
                width: 100%;
                box-sizing: border-box;
            }}
            .tag-input-container:focus-within {{
                border-color: #6366f1;
                background: white;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }}
            .tag {{
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
                color: #4338ca;
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 500;
            }}
            .tag button {{
                background: none;
                border: none;
                color: #6366f1;
                cursor: pointer;
                padding: 0;
                margin-inline-start: 0.25rem;
                font-size: 1rem;
                line-height: 1;
                opacity: 0.7;
                transition: opacity 0.2s;
            }}
            .tag button:hover {{ opacity: 1; }}
            .tag-input-container input {{
                flex: 1;
                border: none;
                outline: none;
                background: transparent;
                min-width: 80px;
                padding: 0.25rem;
                font-size: 0.95rem;
            }}
            .image-preview {{
                margin-top: 0.75rem;
                border-radius: 10px;
                overflow: hidden;
                background: #f1f5f9;
            }}
            .image-preview img {{
                width: 100%;
                height: auto;
                display: block;
                border-radius: 10px;
            }}
            .editor-wrapper {{ min-height: 400px; }}
            .ck-editor__editable {{ min-height: 350px !important; }}
            .slug-display {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 0.75rem;
                background: #f1f5f9;
                border-radius: 8px;
                font-family: monospace;
                font-size: 0.875rem;
                color: #64748b;
                word-break: break-all;
            }}
            .slug-display svg {{
                flex-shrink: 0;
                color: #94a3b8;
            }}
        </style>
        {rtl_styles}
        {wysiwyg_head}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" class="header-logo">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span class="header-separator">|</span>
                <span class="header-user">{session.user_id}</span>
                <a href="/admin/logout" class="header-logout">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <div class="page-header">
                <h1 class="page-title">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    {t('admin.blog.edit_post')}
                </h1>
                <div class="page-header-actions">
                    <a href="/admin/blog/posts" class="btn btn-secondary">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="19" y1="12" x2="5" y2="12"/>
                            <polyline points="12 19 5 12 12 5"/>
                        </svg>
                        <span class="btn-text">{t('admin.blog.back_to_posts')}</span>
                    </a>
                </div>
            </div>

            <div id="msg" class="alert {'alert-success' if created_msg else ''}" style="{'display:flex;' if created_msg else 'display:none;'}">{created_msg}</div>

            <form id="post-form">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <div class="two-col">
                    <div>
                        <div class="card card-static">
                            <div class="card-header primary">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                    <line x1="16" y1="13" x2="8" y2="13"/>
                                    <line x1="16" y1="17" x2="8" y2="17"/>
                                </svg>
                                {t('admin.blog.post_info')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label class="form-label">{t('common.title')}</label>
                                    <input name="title" value="{title}" required class="form-input">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Slug</label>
                                    <div class="slug-display">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                                        </svg>
                                        /blog/{slug}
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('admin.blog.excerpt')}</label>
                                    <textarea name="excerpt" rows="3" class="form-textarea">{excerpt}</textarea>
                                </div>
                            </div>
                        </div>

                        <div class="card card-static" style="margin-top:1rem;">
                            <div class="card-header purple">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 20h9"/>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                                </svg>
                                {t('common.content')}
                            </div>
                            <div class="card-body editor-wrapper">
                                <textarea name="content" id="editor-content">{content}</textarea>
                            </div>
                        </div>
                    </div>

                    <div class="sidebar-wrapper">
                        <div class="sidebar-sticky">
                            <div class="card card-static">
                                <div class="card-header success">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                        <polyline points="22 4 12 14.01 9 11.01"/>
                                    </svg>
                                    {t('admin.blog.publish')}
                                </div>
                                <div class="card-body">
                                    <div class="form-group">
                                        <label class="form-label">{t('common.status')}</label>
                                        <select name="status" class="form-select">
                                            <option value="draft" {"selected" if current_status == "draft" else ""}>{t('admin.blog.draft')}</option>
                                            <option value="published" {"selected" if current_status == "published" else ""}>{t('admin.blog.published')}</option>
                                            <option value="scheduled" {"selected" if current_status == "scheduled" else ""}>{t('admin.blog.scheduled')}</option>
                                        </select>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">{t('admin.blog.publish_date')}</label>
                                        <input type="datetime-local" name="published_at" value="{published_at}" class="form-input">
                                    </div>
                                </div>
                                <div class="card-footer">
                                    <button type="submit" class="btn btn-primary" style="width:100%;">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                            <polyline points="17 21 17 13 7 13 7 21"/>
                                            <polyline points="7 3 7 8 15 8"/>
                                        </svg>
                                        {t('admin.blog.update_post')}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header warning">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                                </svg>
                                {t('admin.blog.category')}
                            </div>
                            <div class="card-body">
                                <select name="category" class="form-select">
                                    <option value="">{t('admin.blog.no_category')}</option>
                                    {cat_options}
                                </select>
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header info">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
                                    <line x1="7" y1="7" x2="7.01" y2="7"/>
                                </svg>
                                {t('admin.blog.tags')}
                            </div>
                            <div class="card-body">
                                <div class="tag-input-container" id="tag-container">
                                    <input type="text" id="tag-input" placeholder="{t('admin.blog.add_tag')}">
                                </div>
                                <input type="hidden" name="tags" id="tags-hidden">
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header purple">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                    <circle cx="8.5" cy="8.5" r="1.5"/>
                                    <polyline points="21 15 16 10 5 21"/>
                                </svg>
                                {t('admin.blog.featured_image')}
                            </div>
                            <div class="card-body">
                                <select name="featured_image" class="form-select">
                                    <option value="">{t('admin.blog.no_image')}</option>
                                    {image_options}
                                </select>
                                <div id="image-preview" class="image-preview">
                                    {"<img src='/uploads/" + current_featured_image + "' alt='Featured'>" if current_featured_image else ""}
                                </div>
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header primary">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                </svg>
                                {t('admin.blog.display_pages')}
                            </div>
                            <div class="card-body">
                                {page_checkboxes if page_checkboxes else f'<p style="color:#64748b;font-size:0.875rem;">{t("admin.blog.no_pages")}</p>'}
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header success">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                                </svg>
                                {t('admin.blog.comments')}
                            </div>
                            <div class="card-body comment-settings">
                                <label class="checkbox-item">
                                    <input type="checkbox" name="comments_enabled" {"checked" if comments_enabled else ""}>
                                    <span>{t('admin.blog.comments_enabled')}</span>
                                </label>
                                <label class="checkbox-item">
                                    <input type="checkbox" name="auto_approve_comments" {"checked" if auto_approve_comments else ""}>
                                    <span>{t('admin.blog.auto_approve_comments')}</span>
                                </label>
                            </div>
                        </div>

                        <div class="card card-static">
                            <div class="card-header warning">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <line x1="2" y1="12" x2="22" y2="12"/>
                                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                                </svg>
                                {t('admin.blog.language')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label class="form-label">{t('admin.blog.post_language')}</label>
                                    <select name="language" class="form-select">
                                        <option value="both" {"selected" if current_language == "both" else ""}>{t('admin.blog.lang_both')}</option>
                                        <option value="en" {"selected" if current_language == "en" else ""}>{t('admin.blog.lang_en')}</option>
                                        <option value="fa" {"selected" if current_language == "fa" else ""}>{t('admin.blog.lang_fa')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('admin.blog.associated_post')}</label>
                                    <select name="associated_post" class="form-select">
                                        <option value="">{t('admin.blog.no_association')}</option>
                                        {get_post_options_for_association(storage, slug, current_associated_post)}
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        {get_admin_footer()}
        {wysiwyg_scripts}
        <script>
            const tags = {tags_json};
            const tagContainer = document.getElementById('tag-container');
            const tagInput = document.getElementById('tag-input');
            const tagsHidden = document.getElementById('tags-hidden');

            function renderTags() {{
                const tagEls = tagContainer.querySelectorAll('.tag');
                tagEls.forEach(el => el.remove());
                tags.forEach((tag, i) => {{
                    const tagEl = document.createElement('span');
                    tagEl.className = 'tag';
                    tagEl.innerHTML = tag + '<button type="button" data-index="' + i + '">&times;</button>';
                    tagContainer.insertBefore(tagEl, tagInput);
                }});
                tagsHidden.value = JSON.stringify(tags);
            }}

            renderTags();

            tagInput.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter' || e.key === ',') {{
                    e.preventDefault();
                    const val = tagInput.value.trim();
                    if (val && !tags.includes(val)) {{
                        tags.push(val);
                        renderTags();
                    }}
                    tagInput.value = '';
                }}
            }});

            tagContainer.addEventListener('click', (e) => {{
                if (e.target.tagName === 'BUTTON') {{
                    const index = parseInt(e.target.dataset.index);
                    tags.splice(index, 1);
                    renderTags();
                }}
            }});

            document.querySelector('select[name="featured_image"]').addEventListener('change', (e) => {{
                const uuid = e.target.value;
                const preview = document.getElementById('image-preview');
                if (uuid) {{
                    preview.innerHTML = '<img src="/uploads/' + uuid + '" alt="Featured">';
                }} else {{
                    preview.innerHTML = '';
                }}
            }});

            document.getElementById('post-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const formData = new FormData(form);

                if (window.editorInstance) {{
                    formData.set('content', window.editorInstance.getData());
                }}

                const displayPages = [];
                form.querySelectorAll('input[name="display_pages"]:checked').forEach(cb => {{
                    displayPages.push(cb.value);
                }});

                const data = {{
                    title: formData.get('title'),
                    excerpt: formData.get('excerpt'),
                    content: formData.get('content'),
                    status: formData.get('status'),
                    published_at: formData.get('published_at') || null,
                    category: formData.get('category') || null,
                    tags: tags,
                    featured_image: formData.get('featured_image') || null,
                    display_pages: displayPages,
                    comments_enabled: formData.get('comments_enabled') === 'on',
                    auto_approve_comments: formData.get('auto_approve_comments') === 'on',
                    language: formData.get('language') || 'both',
                    associated_post: formData.get('associated_post') || null,
                }};

                const res = await fetch('/admin/blog/api/posts/{slug}', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': formData.get('csrf_token'),
                    }},
                    body: JSON.stringify(data),
                }});

                const msg = document.getElementById('msg');
                if (res.ok) {{
                    msg.className = 'alert alert-success';
                    msg.textContent = '{t("messages.saved")}';
                    msg.style.display = 'flex';
                }} else {{
                    const err = await res.json();
                    msg.className = 'alert alert-error';
                    msg.textContent = err.detail || 'Error';
                    msg.style.display = 'flex';
                }}
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================================
# Categories Management
# ============================================================================


@blog_router.get("/categories", response_class=HTMLResponse)
async def categories_list(
    request: Request,
    session=Depends(require_auth()),
):
    """Render categories list."""
    from ..main import storage

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    token, needs_cookie = get_csrf_token(request)

    categories = storage.get("blog_categories", {})
    posts = storage.get("blog_posts", {})

    # Count posts per category
    def count_posts(cat_slug):
        return sum(1 for p in posts.values() if p.get("category") == cat_slug)

    sorted_cats = sorted(categories.values(), key=lambda c: c.get("order", 0))

    rows = "\n".join(
        f"""<tr data-slug="{_html.escape(c.get('slug',''))}">
            <td>
                <span class="order-badge">{c.get('order', 0)}</span>
            </td>
            <td>
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span style="font-weight:500;">{_html.escape(c.get('name',''))}</span>
                </div>
            </td>
            <td style="color:#64748b;font-family:monospace;font-size:0.875rem;">{_html.escape(c.get('slug',''))}</td>
            <td>
                <span class="count-badge">{count_posts(c.get('slug'))}</span>
            </td>
            <td>
                <div class="action-btns">
                    <button class="btn-icon edit edit-btn" data-slug="{_html.escape(c.get('slug',''))}" data-name="{_html.escape(c.get('name',''))}" data-description="{_html.escape(c.get('description',''))}" data-order="{c.get('order', 0)}" data-language="{c.get('language', 'both')}" data-associated="{c.get('associated_category', '') or ''}" title="{t('common.edit')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </button>
                    <button class="btn-icon delete delete-btn" data-slug="{_html.escape(c.get('slug',''))}" title="{t('common.delete')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>"""
        for c in sorted_cats
    )

    empty_state = f'''
    <tr>
        <td colspan="5">
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <p style="margin:0.5rem 0;color:#64748b;">{t('admin.blog.no_categories')}</p>
            </div>
        </td>
    </tr>
    '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.categories')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .two-col {{
                display: grid;
                grid-template-columns: 350px 1fr;
                gap: 1.5rem;
            }}
            @media (max-width: 992px) {{
                .two-col {{ grid-template-columns: 1fr; }}
            }}
            .order-badge {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 28px;
                height: 28px;
                background: #f1f5f9;
                color: #475569;
                border-radius: 6px;
                font-weight: 600;
                font-size: 0.875rem;
            }}
            .count-badge {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 24px;
                height: 24px;
                padding: 0 8px;
                background: #ede9fe;
                color: #7c3aed;
                border-radius: 12px;
                font-weight: 600;
                font-size: 0.75rem;
            }}
            .action-btns {{
                display: flex;
                gap: 0.5rem;
            }}
            .btn-icon {{
                width: 32px;
                height: 32px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .btn-icon.edit {{
                background: #ede9fe;
                color: #7c3aed;
            }}
            .btn-icon.edit:hover {{
                background: #7c3aed;
                color: white;
            }}
            .btn-icon.delete {{
                background: #fee2e2;
                color: #dc2626;
            }}
            .btn-icon.delete:hover {{
                background: #dc2626;
                color: white;
            }}
            .empty-state {{
                text-align: center;
                padding: 3rem 1rem;
            }}
            .form-card {{
                position: sticky;
                top: 1rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <h1 class="page-title">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                {t('admin.blog.categories')}
            </h1>
            <div id="msg" class="alert" style="display:none;"></div>
            <div class="two-col">
                <div class="form-card">
                    <div class="card card-static">
                        <div class="card-header success">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="5" x2="12" y2="19"/>
                                <line x1="5" y1="12" x2="19" y2="12"/>
                            </svg>
                            <span id="form-title">{t('admin.blog.add_category')}</span>
                        </div>
                        <div class="card-body">
                            <form id="cat-form">
                                <input type="hidden" name="csrf_token" value="{token}">
                                <input type="hidden" name="edit_slug" id="edit-slug" value="">
                                <div class="form-group">
                                    <label>{t('common.name')}</label>
                                    <input name="name" id="cat-name" required class="form-input">
                                </div>
                                <div class="form-group">
                                    <label>{t('common.description')}</label>
                                    <textarea name="description" id="cat-desc" rows="3" class="form-input"></textarea>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.blog.order')}</label>
                                    <input type="number" name="order" id="cat-order" value="0" class="form-input">
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.blog.language')}</label>
                                    <select name="language" id="cat-language" class="form-input">
                                        <option value="both">{t('admin.blog.lang_both')}</option>
                                        <option value="en">{t('admin.blog.lang_en')}</option>
                                        <option value="fa">{t('admin.blog.lang_fa')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.blog.associated_category')}</label>
                                    <select name="associated_category" id="cat-associated" class="form-input">
                                        <option value="">{t('admin.blog.no_association')}</option>
                                        {get_category_options_for_association(storage, "", None)}
                                    </select>
                                </div>
                            </form>
                        </div>
                        <div class="card-footer">
                            <button type="submit" form="cat-form" class="btn btn-primary" style="width:100%;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-inline-end:0.5rem;">
                                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                    <polyline points="17 21 17 13 7 13 7 21"/>
                                    <polyline points="7 3 7 8 15 8"/>
                                </svg>
                                {t('common.save')}
                            </button>
                            <button type="button" id="cancel-edit" class="btn" style="width:100%;margin-top:0.5rem;background:#64748b;display:none;">{t('common.cancel')}</button>
                        </div>
                    </div>
                </div>
                <div class="card card-static">
                    <div class="card-header primary">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="8" y1="6" x2="21" y2="6"/>
                            <line x1="8" y1="12" x2="21" y2="12"/>
                            <line x1="8" y1="18" x2="21" y2="18"/>
                            <line x1="3" y1="6" x2="3.01" y2="6"/>
                            <line x1="3" y1="12" x2="3.01" y2="12"/>
                            <line x1="3" y1="18" x2="3.01" y2="18"/>
                        </svg>
                        {t('admin.blog.categories')}
                    </div>
                    <div class="card-body" style="padding:0;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="width:60px;">{t('admin.blog.order')}</th>
                                    <th>{t('common.name')}</th>
                                    <th>Slug</th>
                                    <th style="width:80px;">{t('admin.blog.posts')}</th>
                                    <th style="width:100px;">{t('common.actions')}</th>
                                </tr>
                            </thead>
                            <tbody id="cat-table">
                                {rows if rows else empty_state}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {get_admin_footer()}
        <script>
            const csrfToken = {token!r};
            const form = document.getElementById('cat-form');
            const editSlug = document.getElementById('edit-slug');
            const cancelBtn = document.getElementById('cancel-edit');

            function showMsg(type, text) {{
                const msg = document.getElementById('msg');
                msg.className = 'alert alert-' + type;
                msg.textContent = text;
                msg.style.display = 'block';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }}

            function resetForm() {{
                form.reset();
                editSlug.value = '';
                document.getElementById('form-title').textContent = '{t("admin.blog.add_category")}';
                cancelBtn.style.display = 'none';
            }}

            cancelBtn.addEventListener('click', resetForm);

            // Edit button
            document.querySelectorAll('.edit-btn').forEach(btn => {{
                btn.addEventListener('click', () => {{
                    editSlug.value = btn.dataset.slug;
                    document.getElementById('cat-name').value = btn.dataset.name;
                    document.getElementById('cat-desc').value = btn.dataset.description;
                    document.getElementById('cat-order').value = btn.dataset.order;
                    document.getElementById('cat-language').value = btn.dataset.language || 'both';
                    document.getElementById('cat-associated').value = btn.dataset.associated || '';
                    document.getElementById('form-title').textContent = '{t("admin.blog.edit_category")}';
                    cancelBtn.style.display = 'block';
                    document.querySelector('.form-card').scrollIntoView({{ behavior: 'smooth' }});
                }});
            }});

            // Delete button
            document.querySelectorAll('.delete-btn').forEach(btn => {{
                btn.addEventListener('click', async () => {{
                    if (!confirm('{t("admin.blog.delete_category_confirm")}')) return;

                    const res = await fetch('/admin/blog/api/categories/' + btn.dataset.slug, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }}
                    }});

                    if (res.ok) {{
                        btn.closest('tr').remove();
                        showMsg('success', '{t("messages.deleted")}');
                    }} else {{
                        const data = await res.json();
                        showMsg('error', data.detail || 'Error');
                    }}
                }});
            }});

            // Form submit
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const formData = new FormData(form);
                const slug = editSlug.value;

                const data = {{
                    name: formData.get('name'),
                    description: formData.get('description'),
                    order: parseInt(formData.get('order')) || 0,
                    language: formData.get('language') || 'both',
                    associated_category: formData.get('associated_category') || null,
                }};

                const url = slug ? '/admin/blog/api/categories/' + slug : '/admin/blog/api/categories';
                const method = slug ? 'PUT' : 'POST';

                const res = await fetch(url, {{
                    method: method,
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    body: JSON.stringify(data),
                }});

                if (res.ok) {{
                    location.reload();
                }} else {{
                    const err = await res.json();
                    showMsg('error', err.detail || 'Error');
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================================
# Comments Management
# ============================================================================


@blog_router.get("/comments", response_class=HTMLResponse)
async def comments_list(
    request: Request,
    session=Depends(require_auth()),
):
    """Render comments list."""
    from ..main import storage

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    token, needs_cookie = get_csrf_token(request)

    comments = storage.get("blog_comments", {})
    posts = storage.get("blog_posts", {})

    # Sort by created_at descending
    sorted_comments = sorted(
        comments.values(),
        key=lambda c: c.get("created_at", ""),
        reverse=True,
    )

    def get_post_title(post_slug):
        post = posts.get(post_slug, {})
        return post.get("title", post_slug)

    def get_status_badge(status):
        colors = {
            "approved": "#059669",
            "pending": "#d97706",
            "spam": "#dc2626",
        }
        labels = {
            "approved": t('admin.blog.approved'),
            "pending": t('admin.blog.pending'),
            "spam": t('admin.blog.spam'),
        }
        color = colors.get(status, "#64748b")
        label = labels.get(status, status)
        return f'<span class="status-badge" style="background:{color};">{label}</span>'

    rows = "\n".join(
        f"""<tr data-id="{_html.escape(c.get('id',''))}">
            <td>
                <div class="author-info">
                    <div class="author-avatar">
                        {_html.escape(c.get('author_name','?')[0].upper())}
                    </div>
                    <div>
                        <div style="font-weight:500;">{_html.escape(c.get('author_name',''))}</div>
                        <div style="font-size:0.75rem;color:#64748b;">{_html.escape(c.get('author_email',''))}</div>
                    </div>
                </div>
            </td>
            <td>
                <div class="comment-content">{_html.escape(c.get('content','')[:150])}{'...' if len(c.get('content','')) > 150 else ''}</div>
            </td>
            <td>
                <a href="/admin/blog/posts/edit/{_quote(c.get('post_slug',''))}" class="post-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    {_html.escape(get_post_title(c.get('post_slug',''))[:30])}{'...' if len(get_post_title(c.get('post_slug',''))) > 30 else ''}
                </a>
            </td>
            <td>{get_status_badge(c.get('status', 'pending'))}</td>
            <td style="color:#64748b;font-size:0.875rem;">{c.get('created_at', '')[:10] if c.get('created_at') else '-'}</td>
            <td>
                <select class="status-select" data-id="{_html.escape(c.get('id',''))}">
                    <option value="pending" {"selected" if c.get('status') == 'pending' else ""}>{t('admin.blog.pending')}</option>
                    <option value="approved" {"selected" if c.get('status') == 'approved' else ""}>{t('admin.blog.approved')}</option>
                    <option value="spam" {"selected" if c.get('status') == 'spam' else ""}>{t('admin.blog.spam')}</option>
                </select>
            </td>
            <td>
                <button class="btn-icon delete delete-btn" data-id="{_html.escape(c.get('id',''))}" title="{t('common.delete')}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </td>
        </tr>"""
        for c in sorted_comments
    )

    empty_state = f'''
    <tr>
        <td colspan="7">
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <p style="margin:0.5rem 0;color:#64748b;">{t('admin.blog.no_comments')}</p>
            </div>
        </td>
    </tr>
    '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blog.comments')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .status-badge {{
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 500;
                color: white;
            }}
            .author-info {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}
            .author-avatar {{
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: linear-gradient(135deg, #7c3aed, #a855f7);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                font-size: 0.875rem;
            }}
            .comment-content {{
                color: #475569;
                line-height: 1.4;
                max-width: 300px;
            }}
            .post-link {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                color: #7c3aed;
                text-decoration: none;
                font-size: 0.875rem;
            }}
            .post-link:hover {{
                text-decoration: underline;
            }}
            .status-select {{
                padding: 0.375rem 0.75rem;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 0.875rem;
                background: white;
                cursor: pointer;
            }}
            .status-select:focus {{
                outline: none;
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }}
            .btn-icon {{
                width: 32px;
                height: 32px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .btn-icon.delete {{
                background: #fee2e2;
                color: #dc2626;
            }}
            .btn-icon.delete:hover {{
                background: #dc2626;
                color: white;
            }}
            .empty-state {{
                text-align: center;
                padding: 3rem 1rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <h1 class="page-title">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                {t('admin.blog.comments')}
            </h1>
            <div id="msg" class="alert" style="display:none;"></div>
            <div class="card card-static">
                <div class="card-header warning">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    {t('admin.blog.comments')}
                </div>
                <div class="card-body" style="padding:0;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width:200px;">{t('admin.blog.author')}</th>
                                <th>{t('common.content')}</th>
                                <th style="width:180px;">{t('admin.blog.post')}</th>
                                <th style="width:100px;">{t('common.status')}</th>
                                <th style="width:100px;">{t('admin.blog.date')}</th>
                                <th style="width:120px;">{t('common.actions')}</th>
                                <th style="width:50px;"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else empty_state}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {get_admin_footer()}
        <script>
            const csrfToken = {token!r};

            function showMsg(type, text) {{
                const msg = document.getElementById('msg');
                msg.className = 'alert alert-' + type;
                msg.textContent = text;
                msg.style.display = 'block';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }}

            // Status change
            document.querySelectorAll('.status-select').forEach(select => {{
                select.addEventListener('change', async () => {{
                    const res = await fetch('/admin/blog/api/comments/' + select.dataset.id, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        body: JSON.stringify({{ status: select.value }}),
                    }});

                    if (res.ok) {{
                        showMsg('success', '{t("messages.updated")}');
                        // Update badge color in the same row
                        const row = select.closest('tr');
                        const badge = row.querySelector('.status-badge');
                        const colors = {{ approved: '#059669', pending: '#d97706', spam: '#dc2626' }};
                        const labels = {{ approved: '{t("admin.blog.approved")}', pending: '{t("admin.blog.pending")}', spam: '{t("admin.blog.spam")}' }};
                        badge.style.background = colors[select.value];
                        badge.textContent = labels[select.value];
                    }} else {{
                        const data = await res.json();
                        showMsg('error', data.detail || 'Error');
                    }}
                }});
            }});

            // Delete button
            document.querySelectorAll('.delete-btn').forEach(btn => {{
                btn.addEventListener('click', async () => {{
                    if (!confirm('{t("admin.blog.delete_comment_confirm")}')) return;

                    const res = await fetch('/admin/blog/api/comments/' + btn.dataset.id, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }}
                    }});

                    if (res.ok) {{
                        btn.closest('tr').remove();
                        showMsg('success', '{t("messages.deleted")}');
                    }} else {{
                        const data = await res.json();
                        showMsg('error', data.detail || 'Error');
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================================
# REST API Endpoints
# ============================================================================


@blog_router.get("/api/posts")
async def api_list_posts(
    session=Depends(require_auth()),
):
    """List all blog posts."""
    from ..main import storage

    posts = storage.get("blog_posts", {})
    return {"posts": list(posts.values())}


@blog_router.post("/api/posts")
async def api_create_post(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Create a new blog post."""
    from ..main import storage, sanitizer, audit_logger

    data = await request.json()

    title = data.get("title", "Untitled")
    slug = sanitizer.slugify(title)

    # Check if slug exists
    if storage.get(f"blog_posts.{slug}"):
        # Add suffix
        counter = 1
        while storage.get(f"blog_posts.{slug}-{counter}"):
            counter += 1
        slug = f"{slug}-{counter}"

    now = datetime.now(timezone.utc).isoformat()

    # Validate language
    language = data.get("language", "both")
    if language not in ("en", "fa", "both"):
        language = "both"

    post = {
        "slug": slug,
        "title": title,
        "content": data.get("content", ""),
        "content_format": "html",
        "excerpt": data.get("excerpt", ""),
        "featured_image": data.get("featured_image"),
        "category": data.get("category"),
        "tags": data.get("tags", []),
        "author": session.user_id,
        "status": data.get("status", "draft"),
        "published_at": data.get("published_at"),
        "display_pages": data.get("display_pages", []),
        "comments_enabled": data.get("comments_enabled", True),
        "auto_approve_comments": data.get("auto_approve_comments", False),
        "created_at": now,
        "modified_at": now,
        "modified_by": session.user_id,
        "language": language,
        "associated_post": data.get("associated_post") or None,
    }

    storage.set(f"blog_posts.{slug}", post)

    audit_logger.log(
        "blog_post_create",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return post


@blog_router.get("/api/posts/{slug}")
async def api_get_post(
    slug: str,
    session=Depends(require_auth()),
):
    """Get a single blog post."""
    from ..main import storage

    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post


@blog_router.put("/api/posts/{slug}")
async def api_update_post(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a blog post."""
    from ..main import storage, audit_logger

    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    data = await request.json()

    post["title"] = data.get("title", post["title"])
    post["content"] = data.get("content", post["content"])
    post["excerpt"] = data.get("excerpt", post.get("excerpt", ""))
    post["featured_image"] = data.get("featured_image", post.get("featured_image"))
    post["category"] = data.get("category", post.get("category"))
    post["tags"] = data.get("tags", post.get("tags", []))
    post["status"] = data.get("status", post.get("status", "draft"))
    post["published_at"] = data.get("published_at", post.get("published_at"))
    post["display_pages"] = data.get("display_pages", post.get("display_pages", []))
    post["comments_enabled"] = data.get("comments_enabled", post.get("comments_enabled", True))
    post["auto_approve_comments"] = data.get("auto_approve_comments", post.get("auto_approve_comments", False))
    # Language settings
    language = data.get("language", post.get("language", "both"))
    if language in ("en", "fa", "both"):
        post["language"] = language
    else:
        post["language"] = "both"
    associated_post = data.get("associated_post", post.get("associated_post"))
    post["associated_post"] = associated_post if associated_post else None
    post["modified_at"] = datetime.now(timezone.utc).isoformat()
    post["modified_by"] = session.user_id

    storage.set(f"blog_posts.{slug}", post)

    audit_logger.log(
        "blog_post_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return post


@blog_router.delete("/api/posts/{slug}")
async def api_delete_post(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Delete a blog post."""
    from ..main import storage, audit_logger

    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Delete associated comments
    comments = storage.get("blog_comments", {})
    for comment_id, comment in list(comments.items()):
        if comment.get("post_slug") == slug:
            storage.delete(f"blog_comments.{comment_id}")

    storage.delete(f"blog_posts.{slug}")

    audit_logger.log(
        "blog_post_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return {"status": "deleted"}


# Categories API


@blog_router.get("/api/categories")
async def api_list_categories(
    session=Depends(require_auth()),
):
    """List all categories."""
    from ..main import storage

    categories = storage.get("blog_categories", {})
    return {"categories": list(categories.values())}


@blog_router.post("/api/categories")
async def api_create_category(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Create a new category."""
    from ..main import storage, sanitizer

    data = await request.json()

    name = data.get("name", "Untitled")
    slug = sanitizer.slugify(name)

    if storage.get(f"blog_categories.{slug}"):
        raise HTTPException(status_code=409, detail="Category already exists")

    # Validate language
    language = data.get("language", "both")
    if language not in ("en", "fa", "both"):
        language = "both"

    category = {
        "slug": slug,
        "name": name,
        "description": data.get("description", ""),
        "order": data.get("order", 0),
        "language": language,
        "associated_category": data.get("associated_category") or None,
    }

    storage.set(f"blog_categories.{slug}", category)

    return category


@blog_router.put("/api/categories/{slug}")
async def api_update_category(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a category."""
    from ..main import storage

    category = storage.get(f"blog_categories.{slug}")
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    data = await request.json()

    category["name"] = data.get("name", category["name"])
    category["description"] = data.get("description", category.get("description", ""))
    category["order"] = data.get("order", category.get("order", 0))
    # Language settings
    language = data.get("language", category.get("language", "both"))
    if language in ("en", "fa", "both"):
        category["language"] = language
    else:
        category["language"] = "both"
    associated_category = data.get("associated_category", category.get("associated_category"))
    category["associated_category"] = associated_category if associated_category else None

    storage.set(f"blog_categories.{slug}", category)

    return category


@blog_router.delete("/api/categories/{slug}")
async def api_delete_category(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Delete a category."""
    from ..main import storage

    category = storage.get(f"blog_categories.{slug}")
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Remove category from posts
    posts = storage.get("blog_posts", {})
    for post_slug, post in posts.items():
        if post.get("category") == slug:
            post["category"] = None
            storage.set(f"blog_posts.{post_slug}", post)

    storage.delete(f"blog_categories.{slug}")

    return {"status": "deleted"}


# Comments API


@blog_router.get("/api/comments")
async def api_list_comments(
    session=Depends(require_auth()),
):
    """List all comments."""
    from ..main import storage

    comments = storage.get("blog_comments", {})
    return {"comments": list(comments.values())}


@blog_router.put("/api/comments/{comment_id}")
async def api_update_comment(
    comment_id: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a comment (status only)."""
    from ..main import storage

    comment = storage.get(f"blog_comments.{comment_id}")
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    data = await request.json()

    if "status" in data:
        if data["status"] not in ["pending", "approved", "spam"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        comment["status"] = data["status"]

    storage.set(f"blog_comments.{comment_id}", comment)

    return comment


@blog_router.delete("/api/comments/{comment_id}")
async def api_delete_comment(
    comment_id: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Delete a comment."""
    from ..main import storage

    comment = storage.get(f"blog_comments.{comment_id}")
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    storage.delete(f"blog_comments.{comment_id}")

    return {"status": "deleted"}
