"""CLI for the basic plagiarism checker."""

import argparse
import sys
from pathlib import Path

from checker import DocumentStore, compare_with_document, find_matching_phrases


DEFAULT_DOCS_DIR = Path(__file__).parent / "documents"


def read_input_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8", errors="ignore")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --text, --file, or pipe input through stdin.")


def format_percent(value: float) -> str:
    return f"{value * 100:6.2f}%"


def print_report(query: str, results: list[tuple], show_phrases: bool, phrase_min: int) -> None:
    print(f"\nChecked input ({len(query.split())} words) against {len(results)} document(s)\n")
    print(f"{'Document':<24} {'Overall':>10} {'Words':>10} {'Shingles':>10} {'Cosine':>10}")
    print("-" * 68)

    for document, report in results:
        print(
            f"{document.title:<24}"
            f"{format_percent(report.overall):>10}"
            f"{format_percent(report.jaccard_words):>10}"
            f"{format_percent(report.jaccard_shingles):>10}"
            f"{format_percent(report.cosine):>10}"
        )

        if show_phrases and report.overall > 0:
            phrases = find_matching_phrases(query, document.content, min_length=phrase_min)
            if phrases:
                print(f"  Matching phrases in {document.title}:")
                for phrase in phrases[:3]:
                    preview = phrase if len(phrase) <= 80 else phrase[:77] + "..."
                    print(f"    - \"{preview}\"")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare input text against stored documents using string matching.",
    )
    parser.add_argument("--text", help="Input text to check.")
    parser.add_argument("--file", help="Path to a text file to check.")
    parser.add_argument(
        "--docs-dir",
        default=str(DEFAULT_DOCS_DIR),
        help="Directory containing reference documents.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.15,
        help="Minimum overall similarity score to highlight (0.0-1.0).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Show only the top N most similar documents.",
    )
    parser.add_argument(
        "--show-phrases",
        action="store_true",
        help="Print shared phrases for matched documents.",
    )
    parser.add_argument(
        "--phrase-min",
        type=int,
        default=20,
        help="Minimum shared phrase length when --show-phrases is used.",
    )
    parser.add_argument(
        "--add-doc",
        metavar="ID",
        help="Add a document from --file or --text into the document store.",
    )
    parser.add_argument(
        "--list-docs",
        action="store_true",
        help="List documents currently stored.",
    )
    args = parser.parse_args()

    store = DocumentStore(Path(args.docs_dir))
    loaded = store.load()

    if args.list_docs:
        if not store.documents:
            print(f"No documents found in {args.docs_dir}")
            return
        print(f"Loaded {loaded} document(s) from {args.docs_dir}:")
        for document in store.list_documents():
            words = len(document.content.split())
            print(f"  - {document.title} ({words} words)")
        return

    if args.add_doc:
        content = read_input_text(args)
        document = store.add_text(args.add_doc, content)
        print(f"Stored document '{document.title}' in {document.path}")
        return

    query = read_input_text(args)
    if not store.documents:
        print(f"No documents loaded from {args.docs_dir}. Add files to that folder first.")
        return

    results = []
    for document in store.list_documents():
        report = compare_with_document(query, document.content)
        if report.overall >= args.threshold:
            results.append((document, report))

    results.sort(key=lambda item: item[1].overall, reverse=True)
    results = results[: args.top]

    if not results:
        print(
            f"No documents exceeded the similarity threshold of {args.threshold:.0%}. "
            "Try lowering --threshold."
        )
        return

    print_report(query, results, args.show_phrases, args.phrase_min)


if __name__ == "__main__":
    main()
