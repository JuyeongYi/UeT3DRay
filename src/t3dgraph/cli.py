"""t3dgraph CLI — .t3d 파싱·해석·분석 요약."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from .core.t3d.document import parse_document
from .core.t3d.objects import T3DParseError
from .core.t3d.encoding import read_t3d_text
from .core.registry import default_registry
from .core.analysis.flow import analyze_flow
from .core.analysis.execution_order import compute_execution_order


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="t3dgraph", description="UE T3D 그래프 파서·분석")
    parser.add_argument("file", help=".t3d(.txt) 파일 경로")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 2

    try:
        doc = parse_document(read_t3d_text(path))
    except UnicodeDecodeError as e:
        print(f"파일 인코딩을 해석할 수 없습니다: {path} ({e})", file=sys.stderr)
        return 2
    except T3DParseError as e:
        print(f"T3D 파싱 실패: {path}: {e}", file=sys.stderr)
        return 4
    registry = default_registry()
    try:
        plugin = registry.detect(doc)
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 3

    graph = plugin.interpreter_factory().interpret(doc)
    flow = analyze_flow(graph)
    order = compute_execution_order(graph, flow=flow)

    print(f"graph type: {plugin.id}")
    print(f"nodes: {len(graph.nodes)}  (generic: {sum(n.is_generic for n in graph.nodes)})")
    print(f"links: {len(graph.links)}")
    print(f"variable refs: {len(graph.variable_refs)}")
    print(f"external refs: {len(graph.external_refs)}")
    print(f"execution edges: {len(flow.execution_edges)}")
    print(f"convergence points (fan-in): {flow.convergence_points or '없음'}")
    print(f"execution steps: {len(order)}")
    for w in graph.warnings:
        print(f"  warning: {w}", file=sys.stderr)
    return 0


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
