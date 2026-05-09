# Medium to Markdown Converter

Convert Medium articles to clean, self-contained Markdown files with embedded images.

## Features

- **Images embedded by default** — Images are converted to base64 data URLs and embedded directly in the markdown. No external image files needed.
- **Images in correct positions** — Images appear exactly where they do in the original article, not appended at the end.
- **Optional disk storage** — Use `--disk` flag to save images to a separate folder instead of embedding.
- **Preserves structure** — Headings, paragraphs, blockquotes, lists, code blocks, and captions all render correctly.
- **Extensible architecture** — Ready for video, embeds, and other Medium content types.

## Installation

### Requirements

- Python 3.7+ (via conda environment `python_313x`)
- Playwright (for headless browser automation)

### Setup

```bash
# Activate conda environment
conda activate python_313x

# Install Playwright
conda install -c conda-forge playwright

# Download Chromium browser (one-time)
playwright install chromium
```

## Usage

### Basic: Embed images (default)

```bash
python medium-to-md.py https://gillesdemaneuf.medium.com/the-emi-fix-8be2313448b4
```

Creates `the-emi-fix-8be2313448b4.md` with all images embedded as base64.

### Save images to disk

```bash
python medium-to-md.py https://gillesdemaneuf.medium.com/the-emi-fix-8be2313448b4 --disk
```

Creates:
- `the-emi-fix-8be2313448b4.md` with image references
- `the-emi-fix-8be2313448b4_images/` folder with image files

### Specify output directory

```bash
python medium-to-md.py https://medium.com/path/to/article --dir output/
```

### Debug mode

Debug output is **on by default** — you'll see progress messages like "Waiting for article element", "Waiting Xs for Medium page to fully load", etc.

To disable debug output:

```bash
python medium-to-md.py https://gillesdemaneuf.medium.com/the-emi-fix-8be2313448b4 --nodebug
```

### Adjust page render wait time

If extraction fails the first time (gets 0 blocks), increase the wait time:

```bash
python medium-to-md.py https://medium.com/path/to/article --wait 6
```

Default is 4 seconds. Use higher values (5-8) for slower connections or complex articles.

### Combine options

```bash
# Save to output/ with disk images and extra wait time
python medium-to-md.py https://medium.com/path/to/article --dir output/ --disk --wait 5

# Debug output with custom directory
python medium-to-md.py https://medium.com/path/to/article --dir tmp/ --debug
```

## How It Works

1. **Loads the article** — Uses Playwright to fetch and render the Medium page
2. **Extracts structure** — Walks the DOM tree, preserving element order and hierarchy
3. **Processes images** — 
   - Default: Fetches and converts to base64 data URLs (embedded in markdown)
   - With `--disk`: Downloads and saves to a separate folder
4. **Builds markdown** — Converts each block to appropriate markdown syntax (headings, lists, blockquotes, etc.)
5. **Writes output** — Single `.md` file with embedded or referenced images

## Image Handling

### Embedded (Default)

```html
<img src="data:image/jpeg;base64,/9j/4AAQSkZJRg..." width="800px" />
```

**Pros:**
- Single file to share
- No broken image links
- Works offline
- Images displayed at fixed width (800px default)

**Cons:**
- Larger markdown file
- Less readable in plain text

### Disk Storage (`--disk`)

```markdown
![Image](the-emi-fix-8be2313448b4_images/img_0001.jpg)
```

**Pros:**
- Smaller markdown file
- Images can be edited independently
- Better for version control

**Cons:**
- Multiple files to manage
- Images must be kept with markdown

## Supported Content Types

Currently handles:
- Headings (h1–h6)
- Paragraphs with formatting (**bold**, *italic*, `code`)
- Hyperlinks (converted to Markdown footnotes `[^1]`)
- Blockquotes
- Unordered and ordered lists
- Code blocks
- Images and figure captions

### Link Handling

Links in the article are automatically converted to Markdown footnotes:

**Original article:**
```
This is a [link to example](https://example.com) in the text.
```

**Generated markdown:**
```markdown
This is a link to example[^1] in the text.

---

## References

[^1]: https://example.com
```

This preserves the URL while keeping the text flowing naturally. The footnote reference section is automatically appended at the end of the document.

## Planned: Other Medium Content

Framework is ready to add:
- Embedded videos (YouTube, Vimeo, etc.)
- Audio embeds
- Iframes (Twitter, CodePen, etc.)
- Custom embeds

Pass examples when ready, and the script can be extended.

## How It Handles Heavy Pages

Medium articles with lots of content can take time to load. The script:

1. **Tries to wait for network idle** — waits for all network activity to settle (best reliability)
2. **Retries once if it times out** — some heavy pages need a second attempt
3. **Falls back to DOM content loaded** — if retries don't work, loads what's available
4. **Waits extra time** — the `--wait` parameter adds additional buffer for lazy-loading images

If you get 0 blocks on first run, running again usually succeeds. You can also increase `--wait` to 8-10 for very heavy pages.

## Notes

- Medium images are fetched from `miro.medium.com`
- All resources are downloaded directly (fonts, stylesheets are skipped for speed)
- Article slug is derived from the URL's final path segment
- Output encoding is UTF-8
- Heavy articles may take 30-60 seconds to fully load

## Troubleshooting

**"No <article> tag found"**
- The page may not have rendered. Medium's layout sometimes varies. Try again—it usually works on retry.

**Images fail to download**
- Check your internet connection
- The Medium CDN may be temporarily unavailable
- Try with `--disk` to save partial images

**Output file is very large**
- This is normal with embedded base64 images, especially with many or large images
- Use `--disk` if you want a smaller markdown file
