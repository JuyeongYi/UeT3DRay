# batch ⑮ x3 — CustomProperties skip 정규식 좁힘 + .gitattributes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** x1 improver findings 2건 정리.

- **x1-A1**: `^CustomProperties\s+\w+\s*\(` 너무 넓음 — `CustomProperties Pin (` 으로 좁히고 다른 변종은 `T3DObject.skipped_directives: list[str]`에 raw 보존 (diagnostic). 비-RigVM plugin 도입 시 silent 손실 방지.
- **x1-B1**: 파일 전체 diff 노이즈 — `.gitattributes`에 `*.py text eol=lf` 명시로 향후 review noise 차단.

**Pre-condition:** master `453c044`, 660 tests (x1+x2 머지 후).

C1(structured MacroCall)은 후순위 — 첫 consumer 등장 시.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/objects.py` | 수정 (정규식 좁힘 + `skipped_directives` 보존) |
| `.gitattributes` | 신규 (line ending normalize) |
| `tests/core/t3d/test_custom_properties_skip.py` | 수정 (Pin은 skipped_directives에, Pin 외 형은 raw 보존 검증) |

---

## Task 1: x1-A1 — skip 정규식 좁힘 + skipped_directives 보존

**Files:**
- Modify: `src/t3dgraph/core/t3d/objects.py`
- Modify: `tests/core/t3d/test_custom_properties_skip.py`

- [ ] **Step 1: 테스트 갱신**

`tests/core/t3d/test_custom_properties_skip.py` — 기존 `test_custom_properties_other_subtypes_skipped` 의도 변경:

```python
def test_pin_directive_recorded_in_skipped_directives() -> None:
    """Pin directive는 skip하되 raw line은 skipped_directives에 보존."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Pin (PinId=AAA,PinName="P1",)\n'
        '   ModelNodePath="N"\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert "CustomProperties Pin" in " ".join(objs[0].skipped_directives)
    assert "PinId=AAA" in " ".join(objs[0].skipped_directives)
    assert "ModelNodePath" in objs[0].properties


def test_non_pin_customproperties_also_recorded() -> None:
    """`CustomProperties Foo (...)` 같은 변종도 raw 보존 — 이전엔 silent skip."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Foo (Something=1)\n'
        '   ModelNodePath="N"\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert any("CustomProperties Foo" in d for d in objs[0].skipped_directives)
    assert objs[0].properties.get("ModelNodePath") is not None
```

(기존 `test_multiple_custom_properties_lines_all_skipped`은 properties 비교만 했으므로 그대로 통과; `test_custom_properties_other_subtypes_skipped`는 이름 그대로 둬도 되고 위 두 케이스로 대체 가능.)

- [ ] **Step 2: objects.py — skipped_directives 필드 + skip 분기**

`T3DObject` 데이터클래스에 필드 추가:

```python
@dataclass
class T3DObject:
    cls: str | None
    name: str | None
    export_path: str | None
    header_raw: str
    properties: dict[str, Value] = field(default_factory=dict)
    children: list["T3DObject"] = field(default_factory=list)
    line: int = 0
    skipped_directives: list[str] = field(default_factory=list)
```

`_CUSTOM_PROPERTIES_DIRECTIVE` 그대로 두되 skip 분기 동작 변경:

```python
            elif _CUSTOM_PROPERTIES_DIRECTIVE.match(ln.text):
                # UE EdGraph inline directive (CustomProperties Pin (...), Foo (...), 등).
                # RigVM model 인터프리트와 무관해 properties에 안 넣되, raw line은
                # 진단용으로 보존 — 향후 비-RigVM plugin이 가져갈 수 있다.
                obj.skipped_directives.append(ln.text)
                pos += 1
```

- [ ] **Step 3: 실행**

Run: `pytest tests/core/t3d/test_custom_properties_skip.py -v`
Expected: 신규 2 + 기존 통과.

Run: `pytest tests -v`
Expected: 전체 통과 (660 + 신규 2 = 662).

- [ ] **Step 4: 커밋**

```bash
git add tests/core/t3d/test_custom_properties_skip.py src/t3dgraph/core/t3d/objects.py
git commit -m "feat(t3d): preserve CustomProperties directives in T3DObject.skipped_directives (x3-A1)"
```

---

## Task 2: x1-B1 — .gitattributes line ending normalize

**Files:**
- Create: `.gitattributes`

- [ ] **Step 1: .gitattributes 작성**

저장소 루트 `.gitattributes`:

```
* text=auto eol=lf
*.py text eol=lf
*.md text eol=lf
*.toml text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.t3d binary
*.T3D binary
```

(`.t3d`/`.T3D`는 UTF-16/혼합 인코딩이라 binary 명시 — diff/merge 비활성으로 안전.)

- [ ] **Step 2: 기존 파일 line ending 재정규화 (선택)**

```bash
git add --renormalize .
git status   # 변경 없거나 일부 *.py가 eol 변환됨
```

변경이 있다면 별도 커밋:

```bash
git commit -m "chore: renormalize line endings to LF per .gitattributes"
```

변경이 없으면 skip (이미 LF).

- [ ] **Step 3: .gitattributes 커밋**

```bash
git add .gitattributes
git commit -m "chore: add .gitattributes for line-ending normalize (x3-B1)"
```

- [ ] **Step 4: 실행**

Run: `pytest tests -v`
Expected: 변동 없음 — 단지 git 메타.

---

## 무엇이 깨질 수 있나

| 위험 | 완화 |
|---|---|
| 기존 dataclass 인스턴스 의존 코드가 `skipped_directives` 필드 미설정 가정 | `default_factory=list`라 backward compatible. 외부 호출자 영향 없음 |
| `.gitattributes` 적용 후 모든 *.py가 갱신 보임 | renormalize 커밋이 한 번만 노이즈. 이후엔 clean diff |
| `.t3d binary` 처리로 grep/Read가 막힘 | binary는 `git diff` 표시만 영향. tool로 Read·Grep은 그대로 동작 |
| Windows 환경 사용자가 CRLF 자동 변환 기대 | `text=auto eol=lf`는 working tree에서는 OS 자동, 저장소에는 LF — 표준 패턴 |

## 완료 후

- EdGraph 변종 directive(`CustomProperties Foo (...)` 등) 정보가 raw로 보존되어 미래 plugin 활용 가능
- 향후 commit diff가 line ending 노이즈 없이 깨끗
