# batch ⑮ x1 — `CustomProperties Pin (...)` directive skip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** UE ControlRig T3D 직렬화의 `CustomProperties Pin (...)` directive 라인이 attribute parser에 들어가 폭발(`속성값 파싱 실패: 값 뒤에 남은 입력: ...`)하는 문제 제거.

**Repro 파일:** `Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D` line 78826/78827/78828 — `ControlRigGraphNode` 객체 내부 인라인 핀 메타데이터.

**원인 (확인됨):**
- 라인 형식: `CustomProperties Pin (PinId=GUID,PinName="...",PinType.PinCategory="real",...,LinkedTo=(NodeName GUID,),...)`
- 일반 `Key=Value` attribute가 아닌 별도 directive. attribute parser는 `CustomProperties Pin (PinId`까지를 key로, `GUID,PinName=...,...` 를 value로 잘못 가져감 → `parse_value`가 첫 GUID(scalar)만 정상 소비 → 나머지 `,...,...` 남음 → `ValueParseError("값 뒤에 남은 입력: ...")`.

**해법 (A — 사용자 승인):** `parse_block` 라인 디스패치에서 `^CustomProperties\s+\w+\s*\(` 패턴 라인을 attribute 처리 진입 전에 skip. EdGraph pin 메타데이터는 RigVM model 인터프리트에 사용 안 함 — 데이터 보존 불필요.

**Pre-condition:** master 최신 (사용자가 직전에 push). 현재 t3dgraph 테스트 전부 통과.

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/t3d/objects.py` | 수정 (`parse_block` 라인 dispatch에 directive skip 한 줄) |
| `tests/core/t3d/test_custom_properties_skip.py` | 신규 (재현 → fix 후 통과 + smoke) |

---

## Task 1: 재현 테스트 + skip 가드

**Files:**
- Modify: `src/t3dgraph/core/t3d/objects.py`
- Create: `tests/core/t3d/test_custom_properties_skip.py`

- [ ] **Step 1: 재현 + 가드 테스트**

```python
"""x1 — CustomProperties Pin directive skip."""
from pathlib import Path
import pytest
from t3dgraph.core.t3d.objects import parse_objects, T3DParseError
from t3dgraph.core.t3d.document import parse_document


_MINIMAL_REPRO = '''Begin Object Class=/Script/ControlRigDeveloper.ControlRigGraphNode Name="N"
   ModelNodePath="N"
   NodeGuid=4FBE5A5442B628385572068FB6616A3D
   CustomProperties Pin (PinId=20022E6E43C8E7C68AE8E8BB600B9F63,PinName="N.Result",PinFriendlyName="Result",Direction="EGPD_Output",PinType.PinCategory="real",PinType.PinSubCategoryObject=None,PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,LinkedTo=(RigUnit_SetTranslation_5 2466091D48C71EBA1D2EF4BB6AEED3DD,),PersistentGuid=00000000000000000000000000000000,bHidden=False,bOrphanedPin=False,)
End Object
'''


def test_custom_properties_pin_line_does_not_raise() -> None:
    """fix 전엔 'CustomProperties Pin (...)' 라인에서 폭발했음."""
    objs = parse_objects(_MINIMAL_REPRO)   # raise 없어야 통과
    assert len(objs) == 1
    obj = objs[0]
    assert obj.name == "N"
    # directive는 attribute로 보존 안 됨
    assert "CustomProperties Pin (PinId" not in obj.properties
    assert "CustomProperties" not in obj.properties
    # 정상 attribute는 살아 있음
    assert "ModelNodePath" in obj.properties
    assert "NodeGuid" in obj.properties


def test_multiple_custom_properties_lines_all_skipped() -> None:
    """여러 줄 directive 모두 silent skip."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Pin (PinId=AAA,PinName="P1",LinkedTo=(X Y,),)\n'
        '   CustomProperties Pin (PinId=BBB,PinName="P2",LinkedTo=(X Y,),)\n'
        '   CustomProperties Pin (PinId=CCC,PinName="P3",)\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert len(objs) == 1
    assert objs[0].properties == {}


def test_custom_properties_other_subtypes_skipped() -> None:
    """`CustomProperties Pin` 외 다른 subtype도 동일 패턴이면 skip (방어적)."""
    src = (
        'Begin Object Class=X Name="N"\n'
        '   CustomProperties Foo (Something=1)\n'
        '   ModelNodePath="N"\n'
        'End Object\n'
    )
    objs = parse_objects(src)
    assert objs[0].properties.get("ModelNodePath") is not None
    assert "CustomProperties Foo" not in objs[0].properties


@pytest.mark.skipif(
    not Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").exists(),
    reason="repro file 미존재 환경 — smoke test skip",
)
def test_simple_face_ctrlrig_file_parses() -> None:
    """실제 repro 파일이 폭발 없이 parse_document 통과."""
    raw = Path("Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D").read_text(
        encoding="utf-16",
    )
    doc = parse_document(raw)
    assert doc is not None
```

(`utf-16` 디코딩 가정: 사용자가 확인한 raw 파일이 UTF-16. 만약 UTF-8 BOM 가능성 있으면 `encoding="utf-16"` 실패 시 `utf-8-sig` fallback 추가 — 일단 utf-16 우선.)

- [ ] **Step 2: 재현 실행 (fix 전)**

Run: `pytest tests/core/t3d/test_custom_properties_skip.py -v`
Expected: `test_custom_properties_pin_line_does_not_raise` FAIL with `T3DParseError(..., "속성값 파싱 실패: 값 뒤에 남은 입력: ...")`.

- [ ] **Step 3: objects.py 가드**

`src/t3dgraph/core/t3d/objects.py` 파일 상단 정규식 추가:

```python
_CUSTOM_PROPERTIES_DIRECTIVE = re.compile(r'^CustomProperties\s+\w+\s*\(')
```

`parse_block` 의 라인 dispatch (현재 53~73 라인) 안 — `elif "=" in ln.text:` **앞**에 한 분기 추가:

```python
        while pos < len(lines):
            ln = lines[pos]
            if ln.text.startswith("Begin Object"):
                pos += 1
                child, _ = parse_block(ln)
                obj.children.append(child)
            elif ln.text == "End Object":
                pos += 1
                return obj, pos
            elif _CUSTOM_PROPERTIES_DIRECTIVE.match(ln.text):
                # UE EdGraph (ControlRigGraphNode 등) inline pin metadata.
                # `CustomProperties Pin (...)` directive — RigVM model 인터프리트와
                # 무관하므로 silently skip. 정상 Key=Value attribute가 아니라
                # 그대로 attribute parser에 넘기면 `값 뒤에 남은 입력` 폭발.
                pos += 1
            elif "=" in ln.text:
                ...
```

- [ ] **Step 4: fix 후 실행**

Run: `pytest tests/core/t3d/test_custom_properties_skip.py -v`
Expected: 3 passed + (smoke skip 또는 pass).

Run: `pytest tests -v`
Expected: 전체 통과 (기존 + 신규 3~4).

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

`Orion_WorkStation_Rig_Analysis/simple_face_CtrlRig.T3D` 열기 — 다이얼로그 폭발 없음. RigVM 노드들 정상 표시.

- [ ] **Step 6: 커밋**

```bash
git add tests/core/t3d/test_custom_properties_skip.py src/t3dgraph/core/t3d/objects.py
git commit -m "fix(t3d): skip 'CustomProperties Pin (...)' EdGraph directive lines (x1)"
```

---

## 무엇이 깨질 수 있나

| 위험 | 완화 |
|---|---|
| 정규식이 너무 좁아 `\tCustomProperties Pin (...)` 같은 들여쓰기 라인 놓침 | `tokenize_lines`가 indent 처리 후 `ln.text`를 strip된 형태로 줌(추정) — Step 2 재현 테스트가 보장. strip 안 한다면 정규식을 `^\s*CustomProperties\s+\w+\s*\(`로 |
| 향후 EdGraph 핀 정보가 필요한 기능 추가 시 데이터 손실 | 현재 사용처 없음(YAGNI). 필요 시 별도 dispatcher로 라우팅 추가 |
| UTF-16 파일이 다른 경로(`open_path`)에서 디코딩 실패 | smoke test가 직접 `utf-16` 디코드 — 만약 controller가 UTF-8 강제면 별도 슬라이스 필요 (이번 슬라이스 범위 밖) |
| `CustomProperties Pin` 줄 안에 줄바꿈이 있으면 한 라인 skip만으론 부족 | 현 사례는 한 줄 형태 — multi-line은 별도 케이스 |

## 완료 후

- `simple_face_CtrlRig.T3D` 같은 ControlRig EdGraph가 포함된 t3d 파일이 폭발 없이 열림
- EdGraph 핀 메타데이터는 모델에 들어오지 않음(RigVM 인터프리트 영향 없음)
- 향후 다른 `CustomProperties Xxx (...)` directive(예: K2Node 변수)도 동일 패턴이라면 자동 skip
