# t3dgraph batch ⑥ — UI 단축키 + 멀티 탭 (FEAT-9, FEAT-10) 설계

- **작성일**: 2026-05-22 자율 사이클

## 범위

- **FEAT-9** 뒤로가기/위로 가기 단축키 — `Alt+←`/`Backspace`→`graph_stack.pop()`, `Alt+↑`→ 한 단계 위. UI 키보드 친화.
- **FEAT-10** 멀티 파일 탭 — `GraphStack.open_root`/`roots()`/`select_root`가 이미 받쳐 줌. 상단 `QTabBar`로 노출, 각 탭은 한 루트 그래프.

## 슬라이스

- **η** FEAT-9 + FEAT-10 일괄. 두 항목 모두 `MainWindow`의 작은 추가.

## 아키텍처

- `_build_shortcuts()` 메서드 추가 — `QShortcut` 4종(`Alt+←`, `Alt+→`, `Alt+↑`, `Backspace`).
- `_build_tab_bar()` — `QTabBar`(중앙 위, 브레드크럼 위에). `GraphStack.open_root` 시 탭 추가, `select_root`로 전환. 탭 닫기는 `GraphStack`에 `close_root(index)` 추가.
- 한 탭 안에서 브레드크럼 + 캔버스 동작 동일.

## 불변식

- PRESERVE-ALL/INFO: 변경 ✗.
- 탭 닫기로 *루트 GraphModel 인스턴스*는 GC 가능 — 명시 의도.

## 비목표

- 탭별 인스펙터/분석 상태 보존 — 본 batch는 단순 라우트 전환. 상태 보존은 다음 cycle.
