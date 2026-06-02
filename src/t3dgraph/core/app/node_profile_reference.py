"""노드 프로필 참조 — 클래스별 시각/동작 노브 시각화."""
from __future__ import annotations
from dataclasses import fields as _fields

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
