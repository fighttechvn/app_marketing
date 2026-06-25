"""Local-file preview reader for the preview pane (media + markdown)."""
import os, mimetypes


def preview_file(path):
    """Read a local file for the preview pane. Returns (bytes, content_type)."""
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
    if p.lower().endswith((".md", ".markdown", ".mdx")):
        ctype = "text/markdown; charset=utf-8"
    with open(p, "rb") as f:
        return f.read(), ctype
