#!/usr/bin/env python3
"""
medium-to-md.py — Convert any Medium article to Markdown with embedded or local images.

Usage:
    /opt/anaconda3/envs/python_313x/bin/python medium-to-md.py https://gillesdemaneuf.medium.com/the-emi-fix-8be2313448b4 [--disk] [--debug] [output_dir]

Options:
    --disk      Save images to disk instead of embedding as base64 in markdown (default: embed)
    --debug     Print debug information during extraction
    output_dir  Output directory (default: current directory)

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import sys
import os
import re
import base64
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Missing playwright. Install: pip install playwright && playwright install chromium")
    sys.exit(1)


async def fetch_resource(page, url: str) -> bytes:
    """Fetch resource content using Playwright's request handling."""
    try:
        response = await page.context.request.fetch(url)
        if response.ok:
            return await response.body()
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url[:60]}: {e}", file=sys.stderr)
    return b""


async def image_to_base64(page, img_url: str) -> str:
    """Convert image to base64 data URL."""
    content = await fetch_resource(page, img_url)
    if not content:
        return ""

    # Detect MIME type from URL or default
    if ".webp" in img_url:
        mime = "image/webp"
    elif ".png" in img_url:
        mime = "image/png"
    elif ".gif" in img_url:
        mime = "image/gif"
    elif ".svg" in img_url:
        mime = "image/svg+xml"
    else:
        mime = "image/jpeg"

    b64 = base64.b64encode(content).decode("utf-8")
    return f"data:{mime};base64,{b64}"


async def save_image_to_disk(page, img_url: str, img_dir: Path, index: int) -> str:
    """Download an image and save to disk."""
    content = await fetch_resource(page, img_url)
    if not content:
        return ""

    # Detect extension from content-type or URL
    if ".webp" in img_url:
        ext = ".webp"
    elif ".png" in img_url:
        ext = ".png"
    elif ".gif" in img_url:
        ext = ".gif"
    elif ".svg" in img_url:
        ext = ".svg"
    else:
        ext = ".jpg"

    filename = f"img_{index:04d}{ext}"
    filepath = img_dir / filename
    filepath.write_bytes(content)
    return str(filepath)


async def medium_to_markdown(url: str, output_dir: str = ".", embed_images: bool = True, debug: bool = False) -> str:
    """
    Extract a Medium article to Markdown with images.

    Args:
        url: Medium article URL
        output_dir: Output directory
        embed_images: If True, embed images as base64. If False, save to disk.
        debug: If True, print debug information during extraction
    """
    slug = url.rstrip("/").split("/")[-1] or "article"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    img_dir = None
    if not embed_images:
        img_dir = output_path / f"{slug}_images"
        img_dir.mkdir(exist_ok=True)

    print(f"Converting: {url}", file=sys.stderr)
    print(f"Output dir: {output_path}", file=sys.stderr)
    print(f"Mode: {'Embedded (base64)' if embed_images else 'Disk'}", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # Block font/stylesheet resources for speed
        async def block_resources(route):
            if route.request.resource_type in ["font", "stylesheet", "media", "image"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resources)
        # But allow images from miro.medium.com
        await page.route("https://miro.medium.com/*", lambda route: route.continue_())

        print("  Loading page...", file=sys.stderr)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for article to render
        try:
            await page.wait_for_selector("article", timeout=15000)
        except Exception:
            print("  Warning: No <article> tag found.", file=sys.stderr)

        print("  Extracting content...", file=sys.stderr)

        # Give Medium a moment to render images
        await page.wait_for_timeout(2000)

        if debug:
            print("  [DEBUG] Checking page selectors...", file=sys.stderr)

        # Extract content with image positions preserved
        result = await page.evaluate("""
        () => {
            const article = document.querySelector('article');
            if (!article) {
                return { blocks: [], debug: { articleFound: false } };
            }

            const blocks = [];
            let imgIndex = 0;
            const processedElements = new Set();

            // Recursively walk through all children, preserving order
            function walkElement(el) {
                if (processedElements.has(el)) return;

                const tagName = el.tagName.toLowerCase();

                // Skip wrapper/container divs, but process their children
                if (tagName === 'div' || tagName === 'section' || tagName === 'header' || tagName === 'footer') {
                    for (const child of el.children) {
                        walkElement(child);
                    }
                    return;
                }

                // Handle figures (Medium's image containers)
                if (tagName === 'figure') {
                    const img = el.querySelector('img');
                    if (img) {
                        let src = img.getAttribute('src') || '';
                        const srcset = img.getAttribute('srcset');
                        if (srcset) {
                            const sources = srcset.split(',')
                                .map(s => s.trim().split(' ')[0])
                                .filter(s => s.includes('miro.medium.com'));
                            if (sources.length > 0) {
                                src = sources[sources.length - 1];
                            }
                        }
                        if (src && src.startsWith('http')) {
                            blocks.push({ type: 'image', src: src, index: imgIndex++ });
                        }
                    }

                    // Check for figcaption
                    const caption = el.querySelector('figcaption');
                    if (caption) {
                        const captionText = caption.innerText.trim();
                        if (captionText) {
                            blocks.push({ type: 'figcaption', text: captionText });
                        }
                    }

                    processedElements.add(el);
                    return;
                }

                // Handle headings
                if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
                    const text = el.innerText.trim();
                    if (text) {
                        blocks.push({ type: tagName, text: text });
                        processedElements.add(el);
                    }
                    return;
                }

                // Handle paragraphs
                if (tagName === 'p') {
                    const text = el.innerText.trim();
                    if (text && text.length > 0) {
                        blocks.push({ type: 'p', text: text });
                        processedElements.add(el);
                    }
                    return;
                }

                // Handle blockquotes
                if (tagName === 'blockquote') {
                    const text = el.innerText.trim();
                    if (text) {
                        blocks.push({ type: 'blockquote', text: text });
                        processedElements.add(el);
                    }
                    return;
                }

                // Handle lists
                if (tagName === 'ul' || tagName === 'ol') {
                    const items = Array.from(el.querySelectorAll(':scope > li'))
                        .map(li => li.innerText.trim())
                        .filter(t => t);
                    if (items.length > 0) {
                        blocks.push({ type: tagName, items: items });
                        processedElements.add(el);
                    }
                    return;
                }

                // Handle code blocks
                if (tagName === 'pre') {
                    const text = el.innerText.trim();
                    if (text) {
                        blocks.push({ type: 'pre', text: text });
                        processedElements.add(el);
                    }
                    return;
                }

                // For unknown container elements, recurse into children
                for (const child of el.children) {
                    walkElement(child);
                }
            }

            walkElement(article);

            return { blocks: blocks, debug: { articleFound: true, blockCount: blocks.length } };
        }
        """)

        blocks = result["blocks"]

        if debug:
            print(f"  [DEBUG] Extracted {len(blocks)} blocks", file=sys.stderr)
            # Show first few blocks
            for i, block in enumerate(blocks[:5]):
                print(f"    Block {i}: type={block.get('type')}, content={str(block).[:80]}", file=sys.stderr)

        # Convert blocks to markdown, processing images
        md_parts = []
        img_count = 0

        for block in blocks:
            block_type = block.get("type")

            if block_type == "h1":
                md_parts.append(f"# {block['text']}")
            elif block_type == "h2":
                md_parts.append(f"## {block['text']}")
            elif block_type in ["h3", "h4", "h5", "h6"]:
                md_parts.append(f"### {block['text']}")
            elif block_type == "p":
                md_parts.append(block['text'])
            elif block_type == "blockquote":
                lines = block['text'].split('\n')
                quoted = '\n'.join(f"> {line}" for line in lines)
                md_parts.append(quoted)
            elif block_type == "ul":
                items = '\n'.join(f"- {item}" for item in block['items'])
                md_parts.append(items)
            elif block_type == "ol":
                items = '\n'.join(f"{i+1}. {item}" for i, item in enumerate(block['items']))
                md_parts.append(items)
            elif block_type == "pre":
                md_parts.append(f"```\n{block['text']}\n```")
            elif block_type == "image":
                img_src = block["src"]
                img_count += 1

                if embed_images:
                    # Convert to base64
                    b64_url = await image_to_base64(page, img_src)
                    if b64_url:
                        md_parts.append(f'<img src="{b64_url}" width="800px" />')
                    else:
                        print(f"  [WARN] Failed to embed image {img_src[:60]}", file=sys.stderr)
                else:
                    # Save to disk
                    disk_path = await save_image_to_disk(page, img_src, img_dir, img_count)
                    if disk_path:
                        rel_path = os.path.relpath(disk_path, output_path)
                        md_parts.append(f'<img src="{rel_path}" width="800px" />')
                    else:
                        print(f"  [WARN] Failed to download image {img_src[:60]}", file=sys.stderr)
            elif block_type == "figcaption":
                md_parts.append(f"> _{block['text']}_")

        # Join with double newlines
        md_text = "\n\n".join(md_parts)

        await browser.close()

        # Write markdown file
        md_path = output_path / f"{slug}.md"
        md_path.write_text(md_text, encoding="utf-8")
        print(f"  Saved: {md_path} ({len(md_text)} chars, {img_count} images)", file=sys.stderr)

        return str(md_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    embed_images = True
    debug = False
    output_dir = "."

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg == "--disk":
            embed_images = False
        elif arg == "--debug":
            debug = True
        else:
            output_dir = arg

    result = asyncio.run(medium_to_markdown(url, output_dir, embed_images, debug))
    print(result)