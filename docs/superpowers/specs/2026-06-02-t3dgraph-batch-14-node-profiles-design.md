# t3dgraph batch ⑭ — NodeStyleProfile 데이터 주도 설계 문서

- **작성일**: 2026-06-02
- **상태**: 사용자 승인 — 직접 디스패치
- **모(母) 스펙**: `2026-05-19-t3d-rig-graph-tool-design.md`
- **이전 사이클**: batch ⑬ (`g15` 머지까지, 사용자 피드백 F21~F33 처리)

---

## 1. 동기

`NodeItem`이 클래스별 if-분기로 부풀고 있음:
- `RigVMVariableNode` → var 배지
- `RigVMCollapseNode`/`RigVMFunctionReferenceNode` → chevron 상태
- (예상) `RigVMFunctionEntryNode`/`RigVMFunctionReturnNode` → 단방향 layout
- (예상) `RigVMRerouteNode` → passthrough 시각

코드 분기 누적 → 신규 노드 클래스 추가 시 매번 PR 필요. UE 플러그인·사용자 커스텀 노드는 처리 불가.

**해결**: 데이터 주도 `NodeStyleProfile` — TOML 설정에 클래스별 시각/동작 노브. 신규 클래스 = TOML 한 줄 추가. 코드 변경 0.

---

## 2. 범위

| 슬라이스 | 대상 |
|---|---|
| **k1** | `NodeStyleProfile` 자료구조 + `NodeProfileTable` 로더 + 번들 TOML + 사용자 파일 마이그레이션 |
| **k2** | `NodeItem`이 profile 룩업해 시각 분기 (`show_var_badge`·`always_show_chevron`·`chevron_state_aware`) — 기존 if-분기 제거 |
| **k3** | `layout_hint` 처리 — `outputs_only`/`inputs_only`/`passthrough` |

**Out-of-scope**:
- Python escape hatch 서브클래스 (k4 후보, 필요 시점에)
- 실제 신규 노드 분기 추가 (k2·k3가 기존 분기를 profile로 옮길 뿐, 새 노드 처리는 user TOML 편집으로)

---

## 3. NodeStyleProfile 자료구조

`src/t3dgraph/core/app/node_profiles.py` (신규):

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class NodeStyleProfile:
    show_var_badge: bool = False
    always_show_chevron: bool = False
    chevron_state_aware: bool = False
    tooltip_when_no_subgraph: str | None = None
    layout_hint: str = "default"   # default | outputs_only | inputs_only | passthrough


_DEFAULT_PROFILE = NodeStyleProfile()


class NodeProfileTable:
    def __init__(self, profiles: dict[str, NodeStyleProfile]):
        self._by_suffix = profiles

    def resolve(self, cls_suffix: str) -> NodeStyleProfile:
        return self._by_suffix.get(cls_suffix, _DEFAULT_PROFILE)

    @classmethod
    def load(cls) -> "NodeProfileTable": ...   # 번들 → 사용자 파일 흐름은 PinColorTable 패턴 차용
```

---

## 4. 번들 TOML

`src/t3dgraph/core/app/resources/node_profiles.toml` (신규):

```toml
# t3dgraph 노드 클래스별 시각/동작 프로필
# 사용자가 ~/.config/t3dgraph/node_profiles.toml 편집해 확장 가능 (코드 변경 0).

[profile.RigVMVariableNode]
show_var_badge = true

[profile.RigVMCollapseNode]
always_show_chevron = true
chevron_state_aware = true

[profile.RigVMFunctionReferenceNode]
always_show_chevron = true
chevron_state_aware = true
tooltip_when_no_subgraph = "함수 참조 — 함수 본문이 외부 파일에 있음. 에셋 폴더 열기로 함수 라이브러리 등록 필요."

[profile.RigVMFunctionEntryNode]
layout_hint = "outputs_only"

[profile.RigVMFunctionReturnNode]
layout_hint = "inputs_only"

[profile.RigVMRerouteNode]
layout_hint = "passthrough"
```

---

## 5. NodeProfileTable.load (사용자 파일 마이그레이션)

PinColorTable과 동일 패턴:
- 사용자 파일 없으면 번들 풀 카피
- 있으면 사용자 파일 우선 (전체 덮어쓰기 X, 사용자 자유 편집)
- 미정의 클래스는 `_DEFAULT_PROFILE` 반환

```python
@classmethod
def load(cls) -> "NodeProfileTable":
    user_file = cls._user_dir() / "node_profiles.toml"
    if not user_file.exists():
        user_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cls._bundle_path(), user_file)
    with user_file.open("rb") as f:
        data = tomllib.load(f)
    profiles = {}
    for suffix, fields in data.get("profile", {}).items():
        profiles[suffix] = NodeStyleProfile(**fields)
    return cls(profiles)
```

`_user_dir`·`_bundle_path` 시그니처는 PinColorTable 그대로 차용.

---

## 6. NodeItem에서 profile 사용 (k2)

`NodeItem.__init__`에 `profile: NodeStyleProfile | None = None` 인자 추가. MainWindow가 `NodeProfileTable.load()` 한 번 → 매 NodeItem 생성 시 `profile=profile_table.resolve(cls_suffix)` 전달.

기존 if-분기 변환:

```python
# 기존
if (node.cls or "").rsplit(".", 1)[-1] == "RigVMVariableNode":
    # var 배지 그리기
    ...

# 변경
if profile.show_var_badge:
    # var 배지 그리기 (동일 로직)
    ...
```

`_function_entry_state`도 profile 기반:

```python
def _function_entry_state(self):
    if not profile.always_show_chevron:
        return None
    if self.node.subgraph is not None:
        return QColor("#90EE90"), "더블클릭하여 서브그래프 진입"
    if profile.chevron_state_aware:
        if profile.tooltip_when_no_subgraph:
            return QColor("#FFD700"), profile.tooltip_when_no_subgraph
        return QColor("#888888"), "내부 그래프 데이터 없음"
    return QColor("#FFD700"), "더블클릭하여 서브그래프 진입"
```

---

## 7. layout_hint 처리 (k3)

| hint | 동작 |
|---|---|
| `default` | 기존 — 좌/우 핀 양쪽 표시 |
| `outputs_only` | 좌측(input) 영역 폭 0으로 축소, 모든 핀 우측 정렬. Entry 노드. |
| `inputs_only` | 우측(output) 영역 폭 0, 모든 핀 좌측 정렬. Return 노드. |
| `passthrough` | 단일 행, 최소 라벨. Reroute 노드. |

NodeItem 렌더링 루프에서 `is_input_side` 계산에 layout_hint 반영:

```python
def _resolve_input_side(self, row_direction: str, hint: str) -> bool:
    if hint == "outputs_only":
        return False   # 모든 핀 우측
    if hint == "inputs_only":
        return True    # 모든 핀 좌측
    return row_direction != "output"   # 기존 로직
```

Passthrough는 별도 처리 (라벨 1줄, 노드 폭 축소).

---

## 8. 슬라이스 의존

| 슬라이스 | 의존 | 비고 |
|---|---|---|
| k1 자료구조·로더 | 없음 | 즉시 |
| k2 NodeItem profile 사용 | k1 머지 후 | 기존 분기 제거 |
| k3 layout_hint | k2 머지 후 | k2가 profile 받는 인프라 깔린 후 |

---

## 9. PRESERVE-ALL

전 슬라이스 시각/동작 분기를 데이터 주도로 옮길 뿐 — 모델·노드·링크 보존 ✅. 기존 사용자 경험 동일하되 확장성 ↑.

---

## 10. 사용자 노드 확장 시나리오 검증

**사례 1**: 사용자가 UE에서 `MyCustomNode` 플러그인 추가, var 배지 표시 원함.

```toml
# ~/.config/t3dgraph/node_profiles.toml에 추가
[profile.MyCustomNode]
show_var_badge = true
```

→ t3dgraph 재시작 → 적용. 코드 PR 0.

**사례 2**: `MyDispatchHelper` 노드를 함수처럼 진입 가능하게.

```toml
[profile.MyDispatchHelper]
always_show_chevron = true
chevron_state_aware = true
tooltip_when_no_subgraph = "Helper 구현 필요"
```

→ 적용.

---

## 11. Out-of-scope (다음 라운드)

- **Python escape hatch**: 완전한 커스텀 렌더링(예: 외부 이미지 핀 표시)이 필요한 사용자를 위한 NodeItem 서브클래스 등록 메커니즘. 현재는 profile data만으로 부족한 케이스 없음.
- **profile editor UI**: GUI 메뉴에서 TOML 직접 편집 대신 form으로 편집. 다음 라운드.
- **profile validation**: 사용자가 잘못된 키 입력 시 친절한 에러. 다음 라운드.
