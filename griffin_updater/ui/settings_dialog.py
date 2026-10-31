from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QLabel

from .. import catalog as catalog_mod


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)

        form = QFormLayout()
        self.catalog_url_edit = QLineEdit(catalog_mod.get_catalog_url())
        form.addRow("Catalog URL:", self.catalog_url_edit)
        root.addLayout(form)

        hint = QLabel(
            "This should point at the raw apps.json in your Discordupdater repo "
            "(or any mirror). Click 'Update Catalog' from the main window after "
            "changing this to fetch immediately."
        )
        hint.setObjectName("SubtleLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_accept(self):
        catalog_mod.set_catalog_url(self.catalog_url_edit.text().strip() or catalog_mod.config.DEFAULT_CATALOG_URL)
        self.accept()
