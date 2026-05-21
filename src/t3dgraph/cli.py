"""t3dgraph CLI — summary / dataflow 서브커맨드."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core.t3d.objects import T3DParseError
from .core.analysis.bundle import run as run_analyses
from ._cli.load import strict_load, lenient_load
from ._cli.serialize import summary_dict, dataflow_dict


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='t3dgraph', description='UE T3D 그래프 파서·분석')
    subs = parser.add_subparsers(dest='subcommand')

    p_sum = subs.add_parser('summary', help='.t3d 파일 요약')
    p_sum.add_argument('file')
    p_sum.add_argument('--lenient', action='store_true')
    p_sum.add_argument('--json', action='store_true')

    p_df = subs.add_parser('dataflow', help='데이터 흐름 분석')
    p_df.add_argument('file')
    p_df.add_argument('--lenient', action='store_true')
    p_df.add_argument('--json', action='store_true')

    return parser


def _load(path: Path, lenient: bool):
    return lenient_load(path) if lenient else strict_load(path)


def _resolve_plugin_id(graph) -> str:
    if not graph or not graph.nodes:
        return 'unknown'
    sample = graph.nodes[0].cls or ''
    return 'rigvm' if 'RigVM' in sample else 'unknown'


def _cmd_summary(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f'파일을 찾을 수 없습니다: {path}', file=sys.stderr)
        return 2
    try:
        graph, warnings = _load(path, args.lenient)
    except (UnicodeDecodeError, T3DParseError, LookupError) as e:
        print(f'T3D 파싱 실패: {e}', file=sys.stderr)
        return 4
    if graph is None:
        for w in warnings:
            print(f'warning: {w}', file=sys.stderr)
        return 0 if args.lenient else 4
    bundle = run_analyses(graph)
    plugin_id = _resolve_plugin_id(graph)
    if args.json:
        d = summary_dict(plugin_id, graph, bundle)
        d['warnings'] = warnings
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print(f'graph type: {plugin_id}')
        print(f'nodes: {len(graph.nodes)}  (generic: {sum(n.is_generic for n in graph.nodes)})')
        print(f'links: {len(graph.links)}')
        print(f'variable refs: {len(graph.variable_refs)}')
        print(f'external refs: {len(graph.external_refs)}')
        print(f'execution edges: {len(bundle.flow.execution_edges)}')
        print(f'execution steps: {len(bundle.execution_order)}')
        for w in warnings:
            print(f'  warning: {w}', file=sys.stderr)
    return 0


def _cmd_dataflow(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f'파일을 찾을 수 없습니다: {path}', file=sys.stderr)
        return 2
    try:
        graph, warnings = _load(path, args.lenient)
    except (UnicodeDecodeError, T3DParseError, LookupError) as e:
        print(f'실패: {e}', file=sys.stderr)
        return 4
    if graph is None:
        for w in warnings:
            print(f'warning: {w}', file=sys.stderr)
        return 0 if args.lenient else 4
    bundle = run_analyses(graph)
    if args.json:
        d = dataflow_dict(bundle.data_flow)
        d['warnings'] = warnings
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        r = bundle.data_flow
        print(f'data edges: {len(r.data_edges)}')
        for e in r.data_edges:
            print(f'  {e.source.full} -> {e.target.full}')
        print(f'sources: {", ".join(r.sources) or "없음"}')
        print(f'sinks: {", ".join(r.sinks) or "없음"}')
        print(f'isolated: {", ".join(r.isolated) or "없음"}')
    return 0


def run(argv: list[str]) -> int:
    # 하위 호환: 첫 인자가 서브커맨드가 아니면 summary로 위임
    if argv and argv[0] not in ('summary', 'dataflow', '-h', '--help') and not argv[0].startswith('-'):
        argv = ['summary'] + argv
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.subcommand == 'summary':
        return _cmd_summary(args)
    if args.subcommand == 'dataflow':
        return _cmd_dataflow(args)
    parser.print_help()
    return 2


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == '__main__':
    main()
