"""핀 색 범례 — palette + bucket 매핑 시각화 플로팅 패널."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QWidget,
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

        # palette 섹션
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
        splitter.addWidget(self._make_panel(palette_box, self._palette_table))

        # bucket 섹션
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
        splitter.addWidget(self._make_panel(bucket_box, self._bucket_table))

        outer = QVBoxLayout(self)
        outer.addWidget(splitter)

    @staticmethod
    def _make_panel(layout: QVBoxLayout, table: QTableWidget) -> QWidget:
        layout.addWidget(table)
        w = QWidget()
        w.setLayout(layout)
        return w
