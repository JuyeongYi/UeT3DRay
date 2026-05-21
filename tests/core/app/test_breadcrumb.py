"""BreadcrumbBar — set/segment_clicked/click_segment."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from t3dgraph.core.app.breadcrumb_bar import BreadcrumbBar


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_set_segments_renders_buttons(qapp):
    bar = BreadcrumbBar()
    bar.set_segments(["root", "Physics", "Inner"])
    assert bar.segment_labels() == ["root", "Physics", "Inner"]


def test_segment_click_emits_index(qapp):
    bar = BreadcrumbBar()
    bar.set_segments(["A", "B", "C"])
    received: list[int] = []
    bar.segment_clicked.connect(received.append)
    bar.click_segment(1)
    assert received == [1]


def test_empty_segments(qapp):
    bar = BreadcrumbBar()
    bar.set_segments([])
    assert bar.segment_labels() == []


def test_replace_segments_drops_old(qapp):
    bar = BreadcrumbBar()
    bar.set_segments(["A", "B"])
    bar.set_segments(["X"])
    assert bar.segment_labels() == ["X"]
