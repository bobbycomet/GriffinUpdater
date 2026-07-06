from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QToolBar, QPushButton, QLabel, QSplitter, QPlainTextEdit, QMessageBox,
    QSystemTrayIcon, QMenu, QHeaderView, QAbstractItemView,
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .. import config, models
from ..core import checker, state as state_mod, systemd_manager
from .add_edit_app_dialog import AddEditAppDialog
from .catalog_dialog import CatalogDialog
from .settings_dialog import SettingsDialog


class CheckWorker(QThread):
    finished_one = pyqtSignal(str, bool, bool, str)  # app_id, ok, updated, message
    finished_all = pyqtSignal()

    def __init__(self, entries: list[models.AppEntry]):
        super().__init__()
        self.entries = entries

    def run(self):
        for entry in self.entries:
            result = checker.check_and_update(entry)
            self.finished_one.emit(result.app_id, result.ok, result.updated, result.message)
        self.finished_all.emit()


class MainWindow(QMainWindow):
    COLUMNS = ["", "Name", "Type", "Installed", "Schedule", "Status"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Griffin Updater")
        self.resize(920, 560)
        if config.APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(config.APP_ICON_PATH)))

        self.apps: list[models.AppEntry] = models.load_apps()
        self._worker: CheckWorker | None = None

        self._build_ui()
        self._build_tray()
        self._reload_table()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        def add_action(text, slot, primary=False):
            btn = QPushButton(text)
            if primary:
                btn.setObjectName("PrimaryButton")
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
            return btn

        add_action("Add App", self.add_app, primary=True)
        self.edit_btn = add_action("Edit", self.edit_selected_app)
        self.remove_btn = add_action("Remove", self.remove_selected_app)
        toolbar.addSeparator()
        self.check_btn = add_action("Check Now", self.check_selected_now)
        add_action("Check All Now", self.check_all_now)
        toolbar.addSeparator()
        add_action("Browse Catalog", self.browse_catalog)
        add_action("Update Catalog", self.update_catalog)
        toolbar.addSeparator()
        add_action("Settings", self.open_settings)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_selected_app())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)

        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_label = QLabel("Activity Log")
        log_label.setObjectName("HeaderLabel")
        log_layout.addWidget(log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        splitter.addWidget(log_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Ready")

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        if config.APP_ICON_PATH.exists():
            self.tray.setIcon(QIcon(str(config.APP_ICON_PATH)))
        else:
            self.tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        menu = QMenu()
        show_action = QAction("Show Griffin Updater", self)
        show_action.triggered.connect(self._restore_from_tray)
        check_all_action = QAction("Check All Now", self)
        check_all_action.triggered.connect(self.check_all_now)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(check_all_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._restore_from_tray()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.tray.show()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Griffin Updater", "Still running in the background — scheduled checks continue.",
            QSystemTrayIcon.MessageIcon.Information, 4000,
        )

    # --------------------------------------------------------------- table

    def _reload_table(self):
        self.table.setRowCount(0)
        for entry in self.apps:
            self._add_table_row(entry)
        self._refresh_log_for_selection()

    def _add_table_row(self, entry: models.AppEntry):
        row = self.table.rowCount()
        self.table.insertRow(row)

        enabled_item = QTableWidgetItem("✓" if entry.enabled else "—")
        enabled_item.setData(Qt.ItemDataRole.UserRole, entry.id)
        enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, enabled_item)

        self.table.setItem(row, 1, QTableWidgetItem(entry.name))
        self.table.setItem(row, 2, QTableWidgetItem(entry.category))

        st = state_mod.get_app_state(entry.id)
        installed = st.get("installed_version") or "—"
        self.table.setItem(row, 3, QTableWidgetItem(installed))
        self.table.setItem(row, 4, QTableWidgetItem(entry.schedule.describe()))
        self.table.setItem(row, 5, QTableWidgetItem(st.get("last_result", "never checked")))

    def _selected_entry(self) -> models.AppEntry | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.apps):
            return None
        app_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((a for a in self.apps if a.id == app_id), None)

    def _on_selection_changed(self):
        self._refresh_log_for_selection()

    def _refresh_log_for_selection(self):
        entry = self._selected_entry()
        if not entry:
            self.log_view.setPlainText("Select an app to see its activity log.")
            return
        st = state_mod.get_app_state(entry.id)
        lines = st.get("log", []) or ["No activity yet."]
        self.log_view.setPlainText("\n".join(lines))

    # ------------------------------------------------------------- actions

    def add_app(self):
        dlg = AddEditAppDialog(self, existing_ids=[a.id for a in self.apps])
        if dlg.exec():
            self._persist_new_entry(dlg.result_entry)

    def edit_selected_app(self):
        entry = self._selected_entry()
        if not entry:
            QMessageBox.information(self, "No selection", "Select an app first.")
            return
        dlg = AddEditAppDialog(self, entry=entry, existing_ids=[a.id for a in self.apps if a.id != entry.id])
        if dlg.exec():
            self._persist_new_entry(dlg.result_entry)

    def _persist_new_entry(self, new_entry: models.AppEntry):
        self.apps = models.upsert_app(self.apps, new_entry)
        models.save_apps(self.apps)
        if systemd_manager.systemd_available():
            ok, msg = systemd_manager.sync_unit(new_entry)
            if not ok:
                QMessageBox.warning(self, "Scheduling issue", f"{new_entry.name}: {msg}")
        else:
            self.statusBar().showMessage(
                "systemctl not found - schedules were saved but won't run automatically.", 6000
            )
        self._reload_table()

    def remove_selected_app(self):
        entry = self._selected_entry()
        if not entry:
            return
        reply = QMessageBox.question(
            self, "Remove app", f"Remove '{entry.name}' and its schedule? This won't uninstall it."
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        systemd_manager.remove_unit(entry.id)
        self.apps = models.remove_app(self.apps, entry.id)
        models.save_apps(self.apps)
        self._reload_table()

    def check_selected_now(self):
        entry = self._selected_entry()
        if not entry:
            QMessageBox.information(self, "No selection", "Select an app first.")
            return
        self._run_checks([entry])

    def check_all_now(self):
        enabled = [a for a in self.apps if a.enabled]
        if not enabled:
            QMessageBox.information(self, "Nothing to check", "No enabled apps configured.")
            return
        self._run_checks(enabled)

    def _run_checks(self, entries: list[models.AppEntry]):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Busy", "A check is already running.")
            return
        self.statusBar().showMessage(f"Checking {len(entries)} app(s)…")
        self.check_btn.setEnabled(False)
        self._worker = CheckWorker(entries)
        self._worker.finished_one.connect(self._on_one_finished)
        self._worker.finished_all.connect(self._on_all_finished)
        self._worker.start()

    def _on_one_finished(self, app_id: str, ok: bool, updated: bool, message: str):
        self.statusBar().showMessage(message, 5000)
        self._reload_table()

    def _on_all_finished(self):
        self.check_btn.setEnabled(True)
        self.statusBar().showMessage("Check complete.", 4000)

    def browse_catalog(self):
        dlg = CatalogDialog(self, existing_ids=[a.id for a in self.apps])
        if dlg.exec() and dlg.chosen_entry:
            # Let the user tailor schedule / install location before saving.
            edit_dlg = AddEditAppDialog(
                self, entry=dlg.chosen_entry, existing_ids=[a.id for a in self.apps]
            )
            edit_dlg.setWindowTitle(f"Add {dlg.chosen_entry.name} from Catalog")
            if edit_dlg.exec():
                self._persist_new_entry(edit_dlg.result_entry)

    def update_catalog(self):
        from .. import catalog as catalog_mod
        try:
            apps = catalog_mod.refresh_catalog()
            self.statusBar().showMessage(f"Catalog updated - {len(apps)} app(s) available.", 5000)
        except catalog_mod.CatalogError as exc:
            QMessageBox.warning(self, "Catalog update failed", str(exc))

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
