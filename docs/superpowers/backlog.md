# t3dgraph 백로그

> improver improvement-review에서 나온 **미처리 findings**와 향후 기능 아이디어를 누적·보존하는 문서.
> `.improvement-review/findings.md`는 매 리뷰 사이클마다 덮어쓰이므로, 보존이 필요한 항목을 여기에 옮겨 둔다.
>
> **처리 규칙 (중요):** 백로그 항목을 실제로 착수할 때는 **반드시 그 시점의 코드를 다시 읽어 finding이 여전히 유효한지 재검토**한다. Phase가 진행되며 코드가 바뀌어 finding이 이미 해소됐거나 형태가 달라졌을 수 있다 — 옛 finding을 그대로 적용하지 말 것.

상태: 2026-05-19 기준. 처리 순서 — Phase 2b → Phase 2c 완료 후 별도 정리 batch로 편성.

---

## improver Phase 1.5 리뷰 findings (2026-05-19) — 미처리

| ID | 내용 |
| --- | --- |
| P1.5-A1 | `ValueParseError`에 구조화된 `pos` 속성 부재 — `T3DParseError`의 col이 값 시작만 가리킴. `pos`를 예외 속성으로 노출하면 위치가 정밀해짐. |
| P1.5-B1 | `cli._read_text` 인코딩 로직을 `core/t3d`로 이동(뷰어와 공유). → Phase 2a에서 실제 중복으로 현실화, 아래 P2a-B1과 동일 사안. |

## improver Phase 2a 리뷰 findings (2026-05-19) — 미처리

| ID | 내용 |
| --- | --- |
| P2a-A1 | `Position` 누락 노드 폴백 처리. |
| P2a-A2 | `cli.py`가 `T3DParseError`를 포착하지 않음 — 미처리 시 스택트레이스 노출. |
| **P2a-B1** | **`cli._read_text` ↔ `controller._read_text` 실제 중복 코드 → `core/t3d/encoding.py`로 통합** (핵심 — 두 리뷰 사이클 연속 지적). |
| P2a-B2 | `show_error`를 `AbstractGraphView` 계약으로 승격(현재 `getattr` 덕타이핑). |
| P2a-B3 | 핀 경로(`"Node.Pin.Sub"`) 파싱 헬퍼 중앙화 — 현재 `flow.py`·`scene.py`·`inspector_panel.py` 등에 `split(".")` 로직 분산. |

## 기능 아이디어 (spec §3.3 향후 확장)

| ID | 내용 |
| --- | --- |
| FEAT-1 | `--lenient` 파싱 플래그 — 불량 객체 skip + 경고 누적. Phase 1 계획에서 명시 deferred. |
| FEAT-2 | round-trip `.t3d` 익스포트 — 무손실 모델 → 텍스트 직렬화. |
| FEAT-3 | 에셋 단위 교차 파일 resolver — `external_refs` 해소(spec §3.3 seam). |
| FEAT-4 | CLI `--json` 구조화 출력 — 파이프라인 컴포넌트화. |

---

## 처리 계획

1. **원래 순서 유지** — Phase 2b → Phase 2c 진행 (백로그를 중간에 끼우지 않음).
2. Phase 2c 완료 후 위 항목들을 **별도 정리 batch 계획**으로 편성한다.
3. 착수 시 위 "처리 규칙"대로 각 finding을 **당시 코드 기준으로 재검토** — 유효성 확인 후 계획에 반영.
