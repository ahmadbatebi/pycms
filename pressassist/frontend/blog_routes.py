"""Blog frontend routes for ChelCheleh."""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..core.csrf import get_csrf_token
from ..core.i18n import t
from ..core.language_middleware import (
    get_language_from_request,
    get_direction_from_request,
)
from ..core.languages import get_available_languages
from ..core.themes import jalali_date

blog_frontend_router = APIRouter(prefix="/blog", tags=["blog"])


def get_filtered_menu(storage, current_lang: str, session) -> list:
    """Get menu items filtered by visibility and language.

    Args:
        storage: Storage instance.
        current_lang: Current language code.
        session: User session (None if not logged in).

    Returns:
        List of visible menu items for the current language.
    """
    menu_items = storage.get("menu_items", [])
    visible_menu = []
    for item in menu_items:
        # Check visibility
        if item.get("visibility") != "show" and not session:
            continue
        # Check menu item's own language setting
        item_lang = item.get("language", "both")
        if item_lang != "both" and item_lang != current_lang and not session:
            continue
        # Also check language of the linked page
        page_slug = item.get("slug")
        if page_slug:
            linked_page = storage.get(f"pages.{page_slug}")
            if linked_page:
                page_lang = linked_page.get("language", "both")
                if page_lang != "both" and page_lang != current_lang and not session:
                    continue
        visible_menu.append(item)
    return visible_menu


def get_blog_posts_for_page(
    storage, page_slug: str, limit: int = 10, offset: int = 0, current_lang: str = None
) -> tuple[list, int]:
    """Get published blog posts that should appear on a specific page.

    Args:
        storage: Storage instance.
        page_slug: Slug of the page to filter by.
        limit: Maximum number of posts to return.
        offset: Number of posts to skip (for pagination).
        current_lang: Current language code to filter posts by.

    Returns:
        Tuple of (list of posts for current page, total count of matching posts).
    """
    posts = storage.get("blog_posts", {})
    now = datetime.now(timezone.utc)

    # Filter published posts that include this page
    filtered = []
    for post in posts.values():
        if post.get("status") != "published":
            continue

        # Check if scheduled for future
        published_at = post.get("published_at")
        if published_at:
            try:
                # Handle various date formats
                if "T" in published_at:
                    # ISO format - might be with or without timezone
                    if "+" in published_at or "Z" in published_at:
                        pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    else:
                        # No timezone, assume local and add UTC
                        pub_dt = datetime.fromisoformat(published_at).replace(tzinfo=timezone.utc)
                else:
                    # Just date
                    pub_dt = datetime.fromisoformat(published_at + "T00:00:00").replace(tzinfo=timezone.utc)

                if pub_dt > now:
                    continue  # Scheduled for future
            except (ValueError, TypeError):
                pass  # Invalid date format, include the post

        # Check if this page is in display_pages
        display_pages = post.get("display_pages", [])
        if page_slug not in display_pages:
            continue

        # Check language visibility
        if current_lang:
            post_lang = post.get("language", "both")
            if post_lang != "both" and post_lang != current_lang:
                continue

        filtered.append(post)

    # Sort by published_at descending
    filtered.sort(key=lambda p: p.get("published_at") or p.get("created_at") or "", reverse=True)

    total = len(filtered)
    return filtered[offset:offset + limit], total


def get_all_published_posts(storage, limit: int = 100, offset: int = 0, category: str = None, tag: str = None, current_lang: str = None) -> tuple:
    """Get all published blog posts with optional filtering.

    Args:
        storage: Storage instance.
        limit: Maximum number of posts.
        offset: Number of posts to skip.
        category: Optional category slug to filter by.
        tag: Optional tag to filter by.
        current_lang: Current language code to filter posts by.

    Returns:
        Tuple of (posts list, total count).
    """
    posts = storage.get("blog_posts", {})
    now = datetime.now(timezone.utc).isoformat()

    # Filter published posts
    filtered = []
    for post in posts.values():
        if post.get("status") != "published":
            continue
        published_at = post.get("published_at")
        if published_at and published_at > now:
            continue

        # Category filter
        if category and post.get("category") != category:
            continue

        # Tag filter
        if tag and tag.lower() not in [t.lower() for t in post.get("tags", [])]:
            continue

        # Language filter
        if current_lang:
            post_lang = post.get("language", "both")
            if post_lang != "both" and post_lang != current_lang:
                continue

        filtered.append(post)

    # Sort by published_at descending
    filtered.sort(key=lambda p: p.get("published_at") or p.get("created_at") or "", reverse=True)

    total = len(filtered)
    return filtered[offset:offset + limit], total


def get_approved_comments(storage, post_slug: str) -> list:
    """Get approved comments for a post.

    Args:
        storage: Storage instance.
        post_slug: Slug of the post.

    Returns:
        List of approved comments, sorted by date ascending.
    """
    comments = storage.get("blog_comments", {})
    filtered = [
        c for c in comments.values()
        if c.get("post_slug") == post_slug and c.get("status") == "approved"
    ]
    filtered.sort(key=lambda c: c.get("created_at", ""))
    return filtered


@blog_frontend_router.get("", response_class=HTMLResponse)
@blog_frontend_router.get("/", response_class=HTMLResponse)
async def blog_archive(
    request: Request,
    page: int = 1,
):
    """Render blog archive page."""
    from ..main import storage, sanitizer, theme_manager, get_session

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    session = await get_session(request)
    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    per_page = 10
    offset = (page - 1) * per_page

    posts, total = get_all_published_posts(storage, limit=per_page, offset=offset, current_lang=current_lang)
    categories = storage.get("blog_categories", {})
    uploads = storage.get("uploads", {})

    # Get menu items (filtered by language)
    visible_menu = get_filtered_menu(storage, current_lang, session)

    # Build post cards
    def get_image_url(uuid_str):
        if not uuid_str:
            return None
        upload = uploads.get(uuid_str)
        if upload:
            ext = upload.get("mime_type", "").split("/")[-1]
            return f"/uploads/{uuid_str}"
        return None

    def get_category_name(cat_slug):
        cat = categories.get(cat_slug, {})
        return cat.get("name", "") if cat_slug else ""

    total_pages = (total + per_page - 1) // per_page

    # Get blocks
    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        # Skip disabled blocks
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    # Build HTML for blog archive
    posts_html = ""
    for post in posts:
        image_url = get_image_url(post.get("featured_image"))
        cat_name = get_category_name(post.get("category"))
        excerpt = post.get("excerpt", "")[:200]
        if not excerpt and post.get("content"):
            # Strip HTML and truncate
            import re
            text = re.sub(r"<[^>]+>", "", post.get("content", ""))
            excerpt = text[:200] + "..." if len(text) > 200 else text

        posts_html += f'''
        <article class="blog-post-card">
            {f'<img src="{image_url}" alt="" class="post-thumbnail">' if image_url else ''}
            <div class="post-content">
                {f'<span class="post-category">{cat_name}</span>' if cat_name else ''}
                <h2><a href="/blog/{post.get("slug", "")}">{post.get("title", "")}</a></h2>
                <p class="post-excerpt">{excerpt}</p>
                <div class="post-meta">
                    <span class="post-date">{jalali_date(post.get("published_at") or post.get("created_at") or "", current_lang)}</span>
                    <span class="post-author">{post.get("author", "")}</span>
                </div>
            </div>
        </article>
        '''

    # Pagination
    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        if page > 1:
            pagination_html += f'<a href="/blog?page={page - 1}">&laquo; {t("frontend.blog.prev")}</a>'
        for p in range(1, total_pages + 1):
            if p == page:
                pagination_html += f'<span class="current">{p}</span>'
            else:
                pagination_html += f'<a href="/blog?page={p}">{p}</a>'
        if page < total_pages:
            pagination_html += f'<a href="/blog?page={page + 1}">{t("frontend.blog.next")} &raquo;</a>'
        pagination_html += '</div>'

    # Categories sidebar
    cat_list_html = ""
    for cat in sorted(categories.values(), key=lambda c: c.get("order", 0)):
        cat_list_html += f'<li><a href="/blog/category/{cat.get("slug", "")}">{cat.get("name", "")}</a></li>'

    content_html = f'''
    <div class="blog-archive">
        <div class="blog-main">
            <h1>{t("frontend.blog.title")}</h1>
            <div class="blog-posts">
                {posts_html if posts_html else f'<p class="no-posts">{t("frontend.blog.no_posts")}</p>'}
            </div>
            {pagination_html}
        </div>
        <aside class="blog-sidebar">
            <h3>{t("frontend.categories")}</h3>
            <ul class="category-list">
                {cat_list_html}
            </ul>
        </aside>
    </div>
    '''

    from ..core.themes import CMSContext

    context = CMSContext(
        site_title=storage.get("config.site_title", "My Website"),
        site_lang=storage.get("config.site_lang", "en"),
        theme=storage.get("config.theme", "default"),
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        page_title=t("frontend.blog.title"),
        page_slug="blog",
        page_content=content_html,
        page_description=t("frontend.blog.description"),
        page_keywords="blog",
        page_template=storage.get("config.default_template", "default"),
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default').lower()}/static",
    )

    html = theme_manager.render_page(context)
    return HTMLResponse(html)


@blog_frontend_router.get("/category/{slug}", response_class=HTMLResponse)
async def blog_category(
    request: Request,
    slug: str,
    page: int = 1,
):
    """Render posts in a specific category."""
    from ..main import storage, sanitizer, theme_manager, get_session

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    session = await get_session(request)
    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    category = storage.get(f"blog_categories.{slug}")
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check category language visibility
    cat_lang = category.get("language", "both")
    if cat_lang != "both" and cat_lang != current_lang and not session:
        raise HTTPException(status_code=404, detail="Category not found")

    per_page = 10
    offset = (page - 1) * per_page

    posts, total = get_all_published_posts(storage, limit=per_page, offset=offset, category=slug, current_lang=current_lang)
    categories = storage.get("blog_categories", {})
    uploads = storage.get("uploads", {})

    # Get menu items (filtered by language)
    visible_menu = get_filtered_menu(storage, current_lang, session)

    def get_image_url(uuid_str):
        if not uuid_str:
            return None
        upload = uploads.get(uuid_str)
        return f"/uploads/{uuid_str}" if upload else None

    total_pages = (total + per_page - 1) // per_page

    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    posts_html = ""
    for post in posts:
        image_url = get_image_url(post.get("featured_image"))
        excerpt = post.get("excerpt", "")[:200]
        if not excerpt and post.get("content"):
            import re
            text = re.sub(r"<[^>]+>", "", post.get("content", ""))
            excerpt = text[:200] + "..." if len(text) > 200 else text

        posts_html += f'''
        <article class="blog-post-card">
            {f'<img src="{image_url}" alt="" class="post-thumbnail">' if image_url else ''}
            <div class="post-content">
                <h2><a href="/blog/{post.get("slug", "")}">{post.get("title", "")}</a></h2>
                <p class="post-excerpt">{excerpt}</p>
                <div class="post-meta">
                    <span class="post-date">{jalali_date(post.get("published_at") or post.get("created_at") or "", current_lang)}</span>
                </div>
            </div>
        </article>
        '''

    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        if page > 1:
            pagination_html += f'<a href="/blog/category/{slug}?page={page - 1}">&laquo;</a>'
        for p in range(1, total_pages + 1):
            if p == page:
                pagination_html += f'<span class="current">{p}</span>'
            else:
                pagination_html += f'<a href="/blog/category/{slug}?page={p}">{p}</a>'
        if page < total_pages:
            pagination_html += f'<a href="/blog/category/{slug}?page={page + 1}">&raquo;</a>'
        pagination_html += '</div>'

    content_html = f'''
    <div class="blog-archive">
        <div class="blog-main">
            <h1>{t("frontend.blog.category")}: {category.get("name", slug)}</h1>
            <div class="blog-posts">
                {posts_html if posts_html else f'<p class="no-posts">{t("frontend.blog.no_posts")}</p>'}
            </div>
            {pagination_html}
        </div>
    </div>
    '''

    from ..core.themes import CMSContext

    context = CMSContext(
        site_title=storage.get("config.site_title", "My Website"),
        site_lang=storage.get("config.site_lang", "en"),
        theme=storage.get("config.theme", "default"),
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        page_title=f'{t("frontend.blog.category")}: {category.get("name", slug)}',
        page_slug="blog",
        page_content=content_html,
        page_description=category.get("description", ""),
        page_keywords="",
        page_template=storage.get("config.default_template", "default"),
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default').lower()}/static",
    )

    html = theme_manager.render_page(context)
    return HTMLResponse(html)


@blog_frontend_router.get("/tag/{tag}", response_class=HTMLResponse)
async def blog_tag(
    request: Request,
    tag: str,
    page: int = 1,
):
    """Render posts with a specific tag."""
    from ..main import storage, sanitizer, theme_manager, get_session

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    session = await get_session(request)
    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    per_page = 10
    offset = (page - 1) * per_page

    posts, total = get_all_published_posts(storage, limit=per_page, offset=offset, tag=tag, current_lang=current_lang)
    uploads = storage.get("uploads", {})

    # Get menu items (filtered by language)
    visible_menu = get_filtered_menu(storage, current_lang, session)

    def get_image_url(uuid_str):
        if not uuid_str:
            return None
        upload = uploads.get(uuid_str)
        return f"/uploads/{uuid_str}" if upload else None

    total_pages = (total + per_page - 1) // per_page

    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    posts_html = ""
    for post in posts:
        image_url = get_image_url(post.get("featured_image"))
        excerpt = post.get("excerpt", "")[:200]
        if not excerpt and post.get("content"):
            import re
            text = re.sub(r"<[^>]+>", "", post.get("content", ""))
            excerpt = text[:200] + "..." if len(text) > 200 else text

        posts_html += f'''
        <article class="blog-post-card">
            {f'<img src="{image_url}" alt="" class="post-thumbnail">' if image_url else ''}
            <div class="post-content">
                <h2><a href="/blog/{post.get("slug", "")}">{post.get("title", "")}</a></h2>
                <p class="post-excerpt">{excerpt}</p>
                <div class="post-meta">
                    <span class="post-date">{jalali_date(post.get("published_at") or post.get("created_at") or "", current_lang)}</span>
                </div>
            </div>
        </article>
        '''

    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        if page > 1:
            pagination_html += f'<a href="/blog/tag/{tag}?page={page - 1}">&laquo;</a>'
        for p in range(1, total_pages + 1):
            if p == page:
                pagination_html += f'<span class="current">{p}</span>'
            else:
                pagination_html += f'<a href="/blog/tag/{tag}?page={p}">{p}</a>'
        if page < total_pages:
            pagination_html += f'<a href="/blog/tag/{tag}?page={page + 1}">&raquo;</a>'
        pagination_html += '</div>'

    content_html = f'''
    <div class="blog-archive">
        <div class="blog-main">
            <h1>{t("frontend.blog.tag")}: {tag}</h1>
            <div class="blog-posts">
                {posts_html if posts_html else f'<p class="no-posts">{t("frontend.blog.no_posts")}</p>'}
            </div>
            {pagination_html}
        </div>
    </div>
    '''

    from ..core.themes import CMSContext

    context = CMSContext(
        site_title=storage.get("config.site_title", "My Website"),
        site_lang=storage.get("config.site_lang", "en"),
        theme=storage.get("config.theme", "default"),
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        page_title=f'{t("frontend.blog.tag")}: {tag}',
        page_slug="blog",
        page_content=content_html,
        page_description="",
        page_keywords=tag,
        page_template=storage.get("config.default_template", "default"),
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default').lower()}/static",
    )

    html = theme_manager.render_page(context)
    return HTMLResponse(html)


@blog_frontend_router.get("/{slug}", response_class=HTMLResponse)
async def blog_post(
    request: Request,
    slug: str,
):
    """Render a single blog post."""
    from ..main import storage, sanitizer, theme_manager, get_session

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if published
    session = await get_session(request)
    if post.get("status") != "published" and not session:
        raise HTTPException(status_code=404, detail="Post not found")

    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    # Check language visibility
    post_lang = post.get("language", "both")
    if post_lang != "both" and post_lang != current_lang and not session:
        raise HTTPException(status_code=404, detail="Post not found")

    categories = storage.get("blog_categories", {})
    uploads = storage.get("uploads", {})

    # Get menu items (filtered by language)
    visible_menu = get_filtered_menu(storage, current_lang, session)

    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    # Get featured image
    def get_image_url(uuid_str):
        if not uuid_str:
            return None
        upload = uploads.get(uuid_str)
        return f"/uploads/{uuid_str}" if upload else None

    image_url = get_image_url(post.get("featured_image"))

    # Get category
    category = categories.get(post.get("category", ""), {})
    cat_html = ""
    if category:
        cat_html = f'<a href="/blog/category/{category.get("slug", "")}" class="post-category">{category.get("name", "")}</a>'

    # Get associated post link (other language version)
    associated_link_html = ""
    associated_post_slug = post.get("associated_post")
    if associated_post_slug:
        associated_post_data = storage.get(f"blog_posts.{associated_post_slug}")
        if associated_post_data and associated_post_data.get("status") == "published":
            associated_lang = associated_post_data.get("language", "both")
            if associated_lang == "en" or (associated_lang == "both" and current_lang == "fa"):
                link_text = t("admin.blog.english_version")
            else:
                link_text = t("admin.blog.persian_version")
            associated_link_html = f'<a href="/blog/{associated_post_slug}" class="language-version-link">{link_text}</a>'

    # Get tags
    tags_html = ""
    if post.get("tags"):
        tags_html = '<div class="post-tags">'
        for tag in post.get("tags", []):
            tags_html += f'<a href="/blog/tag/{tag}" class="tag">{tag}</a>'
        tags_html += '</div>'

    # Get comments
    comments = get_approved_comments(storage, slug)
    comments_html = ""
    if post.get("comments_enabled", True):
        comments_html = f'<section class="comments-section"><h3>{t("frontend.blog.comments")} ({len(comments)})</h3>'

        if comments:
            for comment in comments:
                comments_html += f'''
                <div class="comment">
                    <div class="comment-author">{comment.get("author_name", "")}</div>
                    <div class="comment-date">{jalali_date(comment.get("created_at", ""), current_lang)}</div>
                    <div class="comment-content">{comment.get("content", "")}</div>
                </div>
                '''
        else:
            comments_html += f'<p class="no-comments">{t("frontend.blog.no_comments")}</p>'

        # Comment form
        csrf_token = get_csrf_token(request)
        comments_html += f'''
        <div class="comment-form">
            <h4>{t("frontend.blog.leave_comment")}</h4>
            <form method="post" action="/blog/{slug}/comment">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <div class="form-row">
                    <label>{t("frontend.blog.your_name")}</label>
                    <input type="text" name="author_name" required>
                </div>
                <div class="form-row">
                    <label>{t("frontend.blog.your_email")}</label>
                    <input type="email" name="author_email" required>
                </div>
                <div class="form-row">
                    <label>{t("frontend.blog.your_comment")}</label>
                    <textarea name="content" required rows="4"></textarea>
                </div>
                <button type="submit" class="btn">{t("frontend.blog.submit")}</button>
            </form>
        </div>
        '''
        comments_html += '</section>'

    # Render post content
    post_content = sanitizer.render_content(post.get("content", ""), post.get("content_format", "html"))

    content_html = f'''
    <article class="blog-single-post">
        {f'<img src="{image_url}" alt="" class="featured-image">' if image_url else ''}
        <header class="post-header">
            {cat_html}
            <h1>{post.get("title", "")}</h1>
            <div class="post-meta">
                <span class="post-date">{jalali_date(post.get("published_at") or post.get("created_at") or "", current_lang)}</span>
                <span class="post-author">{t("frontend.blog.by")} {post.get("author", "")}</span>
                {associated_link_html}
            </div>
        </header>
        <div class="post-body">
            {post_content}
        </div>
        {tags_html}
        {comments_html}
    </article>
    '''

    from ..core.themes import CMSContext

    context = CMSContext(
        site_title=storage.get("config.site_title", "My Website"),
        site_lang=storage.get("config.site_lang", "en"),
        theme=storage.get("config.theme", "default"),
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        page_title=post.get("title", ""),
        page_slug=f"blog/{slug}",
        page_content=content_html,
        page_description=post.get("excerpt", ""),
        page_keywords=", ".join(post.get("tags", [])),
        page_template=storage.get("config.default_template", "default"),
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default').lower()}/static",
    )

    html = theme_manager.render_page(context)
    return HTMLResponse(html)


@blog_frontend_router.post("/{slug}/comment")
async def submit_comment(
    request: Request,
    slug: str,
    author_name: str = Form(...),
    author_email: str = Form(...),
    content: str = Form(...),
    csrf_token: str = Form(...),
):
    """Submit a comment on a blog post."""
    from ..main import storage

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    # Verify CSRF token (constant-time comparison to prevent timing attacks)
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not cookie_csrf or not csrf_token or not secrets.compare_digest(csrf_token, cookie_csrf):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    # Get post
    post = storage.get(f"blog_posts.{slug}")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if comments enabled
    if not post.get("comments_enabled", True):
        raise HTTPException(status_code=403, detail="Comments are disabled")

    # Basic validation
    import re
    import bleach

    author_name = bleach.clean(author_name.strip(), tags=[], strip=True)[:100]
    author_email = author_email.strip().lower()[:200]
    content = bleach.clean(content.strip(), tags=[], strip=True)[:2000]

    if not author_name or not author_email or not content:
        raise HTTPException(status_code=400, detail="All fields are required")

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", author_email):
        raise HTTPException(status_code=400, detail="Invalid email")

    # Create comment
    # Check if auto-approve is enabled for this post
    auto_approve = post.get("auto_approve_comments", False)
    comment_status = "approved" if auto_approve else "pending"

    comment_id = str(uuid.uuid4())
    comment = {
        "id": comment_id,
        "post_slug": slug,
        "author_name": author_name,
        "author_email": author_email,
        "content": content,
        "status": comment_status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    storage.set(f"blog_comments.{comment_id}", comment)

    # Redirect back to post with message
    return RedirectResponse(
        url=f"/blog/{slug}?comment={comment_status}",
        status_code=303,
    )
