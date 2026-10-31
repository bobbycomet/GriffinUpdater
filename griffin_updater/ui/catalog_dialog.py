from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QWidget,
)
from PyQt6.QtCore import Qt

from .. import catalog as catalog_mod
from ..models import AppEntry


class CatalogDialog(QDialog):
    """Browse the shared apps.json catalog and add entries to the local list."""

    def __init__(self, parent=None, existing_ids=None):
        super().__init__(parent)
        self.existing_ids = set(existing_ids or [])
        self.chosen_entry: AppEntry | None = None
        self.setWindowTitle("Browse Catalog")
        self.setMinimumSize(560, 420)
        self._build_ui()
        self._populate(catalog_mod.load_cached_catalog())

    def _build_ui(self):
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Community Catalog")
        title.setObjectName("HeaderLabel")
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = QPushButton("Update Catalog")
        self.refresh_btn.setObjectName("PrimaryButton")
        self.refresh_btn.clicked.connect(self._refresh)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("SubtleLabel")
        root.addWidget(self.subtitle)

        self.list_widget = QListWidget()
        root.addWidget(self.list_widget)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _refresh(self):
        try:
            apps = catalog_mod.refresh_catalog()
            self.subtitle.setText(f"Fetched {len(apps)} app(s) from {catalog_mod.get_catalog_url()}")
        except catalog_mod.CatalogError as exc:
            QMessageBox.warning(self, "Catalog update failed", str(exc))
            apps = catalog_mod.load_cached_catalog()
            self.subtitle.setText("Showing last cached catalog.")
        self._populate(apps)

    def _populate(self, apps: list[dict]):
        self.list_widget.clear()
        if not apps:
            self.subtitle.setText(
                "No cached catalog yet - click 'Update Catalog' to fetch it."
            )
        for row in apps:
            item = QListWidgetItem()
            widget = self._build_row_widget(row)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _build_row_widget(self, row: dict) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 6, 8, 6)

        text_col = QVBoxLayout()
        name_label = QLabel(f"<b>{row.get('name', row.get('id', 'Unknown'))}</b>  "
                             f"<span style='color:#9aa0b4'>({row.get('category', '?')})</span>")
        desc_label = QLabel(row.get("description", ""))
        desc_label.setObjectName("SubtleLabel")
        desc_label.setWordWrap(True)
        text_col.addWidget(name_label)
        text_col.addWidget(desc_label)
        layout.addLayout(text_col, stretch=1)

        already_added = row.get("id") in self.existing_ids
        add_btn = QPushButton("Added" if already_added else "Add")
        add_btn.setEnabled(not already_added)
        if not already_added:
            add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(lambda _checked, r=row: self._choose(r))
        layout.addWidget(add_btn)
        return w

    def _choose(self, row: dict):
        self.chosen_entry = catalog_mod.catalog_entry_to_app_entry(row)
        self.accept()
