# t3dgraph batch ⑤ — CLI 삼총사 (FEAT-1·4·6) 설계

- **작성일**: 2026-05-22 자율 사이클
- **선행**: batch ④ 진행 중(독립). 본 batch는 cli 영역 — controller/view 영역과 git 충돌 없음.

---

## 1. 범위

세 가지 CLI 확장을 한 슬라이스에 묶음:

- **FEAT-1**: `--lenient` 파싱 플래그 — 불량 객체 발생 시 raise 대신 skip + `g.warnings`에 누적.
- **FEAT-4**: `--json` 구조화 출력 — 현재 사람이 읽는 라인 출력 대신 JSON dump (그래프·분석 요약).
- **FEAT-6**: `t3dgraph dataflow <file>` 서브커맨드 — `DataFlowResult`를 텍스트 또는 JSON으로 덤프.

`argparse`의 서브커맨드 구조로 재편 — 기본(`summary`) + `dataflow` 두 서브커맨드. `--json` 플래그는 둘 다에서 사용.

## 2. CLI 구조 (변경 후)

```
t3dgraph <subcommand> <file> [--lenient] [--json]

Subcommands:
  summary        # 기존 동작 — 노드/링크/실행 흐름 요약
  dataflow       # 데이터 흐름 (sinks/sources/isolated/edges)
```

호환: `t3dgraph <file>`이 `t3dgraph summary <file>`로 동작 (없는 서브커맨드면 첫 인자를 file로 해석하는 fallback).

## 3. `--lenient` 구현

`parse_document`는 변경 ✗(파서는 strict 유지). `interpret` 레벨에서 `lenient=True` 옵션 — interpreter 안의 `_add_generic` 등 `try/except`로 감싸 실패 시 warning + skip. 단순한 접근: CLI가 try/except로 `interpret` 실패를 잡는 식으로 시작.

더 정확히: interpreter가 자기 안의 객체 단위 fail을 받아 warning에 누적. 본 batch는 minimal — `T3DParseError`/`LookupError`를 CLI 레벨에서 warning으로 강등하고 부분 결과를 반환하는 wrapper:

```python
def lenient_load(path: Path) -> tuple[GraphModel | None, list[str]]:
    warnings = []
    try:
        doc = parse_document(read_t3d_text(path))
    except T3DParseError as e:
        warnings.append(f"parse fail: {e}")
        return None, warnings
    try:
        plugin = default_registry().detect(doc)
        graph = plugin.interpreter_factory().interpret(doc)
        warnings.extend(graph.warnings)
        return graph, warnings
    except (LookupError, Exception) as e:
        warnings.append(f"interpret fail: {e}")
        return None, warnings
```

## 4. `--json` 출력

`summary` JSON 스키마:

```json
{
  "graph_type": "rigvm",
  "nodes": {"total": 6, "generic": 0},
  "links": 4,
  "variable_refs": 0,
  "external_refs": 0,
  "execution": {
    "edges": 3,
    "convergence_points": [],
    "branch_points": [],
    "steps": 4
  },
  "warnings": []
}
```

`dataflow` JSON 스키마:

```json
{
  "data_edges": [{"source": "A.O", "target": "B.I"}, ...],
  "sinks": ["..."],
  "sources": ["..."],
  "isolated": ["..."],
  "incoming_nodes": {"B": ["A"]},
  "outgoing_nodes": {"A": ["B"]}
}
```

## 5. 슬라이스

| 슬라이스 | 내용 |
|---|---|
| ζ | FEAT-1 + FEAT-4 + FEAT-6 일괄. CLI 모듈 재편(argparse 서브커맨드) + `--lenient` lenient_load + `--json` 직렬화. |

---

## 6. 불변식

- PRESERVE-ALL/INFO: CLI는 기존 분석을 그대로 호출 — 모델 변경 없음.
- Backward: `t3dgraph <file>` 인자 1개 형태 동작 보장 (subcommand 추론 fallback).

---

## 7. 비목표

- 인터프리터 객체 단위 lenient — 본 batch는 CLI wrapper 수준만. 더 깊은 lenient(객체 1개 fail 시 나머지 보존)는 다음 사이클.
- `t3dgraph diff` (FEAT-7) — batch ⑦.
