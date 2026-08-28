#!/usr/bin/env python3
"""Build the search-the-exchange catalog index from a checkout of
tenable/cyberagents-exchange.

    build-index.py <catalog-dir> [--rev SHA] [--out-dir DIR]

Writes two files whose schema is deliberately identical to the Exchange's own
in-progress endpoints, so that when those ship the skill changes a URL and
nothing else:

  listings.json       every listing's metadata          (the cheap pass)
  listings-full.json  the same rows plus body sections  (the confirm pass)

Both carry `revision`, `generated`, `count`, and a `listings` array, so a stale
index reports itself as stale without a second lookup.
"""
import argparse, datetime, glob, json, os, re, sys

# Directory name -> the singular `type` value the Exchange API uses.
TYPES = {"agents": "agent", "skills": "skill",
         "mcp-servers": "mcp-server", "playbooks": "playbook"}
SITE = "https://exchange.tenable.com"


def frontmatter(txt):
    return txt.split("---", 2)[1] if txt.startswith("---") else ""


def scalar(fm, key):
    m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def sequence(fm, key):
    m = re.search(rf'^{key}:\s*\n((?:\s*-\s.*\n)+)', fm, re.M)
    if m:
        return re.findall(r'-\s*"?([^"\n]+?)"?\s*$', m.group(1), re.M)
    m = re.search(rf'^{key}:\s*\[(.*?)\]', fm, re.M)
    if not m or not m.group(1).strip():
        return []
    return [v.strip().strip('"') for v in m.group(1).split(",") if v.strip()]


def section(txt, heading):
    """One `##` section as a single line of plain text, or None if absent."""
    m = re.search(rf'^##\s+{heading}\s*$(.*?)(?=^##\s|\Z)', txt, re.M | re.S)
    if not m:
        return None
    body = re.sub(r'^\s*[-*]\s+', '; ', m.group(1), flags=re.M)
    body = re.sub(r'^\s*>\s?', '', body, flags=re.M)          # blockquote pull-outs
    # Collapse first: emphasis and links wrap across source lines, and the
    # patterns below are single-line by design.
    body = re.sub(r'\s+', ' ', body)
    body = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', body)      # links
    body = re.sub(r'\*\*([^*]+)\*\*', r'\1', body)            # bold
    body = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'\1', body)   # italic
    body = re.sub(r'`([^`]+)`', r'\1', body)                  # inline code
    body = body.replace('**', '')   # unbalanced markers left by the listing itself
    return body.strip(' ;') or None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("catalog")
    p.add_argument("--rev", default="unknown")
    p.add_argument("--out-dir", default=".")
    a = p.parse_args()

    rows = []
    for d, singular in TYPES.items():
        for f in sorted(glob.glob(os.path.join(a.catalog, d, "*.md"))):
            txt = open(f, encoding="utf-8").read()
            fm = frontmatter(txt)
            slug = os.path.basename(f)[:-3]
            rows.append({
                "type": singular,
                "slug": slug,
                "name": scalar(fm, "name"),
                "description": scalar(fm, "description"),
                "tags": sequence(fm, "tags"),
                "integrations": sequence(fm, "integrations"),
                # Trailing slash: the site 308-redirects the bare path.
                "url": f"{SITE}/{d}/{slug}/",
                "author": scalar(fm, "author"),
                "tier": scalar(fm, "tier"),
                "date_added": scalar(fm, "date_added"),
                # Skills carry an `invocation`; agents, MCP servers, and
                # playbooks carry none, so "" means the type has no such field.
                "invocation": scalar(fm, "invocation"),
                "compatible_platforms": sequence(fm, "compatible_platforms"),
                # A listing with no such section is kept with a null body, never
                # dropped — one absent from the index is invisible to the skill.
                "what_it_does": section(txt, "What it does"),
                "how_it_works": section(txt, "How it works"),
            })

    if not rows:
        sys.exit(f"no listings found under {a.catalog} — wrong directory?")

    envelope = {
        "revision": a.rev,
        "generated": datetime.datetime.now(datetime.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(rows),
    }
    BODY = ("what_it_does", "how_it_works")
    outputs = {
        "listings.json":      [{k: v for k, v in r.items() if k not in BODY} for r in rows],
        "listings-full.json": rows,
    }
    for name, listings in outputs.items():
        path = os.path.join(a.out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({**envelope, "listings": listings}, fh,
                      ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"{path}: {len(listings)} listings, "
              f"{os.path.getsize(path) // 1024}KB", file=sys.stderr)

    missing = [f'{r["type"]}/{r["slug"]}' for r in rows if not r["what_it_does"]]
    if missing:
        print(f"no 'What it does' section: {', '.join(missing)}", file=sys.stderr)


if __name__ == "__main__":
    main()
