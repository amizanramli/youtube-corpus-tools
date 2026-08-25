"""Renders a directory as an ASCII tree, for previewing output structure
without having to open a file browser. Long file lists are truncated per
folder so a video with hundreds of comments doesn't produce an unreadable
wall of text."""

from pathlib import Path

IGNORED_NAMES = {".DS_Store"}


def build_tree(path: Path, prefix: str = "", max_children: int = 8) -> list:
    entries = sorted(
        (p for p in path.iterdir() if p.name not in IGNORED_NAMES),
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    n = len(entries)
    shown = entries[:max_children]
    lines = []

    for i, entry in enumerate(shown):
        is_last = (i == len(shown) - 1) and n <= max_children
        connector = "└── " if is_last else "├── "
        name = entry.name + ("/" if entry.is_dir() else "")
        lines.append(prefix + connector + name)
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(build_tree(entry, prefix + extension, max_children))

    if n > max_children:
        lines.append(prefix + f"└── ... and {n - max_children} more")

    return lines


def tree_string(root: Path, max_children: int = 8) -> str:
    """Full tree as a single string, rooted at `root`'s own name."""
    lines = [f"{root.name}/"] + build_tree(root, "", max_children)
    return "\n".join(lines)
