from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QTimeEdit, QPushButton, QLabel, QGroupBox,
    QStackedWidget, QWidget, QTextEdit, QFileDialog, QDialogButtonBox,
    QMessageBox,
)
from PyQt6.QtCore import QTime

from ..models import AppEntry, Schedule, slugify, WEEKDAYS
from .. import config


class AddEditAppDialog(QDialog):
    def __init__(self, parent=None, entry: AppEntry | None = None, existing_ids=None):
        super().__init__(parent)
        self.existing_ids = set(existing_ids or [])
        self._editing = entry is not None
        self.entry = entry or AppEntry(id="", name="")
        self.setWindowTitle("Edit App" if self._editing else "Add App")
        self.setMinimumWidth(480)
        self._build_ui()
        self._load_entry()

    # ---------------------------------------------------------------- UI

    def _build_ui(self):
        root = QVBoxLayout(self)

        basics = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._maybe_update_id_preview)
        self.id_preview = QLabel()
        self.id_preview.setObjectName("SubtleLabel")
        self.desc_edit = QLineEdit()
        basics.addRow("App name:", self.name_edit)
        basics.addRow("", self.id_preview)
        basics.addRow("Description:", self.desc_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["deb", "appimage", "archive"])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        basics.addRow("Package type:", self.category_combo)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["static_url", "github_release"])
        self.source_combo.setToolTip(
            "Static URL: a link that always redirects to the current file (e.g. Discord).\n"
            "GitHub Repo: queries the GitHub Releases API so it keeps working even when\n"
            "release asset filenames change version-to-version (e.g. OpenTabletDriver)."
        )
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        basics.addRow("Update source:", self.source_combo)

        root.addLayout(basics)

        # --- static url fields ---
        self.static_group = QGroupBox("Static URL")
        static_form = QFormLayout(self.static_group)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/download?platform=linux&format=deb")
        self.version_regex_edit = QLineEdit()
        self.version_regex_edit.setPlaceholderText("optional, e.g. app-([0-9.]+)\\.deb")
        static_form.addRow("Download URL:", self.url_edit)
        static_form.addRow("Version regex:", self.version_regex_edit)
        root.addWidget(self.static_group)

        # --- github release fields ---
        self.github_group = QGroupBox("GitHub Repo")
        gh_form = QFormLayout(self.github_group)
        self.gh_owner_edit = QLineEdit()
        self.gh_owner_edit.setPlaceholderText("e.g. OpenTabletDriver")
        self.gh_repo_edit = QLineEdit()
        self.gh_repo_edit.setPlaceholderText("e.g. OpenTabletDriver")
        self.asset_pattern_edit = QLineEdit()
        self.asset_pattern_edit.setPlaceholderText(r"regex, e.g. x64\.deb$")
        gh_form.addRow("Owner:", self.gh_owner_edit)
        gh_form.addRow("Repo:", self.gh_repo_edit)
        gh_form.addRow("Asset filename pattern:", self.asset_pattern_edit)
        root.addWidget(self.github_group)

        # --- deb-specific ---
        self.deb_group = QGroupBox("Debian Package")
        deb_form = QFormLayout(self.deb_group)
        self.package_name_edit = QLineEdit()
        self.package_name_edit.setPlaceholderText("dpkg package name (blank = same as app id)")
        deb_form.addRow("Package name:", self.package_name_edit)
        root.addWidget(self.deb_group)

        # --- appimage-specific ---
        self.appimage_group = QGroupBox("AppImage")
        appimage_form = QFormLayout(self.appimage_group)
        dir_row = QHBoxLayout()
        self.target_dir_edit = QLineEdit(str(config.DESKTOP_DIR))
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_target_dir)
        dir_row.addWidget(self.target_dir_edit)
        dir_row.addWidget(browse_btn)
        appimage_form.addRow("Install location:", dir_row)
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("optional, blank = keep downloaded filename")
        appimage_form.addRow("Force filename:", self.filename_edit)
        self.delete_old_check = QCheckBox("Delete previous AppImage after installing the new one")
        self.delete_old_check.setChecked(True)
        appimage_form.addRow("", self.delete_old_check)
        root.addWidget(self.appimage_group)

        # --- archive-specific (zip/tar.xz that gets extracted, e.g. Godot) ---
        self.archive_group = QGroupBox("Archive (zip / tar.xz extraction)")
        archive_form = QFormLayout(self.archive_group)
        archive_dir_row = QHBoxLayout()
        self.archive_install_dir_edit = QLineEdit(str(config.HOME / "Applications"))
        archive_browse_btn = QPushButton("Browse…")
        archive_browse_btn.clicked.connect(self._browse_archive_install_dir)
        archive_dir_row.addWidget(self.archive_install_dir_edit)
        archive_dir_row.addWidget(archive_browse_btn)
        archive_form.addRow("Install location:", archive_dir_row)
        archive_form.addRow(
            "", QLabel("Can be any path, including a different drive/mount point.")
        )
        self.archive_subdir_edit = QLineEdit()
        self.archive_subdir_edit.setPlaceholderText("folder name under install location, blank = app id")
        archive_form.addRow("Subfolder name:", self.archive_subdir_edit)
        self.archive_exec_pattern_edit = QLineEdit()
        self.archive_exec_pattern_edit.setPlaceholderText(r"regex against extracted filenames, e.g. ^Godot_v[\d.]+-stable(_mono)?_linux")
        archive_form.addRow("Executable pattern:", self.archive_exec_pattern_edit)
        self.archive_delete_old_check = QCheckBox("Delete previous version before extracting the new one")
        self.archive_delete_old_check.setChecked(True)
        self.archive_delete_old_check.setToolTip(
            "If off, each version is kept in its own '<subfolder>-<version>' directory instead of overwriting."
        )
        archive_form.addRow("", self.archive_delete_old_check)
        self.archive_symlink_edit = QLineEdit()
        self.archive_symlink_edit.setPlaceholderText("optional, e.g. 'godot' - a stable shortcut that always points at the current version")
        archive_form.addRow("Stable symlink name:", self.archive_symlink_edit)
        root.addWidget(self.archive_group)

        # --- schedule ---
        sched_group = QGroupBox("Update Schedule")
        sched_form = QFormLayout(sched_group)
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["daily", "weekly", "monthly", "custom"])
        self.freq_combo.currentTextChanged.connect(self._on_frequency_changed)
        sched_form.addRow("Check:", self.freq_combo)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(13, 0))
        sched_form.addRow("At time:", self.time_edit)

        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(WEEKDAYS)
        sched_form.addRow("On day:", self.weekday_combo)

        self.day_of_month_spin = QSpinBox()
        self.day_of_month_spin.setRange(1, 28)
        self.day_of_month_spin.setValue(1)
        sched_form.addRow("On day of month:", self.day_of_month_spin)

        self.custom_oncalendar_edit = QLineEdit()
        self.custom_oncalendar_edit.setPlaceholderText("systemd OnCalendar= expression, e.g. Mon,Fri *-*-* 09:00:00")
        sched_form.addRow("Custom OnCalendar:", self.custom_oncalendar_edit)

        root.addWidget(sched_group)

        toggles = QHBoxLayout()
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        self.notify_check = QCheckBox("Notify on update")
        self.notify_check.setChecked(True)
        toggles.addWidget(self.enabled_check)
        toggles.addWidget(self.notify_check)
        toggles.addStretch()
        root.addLayout(toggles)

        integrity_form = QFormLayout()
        self.sha256_edit = QLineEdit()
        self.sha256_edit.setPlaceholderText(
            "optional - if set, the download is rejected unless it matches exactly"
        )
        integrity_form.addRow("Expected SHA-256:", self.sha256_edit)
        root.addLayout(integrity_form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._on_category_changed(self.category_combo.currentText())
        self._on_source_changed(self.source_combo.currentText())
        self._on_frequency_changed(self.freq_combo.currentText())

    # ------------------------------------------------------------ helpers

    def _maybe_update_id_preview(self, _text: str):
        if not self._editing:
            self.id_preview.setText(f"id: {slugify(self.name_edit.text())}")

    def _on_category_changed(self, category: str):
        self.deb_group.setVisible(category == "deb")
        self.appimage_group.setVisible(category == "appimage")
        self.archive_group.setVisible(category == "archive")

    def _on_source_changed(self, source: str):
        self.static_group.setVisible(source == "static_url")
        self.github_group.setVisible(source == "github_release")

    def _on_frequency_changed(self, freq: str):
        self.weekday_combo.setEnabled(freq == "weekly")
        self.day_of_month_spin.setEnabled(freq == "monthly")
        self.custom_oncalendar_edit.setEnabled(freq == "custom")
        self.time_edit.setEnabled(freq in ("daily", "weekly", "monthly"))

    def _browse_target_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose install location", self.target_dir_edit.text())
        if d:
            self.target_dir_edit.setText(d)

    def _browse_archive_install_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Choose install location", self.archive_install_dir_edit.text()
        )
        if d:
            self.archive_install_dir_edit.setText(d)

    # -------------------------------------------------------------- load

    def _load_entry(self):
        e = self.entry
        self.name_edit.setText(e.name)
        self.id_preview.setText(f"id: {e.id}" if self._editing else f"id: {slugify(e.name)}")
        self.desc_edit.setText(e.description)
        self.category_combo.setCurrentText(e.category)
        self.source_combo.setCurrentText(e.source_type)
        self.url_edit.setText(e.url)
        self.version_regex_edit.setText(e.version_regex)
        self.gh_owner_edit.setText(e.github_owner)
        self.gh_repo_edit.setText(e.github_repo)
        self.asset_pattern_edit.setText(e.asset_pattern)
        self.package_name_edit.setText(e.package_name)
        self.target_dir_edit.setText(e.appimage_target_dir or str(config.DESKTOP_DIR))
        self.filename_edit.setText(e.appimage_filename)
        self.delete_old_check.setChecked(e.delete_old_appimage)
        self.archive_install_dir_edit.setText(e.archive_install_dir or str(config.HOME / "Applications"))
        self.archive_subdir_edit.setText(e.archive_subdir_name)
        self.archive_exec_pattern_edit.setText(e.archive_executable_pattern)
        self.archive_delete_old_check.setChecked(e.archive_delete_old)
        self.archive_symlink_edit.setText(e.archive_symlink_name)
        self.enabled_check.setChecked(e.enabled)
        self.notify_check.setChecked(e.notify)
        self.sha256_edit.setText(e.sha256)

        s = e.schedule
        self.freq_combo.setCurrentText(s.frequency)
        hh, mm = (s.time.split(":") + ["00"])[:2]
        self.time_edit.setTime(QTime(int(hh), int(mm)))
        self.weekday_combo.setCurrentText(s.day_of_week)
        self.day_of_month_spin.setValue(s.day_of_month)
        self.custom_oncalendar_edit.setText(s.custom_oncalendar)

    # ------------------------------------------------------------ accept

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter an app name.")
            return

        app_id = self.entry.id if self._editing else slugify(name)
        if not self._editing and app_id in self.existing_ids:
            QMessageBox.warning(self, "Duplicate app", f"An app with id '{app_id}' already exists.")
            return

        category = self.category_combo.currentText()
        source_type = self.source_combo.currentText()

        if source_type == "static_url" and not self.url_edit.text().strip():
            QMessageBox.warning(self, "Missing URL", "Please enter a download URL.")
            return
        if source_type == "github_release" and not (self.gh_owner_edit.text().strip() and self.gh_repo_edit.text().strip()):
            QMessageBox.warning(self, "Missing repo", "Please enter both a GitHub owner and repo.")
            return

        t = self.time_edit.time()
        schedule = Schedule(
            frequency=self.freq_combo.currentText(),
            time=f"{t.hour():02d}:{t.minute():02d}",
            day_of_week=self.weekday_combo.currentText(),
            day_of_month=self.day_of_month_spin.value(),
            custom_oncalendar=self.custom_oncalendar_edit.text().strip(),
        )

        self.result_entry = AppEntry(
            id=app_id,
            name=name,
            category=category,
            source_type=source_type,
            description=self.desc_edit.text().strip(),
            url=self.url_edit.text().strip(),
            version_regex=self.version_regex_edit.text().strip(),
            github_owner=self.gh_owner_edit.text().strip(),
            github_repo=self.gh_repo_edit.text().strip(),
            asset_pattern=self.asset_pattern_edit.text().strip(),
            package_name=self.package_name_edit.text().strip(),
            appimage_target_dir=self.target_dir_edit.text().strip() or str(config.DESKTOP_DIR),
            appimage_filename=self.filename_edit.text().strip(),
            delete_old_appimage=self.delete_old_check.isChecked(),
            archive_install_dir=self.archive_install_dir_edit.text().strip() or str(config.HOME / "Applications"),
            archive_subdir_name=self.archive_subdir_edit.text().strip(),
            archive_executable_pattern=self.archive_exec_pattern_edit.text().strip(),
            archive_delete_old=self.archive_delete_old_check.isChecked(),
            archive_symlink_name=self.archive_symlink_edit.text().strip(),
            enabled=self.enabled_check.isChecked(),
            notify=self.notify_check.isChecked(),
            sha256=self.sha256_edit.text().strip(),
            schedule=schedule,
            from_catalog=self.entry.from_catalog,
        )
        self.accept()
