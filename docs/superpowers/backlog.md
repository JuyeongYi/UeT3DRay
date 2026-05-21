# t3dgraph 백로그

> improver improvement-review에서 나온 **미처리 findings**와 향후 기능 아이디어를 누적·보존하는 문서.
> `.improvement-review/findings.md`는 매 리뷰 사이클마다 덮어쓰이므로, 보존이 필요한 항목을 여기에 옮겨 둔다.
>
> **처리 규칙 (중요):** 백로그 항목을 실제로 착수할 때는 **반드시 그 시점의 코드를 다시 읽어 finding이 여전히 유효한지 재검토**한다. Phase가 진행되며 코드가 바뀌어 finding이 이미 해소됐거나 형태가 달라졌을 수 있다 — 옛 finding을 그대로 적용하지 말 것.

상태: 2026-05-22 정합화. batch ②(F1~F9) + batch ③(D-A1/C-A1 축) 종료 후 잔존 항목 정리.

---

## 미해결 잔여 (batch ④+ 대상)

### 코어 리팩터

| ID | 내용 | 출처 |
| --- | --- | --- |
| **D-B3** | AppController·view의 분석 오케스트레이션을 `analyses.bundle.run(graph) -> AnalysisBundle` + `view.show_analyses(bundle)`로 묶기. controller·contracts·view 3곳 변경 비용 제거. | improver Slice D |

### 잡정리

| ID | 내용 | 출처 |
| --- | --- | --- |
| P1.5-A1 | `ValueParseError`에 구조화된 `pos` 속성 노출 — 현재 `T3DParseError.col`이 값 시작만 가리킴. | improver Phase 1.5 |
| P2a-B2 | `show_error`를 `AbstractGraphView` 계약으로 승격 — 현재 contracts.py에 미정의, `getattr` 덕타이핑. | improver Phase 2a |
| P2c-B1 | `highlight_node` 보일러플레이트가 inspector/analysis/exec_order/data_flow 4개 패널에 중복 — NavigablePanel은 시그널만 가짐. 공용 베이스로 끌어올림. | improver Phase 2c |
| P2c-B2(잔여) | `MainWindow._render_current`가 분석(flow·order·data_flow)을 직접 호출 — controller(open_file) 폴백 경로와 중복. D-B3과 함께 해소. | improver Phase 2c |
| BL1-B2 | `scene._connected_paths_by_node`가 `pin_segment(path, 0)` 사용 — `node_of(path)`로 일관화 (호출부 단순화). | improver 정리 batch ① |

### improver Slice ζ 리뷰 findings (2026-05-22, master 1471caa) — 미처리

| ID | 내용 |
| --- | --- |
| **ζ-A1** | `_resolve_plugin_id`가 registry detect 결과를 버리고 `'RigVM' in sample` 문자열 매칭으로 재추론 — 미래 플러그인 추가 시 'unknown' 폴백. `strict_load`/`lenient_load` 반환에 plugin_id(또는 plugin 핸들) 동봉. |
| ζ-A2 | dataflow 텍스트 출력 cap 없음 — `--limit N`(기본 100, 0=unlimited) 추가. |
| ζ-A3 | lenient mode 종료 코드 단일(0) — `0=완전 성공`, `1=부분 결과+warnings`, `4=완전 실패`로 차등화. |
| ζ-B1 | `lenient_load`의 `except Exception` 광범위 — `T3DParseError|LookupError|ValueParseError`로 좁혀 프로그래밍 오류는 surface. |
| ζ-B2 | argparse 공통 옵션 중복 — `parents=[common]` 부모 파서 1개. |
| ζ-B3 | `summary_dict(graph_type, ...)` 인자 — graph_type을 graph/registry 단일 출처로(ζ-A1과 같은 결). |
| FEAT-12 | `t3dgraph exec-order` 서브커맨드 — bundle.execution_order 텍스트/JSON 노출. CLI↔GUI 패리티. |
| FEAT-13 | stdin/stdout 파이프 모드 — `-` 인자 + `cat ... | t3dgraph ...`. git 객체와 직접 결합. |
| (FEAT-7 중복) | dataflow-diff — 이미 batch ⑦ θ-2로 발주됨. |

### 기능 추가 (spec §3.3 향후 확장)

| ID | 내용 |
| --- | --- |
| FEAT-1 | `--lenient` 파싱 플래그 — 불량 객체 skip + 경고 누적. Phase 1 계획에서 명시 deferred. |
| FEAT-2 | round-trip `.t3d` 익스포트 — 무손실 모델 → 텍스트 직렬화. |
| FEAT-3 | 에셋 단위 교차 파일 resolver — `external_refs` 해소(spec §3.3 seam). |
| FEAT-4 | CLI `--json` 구조화 출력 — 파이프라인 컴포넌트화. |
| FEAT-6 | CLI `t3dgraph dataflow <file>` — `data_edges`/`sinks`/`sources`/`isolated` 텍스트·JSON 덤프. |
| FEAT-7 | 두 t3d 파일 간 데이터 흐름 diff — 동일 sink 기준 의존 트리 추가/제거/깊이 변화. |
| FEAT-8 | Sink 단위 "compute trace" 코드형 렌더 — DAG depth(레벨)별 의존 노드 평탄화. FEAT-5와 짝. |
| FEAT-9 | 뒤로가기/위로 가기 단축키 — `Alt+←`/`Backspace`→`pop()`, `Alt+↑`→ 한 단계 위. |
| FEAT-10 | 멀티 파일 탭 UI — `GraphStack.open_root`/`roots()`/`select_root` 기반 `QTabBar`. |
| FEAT-11 | 서브그래프 미니맵 / 위치 인디케이터 — 사이드 도크에 부모 트리 + 현재 위치 하이라이트. |

---

## 처리 계획 (2026-05-22 자율 사이클)

데드라인 — 한국시간 2026-05-22 06:00 KST. 사용자 위임 자율 진행. 권장 발주 순서:

1. **batch ④** δ(D-B3) + ε(잡정리 묶음)
2. **batch ⑤** ζ(CLI 삼총사 — FEAT-1·4·6)
3. **batch ⑥** η(UI — FEAT-9 단축키 + FEAT-10 탭)
4. **batch ⑦** θ(분석 시각화 — FEAT-8 compute trace + FEAT-7 diff)
5. **batch ⑧** ι(FEAT-2) · κ(FEAT-3) · λ(FEAT-11) — 무거운 기능, 시간 남으면

router queue가 모든 slice를 받아 implementer 직렬 처리.

---

## 해소 완료 (이력)

batch ②(F1·F3·F5·F6·F7·F8·F9·F2) · batch ③(α 핀 단위 모델·β 인터프리터 정보 보존·γ UX 잡정리)로 다음 모두 해소:

- P1.5-B1 (encoding 통합), P2a-A1 (Position 폴백), P2a-A2 (cli 캐치), P2a-B1 (read_text 통합), P2a-B3 (paths 중앙화)
- P2b-A1 (InspectorPanel full path), P2b-A2 (zero struct), P2b-B1 (ViewState observer 제거), P2b-B2 (_type_suffix 통합), P2b-B3 (pin_status docstring)
- P2c-A1 (FixedFont), P2c-B2 (controller로 분석 이관 — 단 _render_current 중복 잔여는 D-B3과 함께)
- P2d-A1 (pin_anchor sub-pin 처리), P2d-A2 (fan_in_highlight in_place), P2d-B1 (mode_id)
- BL1-B1 (core/base/paths 이동)
- D-A1·A2·A3·B1·B2 (batch ③ α)
- C-A1·A2·A3·B1·B2·B3 (batch ③ β·γ)
- FEAT-5 (이전 사이클 머지)
