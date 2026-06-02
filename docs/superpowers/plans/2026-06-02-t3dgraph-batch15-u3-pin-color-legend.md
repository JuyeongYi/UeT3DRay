# batch ⑮ u3 — 핀 색 범례 플로팅 패널 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 보기 → "핀 색 범례" 메뉴 액션 → 플로팅 윈도우(QDialog, non-modal). palette 색 스와치 + bucket 매핑(cpp_type → palette key) 시각화.

**Pre-condition:** master 최신. PinColorTable 존재 (μ 슬라이스).

---

## File Structure

| 파일 | 변경 |
|---|---|
| `src/t3dgraph/core/app/pin_color_legend.py` | 신규 (`PinColorLegendDialog`) |
| `src/t3dgraph/core/app/main_window.py` | 수정 (메뉴 액션 + 핸들러) |
| `tests/app/test_pin_color_legend.py` | 신규 |

---

## Task 1: PinColorLegendDialog 구현

**Files:**
- Create: `src/t3dgraph/core/app/pin_color_legend.py`
- Modify: `src/t3dgraph/core/app/main_window.py`
- Create: `tests/app/test_pin_color_legend.py`

- [ ] **Step 1: 테스트**

```python
"""u3 — PinColorLegendDialog 단위."""
from PySide6.QtWidgets import QTableWidget, QLabel

from t3dgraph.core.app.pin_colors import PinColorTable
from t3dgraph.core.app.pin_color_legend import PinColorLegendDialog


def test_dialog_shows_palette_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = PinColorTable.load()
    dlg = PinColorLegendDialog(table)
    qtbot.addWidget(dlg)
    # palette 행 개수 = palette 키 개수
    palette_table = dlg.findChild(QTableWidget, "palette_table")
    assert palette_table is not None
    assert palette_table.rowCount() == len(table._palette)


def test_dialog_shows_bucket_rows(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    table = PinColorTable.load()
    dlg = PinColorLegendDialog(table)
    qtbot.addWidget(dlg)
    bucket_table = dlg.findChild(QTableWidget, "bucket_table")
    assert bucket_table is not None
    assert bucket_table.rowCount() == len(table._bucket)


def test_dialog_is_non_modal(qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(PinColorTable, "_user_dir",
                        classmethod(lambda cls: tmp_path))
    dlg = PinColorLegendDialog(PinColorTable.load())
    qtbot.addWidget(dlg)
    assert dlg.isModal() is False
```

- [ ] **Step 2: 구현**

`src/t3dgraph/core/app/pin_color_legend.py`:

```python
"""핀 색 범례 — palette + bucket 매핑 시각화 플로팅 패널."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter,
)

from .pin_colors import PinColorTable


class PinColorLegendDialog(QDialog):
    """플로팅 핀 색 범례. 메인 윈도우 종속."""

    def __init__(self, color_table: PinColorTable, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("핀 색 범례")
        self.setModal(False)
        self.resize(560, 460)

        splitter = QSplitter(Qt.Horizontal)

        # palette
        palette_box = QVBoxLayout()
        palette_box.addWidget(QLabel("Palette (이름 → 색)"))
        self._palette_table = QTableWidget(0, 3)
        self._palette_table.setObjectName("palette_table")
        self._palette_table.setHorizontalHeaderLabels(["키", "색", "HEX"])
        self._palette_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for key, color in color_table._palette.items():
            r = self._palette_table.rowCount()
            self._palette_table.insertRow(r)
            self._palette_table.setItem(r, 0, QTableWidgetItem(key))
            swatch = QTableWidgetItem("")
            swatch.setBackground(QBrush(color))
            self._palette_table.setItem(r, 1, swatch)
            self._palette_table.setItem(r, 2, QTableWidgetItem(color.name().upper()))
        palette_widget = self._wrap(palette_box, self._palette_table)
        splitter.addWidget(palette_widget)

        # bucket
        bucket_box = QVBoxLayout()
        bucket_box.addWidget(QLabel("Bucket (cpp_type → palette key)"))
        self._bucket_table = QTableWidget(0, 2)
        self._bucket_table.setObjectName("bucket_table")
        self._bucket_table.setHorizontalHeaderLabels(["cpp_type", "palette key"])
        self._bucket_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for cpp_type, key in color_table._bucket.items():
            r = self._bucket_table.rowCount()
            self._bucket_table.insertRow(r)
            self._bucket_table.setItem(r, 0, QTableWidgetItem(cpp_type))
            self._bucket_table.setItem(r, 1, QTableWidgetItem(key))
        bucket_widget = self._wrap(bucket_box, self._bucket_table)
        splitter.addWidget(bucket_widget)

        outer = QVBoxLayout(self)
        outer.addWidget(splitter)

    @staticmethod
    def _wrap(layout, *widgets):
        from PySide6.QtWidgets import QWidget
        w = QWidget()
        for widget in widgets:
            layout.addWidget(widget)
        w.setLayout(layout)
        return w
```

- [ ] **Step 3: MainWindow 메뉴 액션**

`main_window.py`:

```python
def _build_menu(self):
    # ... 기존 ...
    view_menu.addAction("핀 색 범례").triggered.connect(self._on_show_pin_color_legend)

def _on_show_pin_color_legend(self) -> None:
    from .pin_color_legend import PinColorLegendDialog
    if not hasattr(self, "_pin_color_legend_dialog") or self._pin_color_legend_dialog is None:
        self._pin_color_legend_dialog = PinColorLegendDialog(self.pin_colors, parent=self)
    self._pin_color_legend_dialog.show()
    self._pin_color_legend_dialog.raise_()
    self._pin_color_legend_dialog.activateWindow()
```

- [ ] **Step 4: 실행 + 회귀**

Run: `pytest tests/app/test_pin_color_legend.py -v`
Expected: 3 passed.

Run: `pytest tests -v`
Expected: 전체 통과.

- [ ] **Step 5: 수동 검증**

```bash
uv run t3dgraph-gui
```

보기 → "핀 색 범례" → 플로팅 윈도우. palette 좌 (색 스와치 + HEX) + bucket 우 (cpp_type → key) 양분.

- [ ] **Step 6: 커밋**

```bash
git add tests/app/test_pin_color_legend.py src/t3dgraph/core/app/pin_color_legend.py src/t3dgraph/core/app/main_window.py
git commit -m "feat(app): pin color legend floating dialog"
```

## 완료 후

사용자가 팔레트·매핑을 시각적으로 확인 가능. node_profile은 u4에서.
