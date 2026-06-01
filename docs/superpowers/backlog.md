# t3dgraph 백로그

> improver improvement-review에서 나온 **미처리 findings**와 향후 기능 아이디어를 누적·보존하는 문서.
> `.improvement-review/findings.md`는 매 리뷰 사이클마다 덮어쓰이므로, 보존이 필요한 항목을 여기에 옮겨 둔다.
>
> **처리 규칙 (중요):** 백로그 항목을 실제로 착수할 때는 **반드시 그 시점의 코드를 다시 읽어 finding이 여전히 유효한지 재검토**한다. Phase가 진행되며 코드가 바뀌어 finding이 이미 해소됐거나 형태가 달라졌을 수 있다 — 옛 finding을 그대로 적용하지 말 것.

상태: 2026-06-01 정합화. batch ⑨ Spec 1 슬라이스 μ(F10·F12)·ξ(F15)·ν(F13·F18·F19) 모두 머지 완료(`71208c2`). 본 사이클 improver findings 24건 등재 (μ 9 + ξ 6 + ν 9). 다음: Spec 2 (F11·F14·F16·F17·F20) brainstorming 진입.

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

### improver Slice η 리뷰 findings (2026-05-22, master f4d1913) — 미처리

| ID | 내용 |
| --- | --- |
| **η-A1** | Backspace가 `Qt.ApplicationShortcut`로 등록 — 텍스트 입력 위젯에서도 가로채 사용자 데이터 손실. `Qt.WindowShortcut`로 좁히거나 슬롯에서 `focusWidget()`이 QLineEdit/QTextEdit이면 무시. |
| η-A2 | 탭 닫기 후 `_tab_bar.currentIndex` ↔ `graph_stack._cur_root` 동기화 누락 — close 직후 명시 `setCurrentIndex` 호출. |
| η-A3 | `Alt+Up` 동작이 `Alt+Left`와 동일(`jump_to(len-2)` = `pop()`) — `jump_to(0)` "루트로"로 의미 차이 또는 제거. |
| η-B1 | `_build_shortcuts` inline import → 상단으로. |
| η-B2 | `blockSignals` 보일러플레이트 → `QSignalBlocker` RAII. |
| η-B3 | `GraphStack._cur_root` private 우회 → `current_root_index()` getter 노출. |
| FEAT-14 | 탭 컨텍스트 메뉴 — 이 탭 닫기 / 다른 탭 닫기 / 모두 닫기 / 경로 복사. |
| FEAT-15 | 단일 탭 시 탭바 자동 숨김 — `setVisible(count > 1)`. |
| FEAT-16 | 최근 파일 목록 메뉴 — 4~8개. |

### improver Slice θ-1 리뷰 findings (2026-05-22, master e714ed2) — 미처리

| ID | 내용 |
| --- | --- |
| **θ1-A1** | trace 텍스트가 핀 단위 정보 손실 — `compute_trace(incoming_nodes)`가 노드 단위. `data_edges` PinRef를 활용해 "A.O → S.I" 핀 단위 trace 라인. D-A1 일관성 회복. |
| θ1-A2 | 라벨 "sink:"가 비-sink 노드에도 출력 — 활성 노드가 sink면 "sink:", 아니면 "trace from:" 동적 라벨. |
| θ1-A3 | `compute_trace` max_depth 무경고 절단 — `truncated: bool` 또는 sentinel 라인. |
| θ1-B1 | `depth=0` 알고리즘 ↔ UI 스킵 어긋남 — `include_root` 플래그 또는 알고리즘 depth 1부터 통일. |
| θ1-B2 | `activate_node` 외부 호출 경로에서 trace 갱신 누락 — `_on_activated` 단일 진입점화. |
| θ1-B3 | `QSplitter` stretch factor 미설정 — tree(3) : trace(1) 위계 반영. |
| FEAT-17 | Trace 텍스트의 노드명 클릭 네비 — QListWidget 또는 rich-text 링크. |
| FEAT-18 | CLI `compute-trace <file> <sink>` — bundle에 이미 compute_trace 있음. ζ pattern 활용. |
| FEAT-19 | Trace diff (두 파일 같은 sink) — depth별 노드 set diff. dataflow-diff와 짝. |

### improver Slice θ-2 리뷰 findings (2026-05-22, master d458226) — 미처리

| ID | 내용 |
| --- | --- |
| **θ2-A1** | `diff_data_flow` 핀 단위 정보 손실 — `_depth_map(compute_trace)`이 노드 단위. D-A1/C-A1/θ1-A1과 같은 "상위 레이어 정보 묵살" 패턴 **4회 재발 — 정리 batch 우선 축**. ancestor 출처 핀이 사라져 S.InMul vs S.InAdd 경로 구분 불가. |
| θ2-A2 | graph_type 일치 검증 부재 — RigVM vs 미래 plugin 결과 무의미 비교 가능. ζ-A1 해결 시 비용 0. |
| θ2-A3 | diff text 출력 헤드라인 부재 — `changed: X · unchanged: Y · added: Z · removed: W` 한 줄 추가. |
| θ2-B1 | inline import 재발 (`_cmd_diff`의 `from ... data_flow_diff import`) — η-B1 패턴 같은 파일 두 번째. 모듈 상단 import 규약 명문화. |
| θ2-B2 | subcommand 공통 옵션 3번째 중복(`--lenient`/`--json` summary/dataflow/diff) — ζ-B2 backlog가 그대로 있는데 비용을 또 지불. `parents=[common]`. |
| θ2-B3 | subcommand 디스패치 3곳 동시 수정 — `COMMANDS: dict[str, tuple[register, handler]]` 테이블로 통합. ζ-B2·B3와 같은 묶음. |
| FEAT-20 | diff JSON 최상단 `summary: {sinks_added, sinks_removed, sinks_changed, sinks_unchanged}` — CI `jq` 폴리시 가능. |
| FEAT-21 | diff exit code semantics — `0=변화 없음, 1=차이, 2=argv, 4=로드 실패`. ζ-A3와 묶음. |
| FEAT-22 | `t3dgraph diff --markdown` — PR 코멘트용 마크다운 표 출력. |

**메모 (improver 권고):** θ2-B1·B2·B3는 ζ-B 시리즈와 정확히 같은 라인 — 정리 batch에서 한 번에 처리 (parent parser + 디스패치 테이블 + 상단 import 규약). 패턴 일소형 슬라이스 후보.

### improver Slice ι 리뷰 findings (2026-05-22, master ad26139) — 미처리

| ID | 내용 |
| --- | --- |
| **ι-A1** | **QuotedString 직렬화 escape 누락** — `f'"{v.text}"'`가 내부 `"`·`\\` 그대로. round-trip 시 의미 변경 위험. **round-trip 정확성 1순위 가드레일.** |
| ι-A2 | `Class={cls or "?"}` fallback — cls=None 시 `?` 토큰이 invalid t3d. `raise ValueError` 권장 (원본 doc 단계 막기). |
| ι-A3 | `_cmd_serialize`의 `--lenient` 의미 없음 — 파싱 실패 시 빈 stdout silent 손실. 옵션 제거 또는 exit 1 명시 계약. |
| ι-B1 | inline imports 3번째 재발 (cli.py) — η-B1·θ2-B1에 이어. 정리 batch 1순위 신호 강화. |
| ι-B2 | subcommand 추가 4곳 동시 수정 — θ2-B3 dispatch 테이블 4번째 증명. `COMMANDS` 테이블 도입 비용이 또 한 번의 수정 비용에 도달. |
| ι-B3 | 3-space indent 매직 리터럴 — `INDENT = '   '` 모듈 상수 또는 `indent_str` 매개변수. |
| FEAT-23 | Round-trip 등가성(idempotence) 프로퍼티 테스트 — `parse(serialize(parse(src))).objects == parse(src).objects`. ι-A1/A2 자동 감지. |
| FEAT-24 | `serialize --output PATH` — Windows 리다이렉트 인코딩 회피. |
| FEAT-25 | `t3dgraph format` (또는 `serialize --canonical`) — 속성 정렬·들여쓰기 정규화. PR diff 노이즈 감소. |

### improver Slice κ 리뷰 findings (2026-05-22, master e067705) — 미처리

| ID | 내용 |
| --- | --- |
| κ-A1 | `AssetResolver.register` 이름 충돌 silent first-wins — `setdefault` 대신 충돌 누적(warnings 또는 다중 보존). |
| **κ-A2** | `_resolver`가 등록만 되고 활용 안 됨 — inspector/data_flow_panel/controller가 external_refs 해결 결과 미사용. **backend 완성 + frontend 미연결 절반-기능 상태**. |
| κ-A3 | 같은 파일 이중 파싱 — `load_folder`가 파싱한 doc을 `_open_handler` 재호출이 또 파싱. Orion 규모 비용 2배. 핸들러 인터페이스 확장. |
| κ-B1 | `_on_open_folder` triple inline import — η-B1·θ2-B1·ι-B1에 이어 **4번째 패턴, cli.py → main_window.py로 번짐**. 정리 슬라이스 범위 확장 신호. |
| κ-B2 | `load_folder`의 `except Exception` — ι-B1과 같은 결. `(UnicodeDecodeError, T3DParseError)`로 좁힘. |
| κ-B3 | dual-glob 중복 (main_window.py + resolver.py) — `load_folder` 반환 list 또는 `registered_paths()` 도입. |
| FEAT-26 | 충돌 검출 리포트 — `resolver.conflicts()` + status bar/도크 표시. κ-A1 가시화. |
| FEAT-27 | External-ref 네비 — inspector 클릭 시 해당 파일 새 탭으로 + 노드 이동. FEAT-3 + FEAT-10 + F5 합성. |
| FEAT-28 | CLI `t3dgraph resolve <folder>` — 이름→파일/충돌/미해결 JSON dump. RigVM CI 감사. |

### improver Slice λ 리뷰 findings (2026-05-22, master f3e708a) — 미처리

| ID | 내용 |
| --- | --- |
| **λ-A1** | 다른 탭 깊은 위치 클릭 시 depth 점프 누락 — `_on_minimap_click` 분기에서 setCurrentIndex만 되고 jump_to 안 됨. 사용자 2회 클릭 필요. 단일 경로로 통합. |
| λ-A2 | 멀티 ContainedGraph 자식이 minimap에 미표시 — `extra_subgraphs`(C-A1으로 보존) 미렌더. 모델은 다중 보존하는데 UI 절반. |
| λ-A3 | minimap `_render_children` 재귀 깊이 cap 부재 — C-A2/dependency_tree와 같은 결. defensive cap 통일. |
| λ-B1 | `stack._cur_root`/`_paths` private access — η-B3 `current_root_index()` getter 부재가 실제 비용으로 증명. |
| λ-B2 | `_click_for_test` 3번째 프로덕션 노출 (η-B2 패턴 BreadcrumbBar·NodeItem 이어) — `tests/helpers.py` 분리 시기. |
| λ-B3 | `NavigablePanel` 상속 의문 — `navigate_requested` 미사용, 자체 `location_clicked` 사용. 상속 끊거나 베이스 일반화. |
| FEAT-29 | minimap 노드 검색·필터 — 트리 상단 검색 박스 + 하이라이트. |
| FEAT-30 | minimap 우클릭 컨텍스트 메뉴 — 새 탭으로/북마크/경로 복사. AssetResolver 연동 시 "external-ref 네비게이션"도. |
| FEAT-31 | 형제 서브그래프 빠른 점프 단축키 — `Alt+Right`/`Alt+]` 등. FEAT-9 연장. |

**메모 (improver 권고):** B1·B2는 누적 신호들의 일관 재확인. 정리 슬라이스 범위 — `cli.py` + `main_window.py` + `panels` 한 묶음.

### improver Slice μ 리뷰 findings (2026-06-01, master ddfa8ea) — 미처리

batch ⑨ Spec 1, F10(핀 타입별 색) + F12(disclosure ▶/▼).

| ID | 내용 |
| --- | --- |
| **μ-A1** | 팔레트 로드 실패 무음 처리 — `MainWindow.__init__`에서 `PinColorTable.load()`가 bare `except`로 잡혀 `self.pin_colors = None`이 되면 모든 핀이 노랑 fallback. 사용자가 TOML을 깼는지 알 수 없음. statusBar 메시지/로그/리셋 유도 다이얼로그 중 최소 하나 필요. **위중도 최상** (디버깅 단서 0, 지원 부담 누적). |
| μ-A2 | 사용자 팔레트 파일 열기·재로드 액션 부재 — "리셋"만 있어 커스터마이즈하려면 `%APPDATA%/t3dgraph/pin_colors.toml`을 수동으로 찾아야 함. "보기 → 팔레트 파일 위치 열기" + "팔레트 재로드". |
| μ-A3 | disclosure 화살표 hit-zone이 깊은 depth에서 0 이하로 축소 — output 핀 zone이 `indent = 18 + depth*12`이라 nested struct에서 x0 > x1. 최소 폭 보장 또는 zone swap 가드. |
| μ-B1 | 번들 카피 로직 중복 — `load`·`reset_user_file` 두 메서드에 동일 3줄 복붙. `_copy_bundle_to(user_file)` private helper로 추출. |
| μ-B2 | `collect_pin_rows`의 PinRow 재구성 — 명시 인자 5개 대신 `dataclasses.replace(cur, has_dot=False)`. 필드 누락 위험 제거. |
| μ-B3 | 화살표 레이아웃 매직 넘버 산재 — `18 + depth*12`, `indent-14`, `PIN_RADIUS+2`, `NODE_WIDTH-indent+2`를 `_INDENT_BASE`/`_INDENT_PER_DEPTH`/`_ARROW_GLYPH_OFFSET`/`_ARROW_ZONE_PAD` 모듈 상수로. ν 슬라이스 링크 레이아웃과의 충돌 감축. |
| FEAT-32 (μ-C1) | 핀 dot hover tooltip — `FRotator → struct (#5B8FF9)`, `TArray<bool> → bool (외곽선=array)` 룩업 결과 노출. 학습·디버깅 양쪽. |
| FEAT-33 (μ-C2) | 팔레트 범례(legend) 도크 — 카테고리별 색 스와치 + 라벨(exec/bool/int/float/name/string/struct/object/default + array outline). 신규 사용자 학습 곡선 단축. |
| FEAT-34 (μ-C3) | 사용자 TOML hot-reload — `QFileSystemWatcher`로 외부 편집기 저장 시 자동 재로드 + scene rebuild. 팔레트 튜닝 워크플로 끊김 제거. |

### improver Slice ξ 리뷰 findings (2026-06-01, master 806653a) — 미처리

batch ⑨ Spec 1, F15(인스펙터 폭 안정).

| ID | 내용 |
| --- | --- |
| ξ-A1 | column-0 indent-aware truncation 누락 — `_apply_truncation_tooltips`의 `fm.horizontalAdvance(text) > live_w - _CELL_PAD_PX` 비교가 트리 들여쓰기를 빼지 않아 깊은 subpin에서 텍스트는 잘리는데 툴팁 미부여. 리뷰어 I-3 동일. `QStyleOptionViewItem` 들여쓰기 반영. |
| ξ-A2 | 컬럼 폭 영속화 부재 — Interactive 드래그 가능해졌으나 앱 재시작 시 디폴트(140·160·70·120·90)로 리셋. QSettings 저장·복원. 리뷰어 I-4 동일. |
| ξ-B1 | `_CELL_PAD_PX = 12`이 스타일 무관 추정치 — Qt 스타일별 셀 패딩 차로 한두 픽셀 차이로 툴팁 잘못 부여/누락. `style().pixelMetric(QStyle.PM_HeaderMargin)` 또는 `viewOptions().rect`로 동적 산출. |
| ξ-B2 | `_on_section_resized` 전체 재평가가 O(items × columns) — 드래그 매 픽셀마다 모든 트리 아이템 순회. 큰 노드(수백 핀)에서 끊김. `_resize_logical` 한 컬럼만 갱신 또는 `QTimer.singleShot(0, ...)`로 코얼레스. |
| FEAT-35 (ξ-C1) | header 컨텍스트 메뉴 — 컬럼 가시성 토글. 우클릭으로 "상태"·"방향" 등 비주력 컬럼 숨기기. 좁은 도크에서 핀명·타입 가독성 회복. |
| FEAT-36 (ξ-C2) | inspector 내부 필터 박스 — 핀 이름·타입 부분일치 필터. 핀 수백 개짜리 노드(Orion rig)에서 핵심. |

**메모 (improver 권고):** μ-A1은 사용자 직격 — Spec 2 진입 시 우선 검토 또는 별도 핫픽스 슬라이스 후보. μ-B3는 ν 슬라이스와 같은 파일(items.py) 편집이 임박했으므로 ν 머지 후 즉시 처리하는 게 충돌·재작업 비용 최소.

### improver Slice ν 리뷰 findings (2026-06-01, master 71208c2) — 미처리

batch ⑨ Spec 1, F13(베지어)·F18(드래그+LayoutOverrides)·F19(노드 컨텍스트 메뉴).

| ID | 내용 |
| --- | --- |
| ν-A1 | `_root_tokens`가 `id(root_graph)` 기반 — 동일 graph 객체 reopen 시 `clear_by_prefix`로 LayoutOverrides 제거 후 토큰 누락. 사용자가 위치 정보를 의도치 않게 잃을 수 있음. 구현자가 본인 메시지에서 `_tab_tokens` 리네이밍 + 탭 단위 키잉 제안. 탭 인덱스/UUID 기반 키로 전환. |
| **ν-A2** | 노드 위치 영속화 부재 — `LayoutOverrides`가 세션 메모리에만. 앱 재시작 시 드래그 결과 전부 휘발. F18의 핵심 가치(레이아웃 튜닝)가 한 세션 한정. `.t3dgraph/layouts/{root_token}.json` 또는 QSettings 영속화 필요. Spec §9.5에서 "다음 라운드" deferred로 명시했으나 사용 가치 직격이라 다음 batch 우선 후보. |
| ν-A3 | 드래그 시 모든 링크 O(L) 풀스캔 — `_update_links_for_node`가 1픽셀 드래그마다 전체 `_links` 순회. Orion 규모(수백 핀·수천 링크)에서 끊김 가능. 구현자도 본인 인지. `_links_by_node: dict[str, list[LinkItem]]` 인덱스로 O(degree). |
| ν-B1 | 핀 트리 walk 중복 — `MainWindow._collect_node_pin_paths` vs `items.collect_pin_rows` 두 곳에서 재귀. 세 번째 등장(F2 dependency_tree 등) 시 drift 확실. `base/graph_model.py` 또는 `base/paths.py`에 `iter_pin_paths(node) -> Iterator[str]` 단일 helper. |
| ν-B2 | `_links` 5-튜플 깨지기 쉬움 — `(link_item, s_node, s_sub, d_node, d_sub)`이 호출부마다 다르게 언팩(`_ss`/`_ts` 무시 또는 풀 언팩). `dataclass LinkEntry` 또는 `NamedTuple`로 명명. |
| ν-B3 | `graph_key` 문자열 concat의 escape 없음 — `f"{token}/{label}/{parent}"`이 label에 `/` 들어가면 키 충돌 (ContainedGraph label·parent_node 이름에 슬래시). 튜플 키 또는 `urllib.parse.quote` 적용. |
| FEAT-37 (ν-C1) | 다중 선택 드래그 — `ItemIsMovable` 노드별인데 멀티 선택 시 묶음 이동 안 됨. 표준 그래프 에디터 UX(서브트리 묶어 재배치). `QGraphicsScene` 멀티 선택 + 그룹 드래그. |
| FEAT-38 (ν-C2) | 드래그/메뉴 액션 Undo/Redo — `QUndoStack` + `MovedCommand`·`ResetPositionCommand`·`ExpandedNodeCommand`. `Ctrl+Z`/`Ctrl+Shift+Z` 매핑. F19 컨텍스트 메뉴와 자연 결합. |
| FEAT-39 (ν-C3) | 자동 레이아웃(Sugiyama/dagre) — `node.position` 없을 때 폴백 그리드 가독성 낮음. `networkx`/`graphviz` "보기 → 자동 정렬". 첫 열림 인상 개선. |

**메모 (improver 권고):** **ν-A2 영속화**가 사용 가치 직격(드래그한 의미 휘발) → Spec 2와 묶거나 단독 핫픽스 슬라이스로 격상 권장. **ν-A1·ν-A3**는 같은 `main_window.py`·`scene.py`를 만지므로 ν-A2 슬라이스에 동승. **ν-B1**은 F19/F2 양쪽이 같은 walk 패턴 — 정리 슬라이스 1순위.

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
