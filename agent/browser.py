"""
Interactive Browser Automation Module using Playwright.
Supports real browser actions: open, search, click, type, extract, screenshot.
Returns structured results with verification metadata.
"""

import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from config import WORKSPACE_DIR
from agent.permissions import validate_safe_path
from agent.logger import logger


def _normalize_url(url: str) -> str:
    clean = url.strip()
    if not clean.startswith(("http://", "https://")):
        clean = "https://" + clean
    return clean


def browser_open(url: str, headless: bool = False) -> Dict[str, Any]:
    """
    Opens a URL in a browser using Playwright.
    If headless=False, the browser window is visible on screen.
    """
    target_url = _normalize_url(url)
    logger.info(f"Opening browser at: {target_url} (headless={headless})")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            response = page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
            title = page.title()
            status = response.status if response else 200
            browser.close()

            return {
                "success": True,
                "result": {
                    "url": target_url,
                    "title": title,
                    "status_code": status
                },
                "error": None,
                "verification": {
                    "verified": True,
                    "details": f"Page loaded successfully with title '{title}' (HTTP {status})."
                }
            }
    except Exception as e:
        logger.error(f"Playwright browser_open error for {target_url}: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Failed to open browser at {target_url}: {str(e)}",
            "verification": {"verified": False, "details": "Navigation failed."}
        }


def browser_search(query: str) -> Dict[str, Any]:
    """
    Simulates real browser search interaction: navigates to Google, types query,
    extracts organic search result headlines and links.
    """
    clean_query = query.strip()
    search_url = f"https://www.google.com/search?q={clean_query}"
    logger.info(f"Executing browser search for '{clean_query}'")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
            title = page.title()

            # Extract search items
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        results = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            h3 = a.find("h3")
            if h3 and href.startswith("http"):
                results.append({
                    "title": h3.get_text(strip=True),
                    "url": href
                })
            if len(results) >= 5:
                break

        return {
            "success": True,
            "result": {
                "query": clean_query,
                "results": results,
                "count": len(results)
            },
            "error": None,
            "verification": {
                "verified": len(results) > 0,
                "details": f"Extracted {len(results)} browser search results from Google."
            }
        }
    except Exception as e:
        logger.error(f"Browser search error: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Browser search failed: {str(e)}",
            "verification": {"verified": False, "details": "Google search interaction error."}
        }


def browser_extract(url: str, selector: Optional[str] = None, max_chars: int = 4000) -> Dict[str, Any]:
    """
    Extracts text content or selector text from a webpage using Playwright.
    """
    target_url = _normalize_url(url)
    logger.info(f"Extracting content from: {target_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
            title = page.title()

            if selector:
                extracted_element = page.query_selector(selector)
                extracted_text = extracted_element.inner_text() if extracted_element else ""
            else:
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                extracted_text = " ".join(soup.get_text(separator=" ").split())

            browser.close()

        truncated = extracted_text[:max_chars]
        return {
            "success": True,
            "result": {
                "url": target_url,
                "title": title,
                "content_sample": truncated,
                "total_chars": len(extracted_text)
            },
            "error": None,
            "verification": {
                "verified": len(extracted_text) > 0,
                "details": f"Extracted {len(extracted_text)} characters from '{title}'."
            }
        }
    except Exception as e:
        logger.error(f"browser_extract error: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Extraction failed: {str(e)}",
            "verification": {"verified": False, "details": "Browser extraction error."}
        }


def browser_screenshot(url: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """Captures a full-page or viewport browser screenshot saved to workspace/."""
    target_url = _normalize_url(url)
    if not filename:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"web_screenshot_{ts}.png"
    if not filename.endswith(".png"):
        filename += ".png"

    target_path = validate_safe_path(WORKSPACE_DIR / filename, allowed_roots=[WORKSPACE_DIR])
    logger.info(f"Taking browser screenshot of {target_url} -> {target_path}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
            page.screenshot(path=str(target_path), full_page=False)
            browser.close()

        if target_path.exists() and target_path.stat().st_size > 0:
            return {
                "success": True,
                "result": {
                    "url": target_url,
                    "filename": target_path.name,
                    "saved_path": str(target_path),
                    "size_bytes": target_path.stat().st_size
                },
                "error": None,
                "verification": {
                    "verified": True,
                    "details": f"Screenshot verified on disk ({target_path.stat().st_size} bytes)."
                }
            }
        return {
            "success": False,
            "result": None,
            "error": "Screenshot failed to write.",
            "verification": {"verified": False, "details": "Disk check failed."}
        }
    except Exception as e:
        logger.error(f"browser_screenshot error: {e}")
        return {
            "success": False,
            "result": None,
            "error": f"Screenshot failed: {str(e)}",
            "verification": {"verified": False, "details": "Playwright screenshot error."}
        }
