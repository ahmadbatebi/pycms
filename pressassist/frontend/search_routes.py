"""Frontend search routes for ChelCheleh."""

import html
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/search", tags=["search"])


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def get_excerpt(text: str, query: str, context_chars: int = 100) -> str:
    """Extract excerpt around the search query.

    Args:
        text: Full text content.
        query: Search query.
        context_chars: Characters to show before and after match.

    Returns:
        Excerpt with query highlighted.
    """
    if not text or not query:
        return text[:200] + "..." if text and len(text) > 200 else text or ""

    # Clean the text
    clean_text = strip_html_tags(text)

    # Find query position (case-insensitive)
    query_lower = query.lower()
    text_lower = clean_text.lower()

    pos = text_lower.find(query_lower)
    if pos == -1:
        # Query not found in this text, return beginning
        return clean_text[:200] + "..." if len(clean_text) > 200 else clean_text

    # Calculate start and end positions
    start = max(0, pos - context_chars)
    end = min(len(clean_text), pos + len(query) + context_chars)

    # Adjust to word boundaries
    if start > 0:
        space_pos = clean_text.rfind(" ", 0, start + 20)
        if space_pos > start - 30:
            start = space_pos + 1

    if end < len(clean_text):
        space_pos = clean_text.find(" ", end - 20)
        if space_pos != -1 and space_pos < end + 30:
            end = space_pos

    excerpt = clean_text[start:end]

    # Add ellipsis
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(clean_text):
        excerpt = excerpt + "..."

    return excerpt


def highlight_query(text: str, query: str) -> str:
    """Highlight search query in text.

    Args:
        text: Text to highlight in.
        query: Query to highlight.

    Returns:
        Text with query wrapped in <mark> tags.
    """
    if not text or not query:
        return text or ""

    # Escape HTML in text first
    escaped_text = html.escape(text)

    # Case-insensitive replacement with highlighting
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    highlighted = pattern.sub(lambda m: f"<mark>{html.escape(m.group())}</mark>", escaped_text)

    return highlighted


def search_in_text(text: str, query: str) -> bool:
    """Check if query exists in text (case-insensitive)."""
    if not text or not query:
        return False
    return query.lower() in strip_html_tags(text).lower()


def calculate_relevance(item: dict, query: str, item_type: str) -> float:
    """Calculate relevance score for search result.

    Args:
        item: The item to score.
        query: Search query.
        item_type: 'page' or 'post'.

    Returns:
        Relevance score (higher is better).
    """
    score = 0.0
    query_lower = query.lower()

    title = (item.get("title") or "").lower()
    content = strip_html_tags(item.get("content") or "").lower()
    description = (item.get("description") or item.get("excerpt") or "").lower()

    # Title match is most important
    if query_lower in title:
        score += 10.0
        # Exact title match
        if title == query_lower:
            score += 5.0
        # Title starts with query
        elif title.startswith(query_lower):
            score += 3.0

    # Description/excerpt match
    if query_lower in description:
        score += 5.0

    # Content match
    if query_lower in content:
        score += 2.0
        # Count occurrences (max 5 points)
        occurrences = content.count(query_lower)
        score += min(occurrences * 0.5, 5.0)

    # Keywords/tags match
    keywords = (item.get("keywords") or "").lower()
    tags = item.get("tags") or []
    if query_lower in keywords:
        score += 3.0
    for tag in tags:
        if query_lower in tag.lower():
            score += 2.0

    return score


@router.get("", response_class=JSONResponse)
@router.get("/", response_class=JSONResponse)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    type: str = Query("all", description="Search type: all, pages, blog"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Results per page"),
):
    """Search across site content.

    Returns matching pages and blog posts with excerpts and highlighting.
    """
    # Lazy imports to avoid circular imports
    from ..main import storage

    # Get search settings
    config = storage.get("config", {})

    # Check if search is enabled
    if not config.get("enable_search", True):
        raise HTTPException(status_code=403, detail="Search is disabled")

    # Check minimum query length
    min_chars = config.get("search_min_chars", 2)
    if len(q.strip()) < min_chars:
        return JSONResponse({
            "query": q,
            "results": [],
            "total": 0,
            "page": page,
            "total_pages": 0,
            "message": f"Query must be at least {min_chars} characters"
        })

    query = q.strip()
    max_results = config.get("search_max_results", 20)
    search_in_pages = config.get("search_in_pages", True)
    search_in_blog = config.get("search_in_blog", True)

    results: list[dict[str, Any]] = []

    # Search in pages
    if search_in_pages and type in ("all", "pages"):
        pages = storage.get("pages", {})
        for slug, page_data in pages.items():
            # Skip hidden pages
            if page_data.get("visibility") == "hide":
                continue

            # Search in title, content, description, keywords
            title = page_data.get("title", "")
            content = page_data.get("content", "")
            description = page_data.get("description", "")
            keywords = page_data.get("keywords", "")

            if (search_in_text(title, query) or
                search_in_text(content, query) or
                search_in_text(description, query) or
                search_in_text(keywords, query)):

                # Calculate relevance
                relevance = calculate_relevance(page_data, query, "page")

                # Get excerpt
                if search_in_text(content, query):
                    excerpt = get_excerpt(content, query)
                elif description:
                    excerpt = description[:200]
                else:
                    excerpt = strip_html_tags(content)[:200]

                results.append({
                    "type": "page",
                    "slug": slug,
                    "url": f"/{slug}",
                    "title": title,
                    "title_highlighted": highlight_query(title, query),
                    "excerpt": excerpt,
                    "excerpt_highlighted": highlight_query(excerpt, query),
                    "relevance": relevance,
                })

    # Search in blog posts
    if search_in_blog and type in ("all", "blog"):
        posts = storage.get("blog_posts", {})
        categories = storage.get("blog_categories", {})

        for slug, post_data in posts.items():
            # Only search published posts
            if post_data.get("status") != "published":
                continue

            title = post_data.get("title", "")
            content = post_data.get("content", "")
            excerpt_text = post_data.get("excerpt", "")
            tags = post_data.get("tags", [])
            category_slug = post_data.get("category", "")
            category_name = categories.get(category_slug, {}).get("name", "")

            # Search in title, content, excerpt, tags, category
            if (search_in_text(title, query) or
                search_in_text(content, query) or
                search_in_text(excerpt_text, query) or
                any(search_in_text(tag, query) for tag in tags) or
                search_in_text(category_name, query)):

                # Calculate relevance
                relevance = calculate_relevance(post_data, query, "post")

                # Get excerpt
                if search_in_text(content, query):
                    excerpt = get_excerpt(content, query)
                elif excerpt_text:
                    excerpt = excerpt_text[:200]
                else:
                    excerpt = strip_html_tags(content)[:200]

                results.append({
                    "type": "blog",
                    "slug": slug,
                    "url": f"/blog/{slug}",
                    "title": title,
                    "title_highlighted": highlight_query(title, query),
                    "excerpt": excerpt,
                    "excerpt_highlighted": highlight_query(excerpt, query),
                    "category": category_name,
                    "tags": tags,
                    "featured_image": post_data.get("featured_image"),
                    "published_at": post_data.get("published_at"),
                    "author": post_data.get("author"),
                    "relevance": relevance,
                })

    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)

    # Limit total results
    results = results[:max_results]

    # Pagination
    total = len(results)
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_results = results[start_idx:end_idx]

    # Remove relevance score from output (internal use only)
    for r in paginated_results:
        del r["relevance"]

    return JSONResponse({
        "query": query,
        "results": paginated_results,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    })


@router.get("/suggest", response_class=JSONResponse)
async def search_suggest(
    request: Request,
    q: str = Query(..., min_length=1, max_length=50, description="Query prefix"),
):
    """Get search suggestions based on query prefix.

    Returns titles that start with or contain the query.
    """
    from ..main import storage

    config = storage.get("config", {})

    if not config.get("enable_search", True):
        return JSONResponse({"suggestions": []})

    query = q.strip().lower()
    if len(query) < 2:
        return JSONResponse({"suggestions": []})

    suggestions: list[dict[str, str]] = []

    # Suggest from pages
    if config.get("search_in_pages", True):
        pages = storage.get("pages", {})
        for slug, page_data in pages.items():
            if page_data.get("visibility") == "hide":
                continue
            title = page_data.get("title", "")
            if query in title.lower():
                suggestions.append({
                    "title": title,
                    "url": f"/{slug}",
                    "type": "page",
                })

    # Suggest from blog posts
    if config.get("search_in_blog", True):
        posts = storage.get("blog_posts", {})
        for slug, post_data in posts.items():
            if post_data.get("status") != "published":
                continue
            title = post_data.get("title", "")
            if query in title.lower():
                suggestions.append({
                    "title": title,
                    "url": f"/blog/{slug}",
                    "type": "blog",
                })

    # Sort: titles starting with query first, then alphabetically
    suggestions.sort(key=lambda x: (
        not x["title"].lower().startswith(query),
        x["title"].lower()
    ))

    # Limit to 8 suggestions
    suggestions = suggestions[:8]

    return JSONResponse({"suggestions": suggestions})
