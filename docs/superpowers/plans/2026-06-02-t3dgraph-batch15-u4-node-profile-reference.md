# batch ⑮ u4 — 노드 프로필 참조 플로팅 패널 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 보기 → "노드 프로필 참조" 메뉴 액션 → 플로팅 윈도우. NodeProfileTable의 정의된 클래스별 시각/동작 노브 시각화. 사용자 TOML 편집 가이드.

**Pre-condition:** master 최신. NodeProfileTable 존재 (batch ⑭ k1).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/node_profile_reference.py` | 신규 (`NodeProfileReferenceDialog`) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (메뉴 액션) |
| `tests/app/test_node_profile_reference.py` | 신규 |

---

## Task 1: NodeProfileReferenceDialog 구현

**Files:**
- Create: `src/t3dgraph/core/app/node_profile_reference.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_node_profile_reference.py`

- [ ] **Step 1: 테스트**

```python
"""u4 — NodeProfileReferenceDialog 단위."""
from PySide6.QtWidgets import QTableWidget

from t3dgraph.core.app.node_profiles import NodeProfileTable
from t3dgraph.core.app.node_profile_reference import NodeProfileReferenceDialog


def test_dialog_shows_profile_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = NodeProfileTable.load()
    dlg = NodeProfileReferenceDialog(table)
    qtbot.addWidget(dlg)
    profile_table = dlg.findChild(QTableWidget, "profile_table")
    assert profile_table is not None
    # 번들에 정의된 6개 클래스 (Variable·Collapse·FunctionRef·Entry·Return·Reroute)
    assert profile_table.rowCount() == len(table._by_suffix)


def test_dialog_columns(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = NodeProfileReferenceDialog(NodeProfileTable.load())
    qtbot.addWidget(dlg)
    profile_table = dlg.findChild(QTableWidget, "profile_table")
    # 컬럼: 클래스 suffix + 5 필드
    assert profile_table.columnCount() == 6


def test_dialog_non_modal(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(NodeProfileTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = NodeProfileReferenceDialog(NodeProfileTable.load())
    qtbot.addWidget(dlg)
    assert dlg.isModal() is False
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/node_profile_reference.py`:

```python
"""노드 프로필 참조 — 클래스별 시각/동작 노브 시각화."""
from __future__ import annotations
from dataclasses import fields as _fields

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton,
)

from .node_profiles import NodeProfileTable, NodeStyleProfile


class NodeProfileReferenceDialog(QDialog):
    """플로팅 노드 프로필 참조."""

    def __init__(self, profile_table: NodeProfileTable, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("노드 프로필 참조")
        self.setModal(False)
        self.resize(760, 480)
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel(
            "정의된 클래스별 시각/동작 프로필. "
            "사용자 파일(~/.config/t3dgraph/node_profiles.toml) 편집으로 확장 가능."
        ))

        field_names = [f.name for f in _fields(NodeStyleProfile)]
        cols = ["class suffix"] + field_names
        self._table = QTableWidget(0, len(cols))
        self._table.setObjectName("profile_table")
        self._table.setHorizontalHeaderLabels(cols)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        for suffix, profile in profile_table._by_suffix.items():
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(suffix))
            for c, name in enumerate(field_names, start=1):
                value = getattr(profile, name)
                if value is None:
                    text = "—"
                elif isinstance(value, bool):
                    text = "✓" if value else ""
                else:
                    text = str(value)
                self._table.setItem(r, c, QTableWidgetItem(text))
        outer.addWidget(self._table)

        # 하단 버튼 (TOML 파일 열기)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        open_btn = QPushButton("사용자 TOML 위치")
        open_btn.clicked.connect(self._show_user_file_path)
        btn_row.addWidget(open_btn)
        outer.addLayout(btn_row)
        self._profile_table = profile_table

    def _show_user_file_path(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        path = self._profile_table._user_dir() / "node_profiles.toml"
        QMessageBox.information(
            self, "사용자 TOML 위치",
            f"사용자 파일 경로:\n{path}\n\n"
            "이 파일을 편집해 신규 클래스 프로필 추가 또는 기존 갱신 가능.\n"
            "예시:\n"
            "[profile.MyCustomNode]\n"
            "show_var_badge = true\n"
            "layout_hint = \"outputs_only\"",
        )
```

- [ ] **Step 3: MainWindow 메뉴 액션**

```python
def _build_menu(self):
    # ... 기존 ...
    view_menu.addAction("노드 프로필 참조").triggered.connect(self._on_show_node_profile_reference)

def _on_show_node_profile_reference(self) -> None:
    from .node_profile_reference import NodeProfileReferenceDialog
    if not hasattr(self, "_node_profile_ref_dialog") or self._node_profile_ref_dialog is None:
        self._node_profile_ref_dialog = NodeProfileReferenceDialog(self.node_profiles, parent=self)
    self._node_profile_ref_dialog.show()
    self._node_profile_ref_dialog.raise_()
    self._node_profile_ref_dialog.activateWindow()
```

- [ ] **Step 4: 실행 + 회귀**

Run: `pytest tests/app/test_node_profile_reference.py -v`
Expected: 3 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

보기 → "노드 프로필 참조" → 테이블 (6 클래스 × 6 컬럼: suffix · show_var_badge · always_show_chevron · chevron_state_aware · tooltip · layout_hint). "사용자 TOML 위치" 버튼 클릭 → 경로·예시 표시.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_node_profile_reference.py src/t3dgraph/core/app/node_profile_reference.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): node profile reference floating dialog"
```

## 완료 후

사용자가 정의된 프로필 시각 확인 + TOML 파일 경로 안내. 신규 클래스 추가 비용 더 낮아짐.
