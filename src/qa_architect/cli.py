"""Command-line entry point.

    qa-architect run path/to/brd.md [--out data/runs]
    qa-architect serve [--host 0.0.0.0] [--port 8000]
"""

from __future__ import annotations

import argparse
import sys

from qa_architect.config import get_settings
from qa_architect.export.promptfoo import to_promptfoo_yaml
from qa_architect.ingestion.parser import parse_document
from qa_architect.orchestration.pipeline import build_pipeline
from qa_architect.store import RunStore


def _cmd_run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.out:
        settings.data_dir = args.out
    pipeline = build_pipeline(settings)
    document = parse_document(args.brd)
    blueprint = pipeline.run(document)

    store = RunStore(settings.data_dir)
    store.save(blueprint)

    print(f"Run:          {blueprint.generation_run_id}")
    print(f"Provider:     {blueprint.provenance.llm_provider} ({blueprint.provenance.llm_model})")
    print(f"Document:     {blueprint.doc_metadata.source_name}")
    print(f"Requirements: {len(blueprint.requirements)}")
    print(f"Tests:        {len(blueprint.tests)}")
    print(f"Trace links:  {len(blueprint.trace_links)}")
    print(f"Saved to:     {store._run_dir(blueprint.generation_run_id)}")
    if args.print_promptfoo:
        print("\n--- promptfooconfig.yaml ---\n")
        print(to_promptfoo_yaml(blueprint))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "qa_architect.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qa-architect", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the pipeline on a BRD file.")
    p_run.add_argument("brd", help="Path to BRD (.md/.txt/.pdf/.docx)")
    p_run.add_argument("--out", help="Data dir for outputs", default=None)
    p_run.add_argument("--print-promptfoo", action="store_true")
    p_run.set_defaults(func=_cmd_run)

    p_serve = sub.add_parser("serve", help="Run the FastAPI server.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
