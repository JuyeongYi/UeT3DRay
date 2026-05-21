# t3dgraph batch ⑧ — 무거운 기능 (FEAT-2, FEAT-3, FEAT-11) 설계

- **작성일**: 2026-05-22 자율 사이클
- **주의**: 시간 여유에 따라 슬라이스별 발주. 데드라인 부담 시 우선순위 — ι > κ > λ.

## 범위

- **FEAT-2** round-trip `.t3d` 익스포트 — `GraphModel`+`T3DDocument` → 텍스트. 무손실 직렬화.
- **FEAT-3** 에셋 단위 교차 파일 resolver — `external_refs` 해소. 같은 폴더의 다른 `.t3d.txt`에서 참조 노드 찾기.
- **FEAT-11** 서브그래프 미니맵 / 위치 인디케이터 — 사이드 도크에 부모 트리 + 현재 위치 하이라이트.

## 슬라이스

| 슬라이스 | 내용 |
|---|---|
| ι | FEAT-2 round-trip |
| κ | FEAT-3 asset resolver |
| λ | FEAT-11 미니맵 |

세 슬라이스 독립. 각각 별도 발주.

## 아키텍처

### ι round-trip

`core/t3d/serializer.py` (신규) — `serialize_document(doc: T3DDocument) -> str`. 같은 객체 두 번 등장(declaration + definition 패턴) 보존. `core/t3d/document.parse_document` 의 역함수.

`GraphModel` → `T3DDocument`는 별도 (어차피 raw가 모두 보존됨 — `T3DObject` 모델 자체를 직렬화).

테스트: 샘플 t3d.txt를 parse → serialize → parse 다시 → 동일 GraphModel.

### κ asset resolver

`core/t3d/resolver.py` (신규) — `AssetResolver` 클래스. `register(path: Path, doc: T3DDocument)` + `resolve(ref_path: str) -> T3DObject | None`. 같은 폴더(또는 명시된 search path)의 다른 파일들을 lazy 등록.

UI: 파일 메뉴 "에셋 폴더 열기..." — 폴더 선택 → 모든 `.t3d.txt` 등록. external_refs를 GraphModel.external_refs 대신 resolve된 노드 참조로 patch.

### λ 미니맵

`core/app/minimap_panel.py` (신규) — 도크 패널. `GraphStack`을 시각화하는 트리 위젯. 부모/형제 서브그래프를 보여주고 현재 위치 표시. 클릭 시 jump_to.

## 비목표

- λ의 *축소 그래프* 미니맵(노드 위치 미리보기) — 본 cycle은 *트리 구조* 인디케이터만. 위치 미리보기는 다음 사이클.
- ι의 *증분* round-trip(편집된 부분만 출력) — 본 cycle은 *전체* 직렬화만.
