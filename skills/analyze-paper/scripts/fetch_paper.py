#!/usr/bin/env python3
"""
Helper script for the /analyze-paper skill to resolve arXiv IDs/URLs,
fetch bibliographic metadata via the arXiv API, and download PDFs locally
using only the Python standard library.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ARXIV_ID_REGEX = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf|html)/|arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def extract_arxiv_id(source: str) -> str | None:
    source = source.strip().removesuffix(".pdf")
    match = ARXIV_ID_REGEX.search(source)
    if match:
        return match.group(1)
    return None


def fetch_arxiv_metadata(arxiv_id: str, download_dir: Path | None = None) -> dict:
    api_url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "Antigravity-AnalyzePaper-Skill/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        xml_bytes = resp.read()

    root = ET.fromstring(xml_bytes)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"No arXiv entry found for ID: {arxiv_id}")

    title_el = entry.find("atom:title", ns)
    summary_el = entry.find("atom:summary", ns)
    published_el = entry.find("atom:published", ns)

    title = " ".join((title_el.text or "").split()) if title_el is not None else ""
    abstract = " ".join((summary_el.text or "").split()) if summary_el is not None else ""
    published = (published_el.text or "")[:10] if published_el is not None else ""
    year = published[:4] if published else ""

    authors = []
    for author_el in entry.findall("atom:author", ns):
        name_el = author_el.find("atom:name", ns)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    categories = []
    for cat_el in entry.findall("atom:category", ns):
        term = cat_el.attrib.get("term")
        if term:
            categories.append(term)

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    local_pdf_path = None

    if download_dir is not None:
        download_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^a-zA-Z0-9._-]", "_", arxiv_id)
        target_pdf = download_dir / f"{safe_id}.pdf"
        if not target_pdf.exists():
            pdf_req = urllib.request.Request(
                pdf_url,
                headers={"User-Agent": "Antigravity-AnalyzePaper-Skill/1.0"},
            )
            with urllib.request.urlopen(pdf_req, timeout=60) as pdf_resp:
                target_pdf.write_bytes(pdf_resp.read())
        local_pdf_path = str(target_pdf.resolve())

    return {
        "source_type": "arxiv",
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "published_date": published,
        "year": year,
        "categories": categories,
        "abstract": abstract,
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": pdf_url,
        "local_pdf_path": local_pdf_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve paper source (local path or arXiv ID/URL) and fetch metadata/PDF."
    )
    parser.add_argument("source", help="Path to local file, arXiv ID, or arXiv URL")
    parser.add_argument(
        "--download-dir",
        default="./reports/papers",
        help="Directory to save downloaded PDFs (default: ./reports/papers)",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Fetch metadata only without downloading the PDF",
    )
    args = parser.parse_args()

    local_path = Path(args.source)
    if local_path.exists():
        info = {
            "source_type": "local_file",
            "local_path": str(local_path.resolve()),
            "file_name": local_path.name,
            "extension": local_path.suffix.lower(),
            "size_bytes": local_path.stat().st_size,
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    arxiv_id = extract_arxiv_id(args.source)
    if arxiv_id:
        dl_dir = None if args.no_download else Path(args.download_dir)
        info = fetch_arxiv_metadata(arxiv_id, download_dir=dl_dir)
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    print(
        json.dumps(
            {
                "error": f"Could not resolve '{args.source}' as a local file or valid arXiv identifier."
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

