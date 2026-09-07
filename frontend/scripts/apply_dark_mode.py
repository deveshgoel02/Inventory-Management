"""One-off script: append matching dark: utility classes next to the app's
existing light-mode Tailwind classes across page files. Not part of the
build - run manually, then delete or keep for future bulk restyles."""
import re
from pathlib import Path

PAGES_DIR = Path(__file__).resolve().parents[1] / "src" / "pages"
EXCLUDE: set[str] = set()

# Order matters: hover: variants must be handled before their bare
# counterparts, and each bare pattern excludes a preceding "hover:" so it
# doesn't also match (and corrupt) the substring inside the hover: form.
MAPPING = [
    ("hover:bg-slate-50", "hover:bg-slate-50 dark:hover:bg-slate-800/60"),
    ("bg-slate-50", "bg-slate-50 dark:bg-slate-800/60"),
    ("bg-slate-100", "bg-slate-100 dark:bg-slate-700"),
    ("bg-white", "bg-white dark:bg-slate-800"),
    ("border-slate-300", "border-slate-300 dark:border-slate-600"),
    ("border-slate-200", "border-slate-200 dark:border-slate-700"),
    ("border-slate-100", "border-slate-100 dark:border-slate-700/60"),
    ("border-slate-50", "border-slate-50 dark:border-slate-800"),
    ("text-slate-900", "text-slate-900 dark:text-white"),
    ("text-slate-800", "text-slate-800 dark:text-slate-100"),
    ("text-slate-700", "text-slate-700 dark:text-slate-200"),
    ("text-slate-600", "text-slate-600 dark:text-slate-300"),
    ("text-slate-500", "text-slate-500 dark:text-slate-400"),
    ("text-slate-400", "text-slate-400 dark:text-slate-500"),
    ("text-slate-200", "text-slate-200 dark:text-slate-600"),
    # Semantic alert/callout banners (error/success/warning/selected-filter chips)
    ("text-red-700", "text-red-700 dark:text-red-300"),
    ("bg-red-50", "bg-red-50 dark:bg-red-900/30"),
    ("border-red-200", "border-red-200 dark:border-red-800/50"),
    ("text-emerald-700", "text-emerald-700 dark:text-emerald-300"),
    ("bg-emerald-50", "bg-emerald-50 dark:bg-emerald-900/30"),
    ("border-emerald-200", "border-emerald-200 dark:border-emerald-800/50"),
    ("bg-amber-50", "bg-amber-50 dark:bg-amber-900/30"),
    ("bg-indigo-50", "bg-indigo-50 dark:bg-indigo-900/30"),
]


def process(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in MAPPING:
        # Never match a token that's itself part of a dark: class we already
        # inserted (e.g. the "text-slate-400" inside "dark:text-slate-400"
        # added by an earlier rule in this same pass) or preceded by hover:
        # (handled by its own dedicated rule above).
        guard = "" if old.startswith("hover:") else r"(?<!hover:)(?<!dark:)"
        pattern = rf"{guard}\b{re.escape(old)}\b(?!\s+dark:)"
        text = re.sub(pattern, new, text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    for path in sorted(PAGES_DIR.glob("*.tsx")):
        if path.name in EXCLUDE:
            continue
        changed = process(path)
        print(("updated " if changed else "no change ") + path.name)


if __name__ == "__main__":
    main()
