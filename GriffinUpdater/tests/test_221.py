import errno, json, os, shutil, sys, tempfile, types
from pathlib import Path
from unittest import mock

tmp_home = tempfile.mkdtemp(prefix="gu-home-")
os.environ["HOME"] = tmp_home
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from griffin_updater import models, catalog, config, __version__
from griffin_updater.core import version as V, appimage_installer as AI, checker

ok = 0
def check(name, cond):
    global ok
    assert cond, "FAIL: " + name
    ok += 1
    print("ok  -", name)

# ---------------------------------------------------------------- releases
def rel(tag, pre=False, draft=False, assets=()):
    return {"tag_name": tag, "prerelease": pre, "draft": draft,
            "assets": [{"name": a, "browser_download_url": f"https://x/{tag}/{a}"} for a in assets]}

class Resp:
    def __init__(self, code, payload):
        self.status_code, self._p = code, payload
    def json(self): return self._p

calls = []
def fake_get(url, **kw):
    calls.append(url)
    if url.endswith("/releases/latest"):
        return Resp(404, {})            # repo only has pre-releases
    return Resp(200, [
        rel("v1.2.0", draft=True, assets=["UltraCombo-x86_64.AppImage"]),   # draft: must be skipped
        rel("v1.1.0", pre=True, assets=["UltraCombo-x86_64.AppImage", "src.zip"]),
        rel("v1.0.0", assets=["UltraCombo-x86_64.AppImage"]),
    ])

pat = r"^UltraCombo-x86_64.AppImage$"
with mock.patch.object(V.requests, "get", fake_get):
    try:
        V.resolve_github_release("o", "r", pat, False); check("stable-only 404 raises", False)
    except V.VersionResolutionError as e:
        check("stable-only: 404 error mentions pre-release option", "Include pre-releases" in str(e))
    r = V.resolve_github_release("o", "r", pat, True)
    check("prerelease on: picks newest non-draft (v1.1.0)", r.version == "1.1.0")
    check("prerelease on: download url from that release", r.download_url == "https://x/v1.1.0/UltraCombo-x86_64.AppImage")
    check("prerelease on: uses list endpoint", any("/releases?per_page=30" in c for c in calls))

# newest release lacks the asset -> falls back to older one that has it
def fake_get2(url, **kw):
    return Resp(200, [rel("v2.0.0", pre=True, assets=["notes.txt"]),
                      rel("v1.9.0", pre=True, assets=["app_1.9.0_x64.deb"])])
with mock.patch.object(V.requests, "get", fake_get2):
    r = V.resolve_github_release("o", "r", r"x64\.deb$", True)
    check("skips newest release without matching asset", r.version == "1.9.0")
    try:
        V.resolve_github_release("o", "r", r"nomatch", True); check("no match raises", False)
    except V.VersionResolutionError as e:
        check("no match error lists assets", "notes.txt" in str(e))

# default (stable) path still uses /latest and works
def fake_get3(url, **kw):
    assert url.endswith("/releases/latest"), url
    return Resp(200, rel("v3.0.0", assets=["a.AppImage"]))
with mock.patch.object(V.requests, "get", fake_get3):
    check("default path unchanged (/latest)", V.resolve_github_release("o", "r", "", False).version == "3.0.0")

# resolve() honours entry flag; missing attr -> False
e = models.AppEntry(id="u", name="U", category="appimage", source_type="github_release",
                    github_owner="o", github_repo="r", asset_pattern=pat, include_prereleases=True)
with mock.patch.object(V.requests, "get", fake_get):
    check("resolve(entry) honours include_prereleases", V.resolve(e).version == "1.1.0")

# ------------------------------------------------------------ is_newer
check("1.1.0 newer than 1.1.0-rc1", V.is_newer("1.1.0", "1.1.0-rc1"))
check("1.1.0-rc1 NOT newer than 1.1.0", not V.is_newer("1.1.0-rc1", "1.1.0"))
check("beta.2 newer than beta.1", V.is_newer("1.1.0-beta.2", "1.1.0-beta.1"))
check("1.2.0-alpha newer than 1.1.0", V.is_newer("1.2.0-alpha", "1.1.0"))
check("plain 1.10 > 1.9", V.is_newer("1.10.0", "1.9.0"))
check("same version not newer", not V.is_newer("1.0.0", "1.0.0"))
check("no old version -> newer", V.is_newer("1.0.0", None))
# force the pure-python fallback (no dpkg)
with mock.patch.object(V.subprocess, "run", side_effect=FileNotFoundError):
    check("py fallback: final > rc", V.is_newer("1.1.0", "1.1.0-rc1"))
    check("py fallback: rc !> final", not V.is_newer("1.1.0-rc1", "1.1.0"))
    check("py fallback: beta.10 > beta.9", V.is_newer("1.1.0-beta.10", "1.1.0-beta.9"))
    check("py fallback: 1.10 > 1.9", V.is_newer("1.10", "1.9"))

# ------------------------------------------- cross-device AppImage install
src_dir = Path(tempfile.mkdtemp(prefix="gu-src-")); dst_dir = Path(tempfile.mkdtemp(prefix="gu-dst-"))
old = dst_dir / "app-1.0.AppImage"; old.write_text("old")
tmpf = src_dir / "dl.AppImage"; tmpf.write_bytes(b"NEW" * 1000)

real_rename, real_replace = os.rename, os.replace
def exdev_rename(a, b, *args, **kw):
    if str(a).startswith(str(src_dir)) and not str(b).startswith(str(src_dir)):
        raise OSError(errno.EXDEV, "Invalid cross-device link")
    return real_rename(a, b, *args, **kw)
def exdev_replace(a, b, *args, **kw):
    if str(a).startswith(str(src_dir)) and not str(b).startswith(str(src_dir)):
        raise OSError(errno.EXDEV, "Invalid cross-device link")
    return real_replace(a, b, *args, **kw)
with mock.patch("os.rename", exdev_rename), mock.patch("os.replace", exdev_replace):
    # sanity: the OLD approach really would have failed here
    try:
        Path(tmpf).replace(dst_dir / "x"); check("old Path.replace fails under EXDEV", False)
    except OSError as ex:
        check("old Path.replace fails under EXDEV", ex.errno == errno.EXDEV)
    final = AI.install_appimage(tmpf, str(dst_dir), "", "app-1.1.AppImage", old_path=str(old), delete_old=True)
check("cross-device: new file installed", final.read_bytes() == b"NEW" * 1000)
check("cross-device: executable bit set", os.access(final, os.X_OK))
check("cross-device: old file removed after success", not old.exists())
check("cross-device: temp download cleaned", not tmpf.exists())
check("cross-device: no .part leftovers", not list(dst_dir.glob(".*.part")))

# same filename on every release (UltraCombo style): overwritten, not deleted
same = dst_dir / "UltraCombo-x86_64.AppImage"; same.write_text("v1")
t2 = src_dir / "dl2.AppImage"; t2.write_text("v2")
AI.install_appimage(t2, str(dst_dir), "", "UltraCombo-x86_64.AppImage", old_path=str(same), delete_old=True)
check("same-name update keeps new file", same.read_text() == "v2")

# failed install keeps the old app
keep = dst_dir / "keep.AppImage"; keep.write_text("keepme")
t3 = src_dir / "dl3.AppImage"; t3.write_text("v3")
with mock.patch.object(AI.shutil, "move", side_effect=OSError(errno.ENOSPC, "No space left")):
    try:
        AI.install_appimage(t3, str(dst_dir), "", "new.AppImage", old_path=str(keep), delete_old=True)
        check("failed install raises", False)
    except AI.AppImageInstallError as ex:
        check("failed install raises AppImageInstallError", "No space" in str(ex))
check("failed install leaves old app intact", keep.exists() and keep.read_text() == "keepme")

# checker never raises on unexpected errors
with mock.patch.object(checker, "resolve", side_effect=RuntimeError("boom")):
    pass  # RuntimeError at resolve is outside the narrow except; covered below
e2 = models.AppEntry(id="boom", name="Boom", category="appimage", source_type="github_release",
                     github_owner="o", github_repo="r", notify=False)
with mock.patch.object(checker, "resolve", return_value=V.ResolvedVersion("1.0", "http://x", "a.AppImage")), \
     mock.patch.object(checker.appimage_installer, "check_and_install", side_effect=RuntimeError("boom")):
    res = checker.check_and_update(e2)
check("checker converts unexpected error into a failed result", (not res.ok) and "boom" in res.message)
with mock.patch.object(checker, "resolve", side_effect=ValueError("bad json")):
    res = checker.check_and_update(e2)
check("checker handles ValueError from resolve", (not res.ok) and "bad json" in res.message)

# ---------------------------------------------------------------- models
d = e.to_dict()
check("model roundtrip keeps include_prereleases", models.AppEntry.from_dict(d).include_prereleases is True)
check("old my_apps.json without the key defaults to False",
      models.AppEntry.from_dict({"id": "a", "name": "A"}).include_prereleases is False)

# --------------------------------------------------------- catalog sync
config.ensure_dirs()
local = models.AppEntry(id="ultracombo", name="UltraCombo", category="appimage", source_type="github_release",
                        github_owner="thefixinhixon", github_repo="UltraCombo", asset_pattern="old",
                        from_catalog=True, enabled=False, notify=False, sha256="abc",
                        appimage_target_dir="/opt/apps", appimage_filename="uc.AppImage",
                        schedule=models.Schedule(frequency="daily", time="03:30"))
manual = models.AppEntry(id="manual", name="Manual", from_catalog=False, url="keep")
rows = {"version": 1, "apps": [
    {"id": "ultracombo", "name": "UltraCombo", "category": "appimage", "source_type": "github_release",
     "github_owner": "thefixinhixon", "github_repo": "UltraCombo", "asset_pattern": pat,
     "include_prereleases": True},
    {"id": "manual", "name": "Manual", "url": "https://changed"}]}
config.CATALOG_CACHE_FILE.write_text(json.dumps({"apps": rows["apps"]}))
changed = catalog.apply_catalog_updates([local, manual])
check("catalog sync reports the tracked app", [c[0].id for c in changed] == ["ultracombo"])
check("catalog sync fields", set(changed[0][1]) == {"asset_pattern", "include_prereleases"})
check("catalog sync applied new pattern + flag", local.asset_pattern == pat and local.include_prereleases)
check("catalog sync keeps local choices",
      (local.enabled, local.notify, local.sha256, local.appimage_target_dir, local.appimage_filename,
       local.schedule.frequency, local.schedule.time) == (False, False, "abc", "/opt/apps", "uc.AppImage", "daily", "03:30"))
check("catalog sync ignores non-catalog apps", manual.url == "keep")
check("catalog sync is idempotent", catalog.apply_catalog_updates([local, manual]) == [])
# row that omits include_prereleases must not flip a user's own setting
local.include_prereleases = True
config.CATALOG_CACHE_FILE.write_text(json.dumps({"apps": [{"id": "ultracombo", "name": "UltraCombo"}]}))
check("absent catalog key leaves local value alone", catalog.apply_catalog_updates([local]) == [] and local.include_prereleases)

# ---------------------------------------------------------------- Qt UI
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from griffin_updater.ui.add_edit_app_dialog import AddEditAppDialog
from griffin_updater.ui.main_window import MainWindow
dlg = AddEditAppDialog(entry=e)
check("dialog loads pre-release flag", dlg.prerelease_check.isChecked())
dlg.prerelease_check.setChecked(False)
dlg._on_accept()
check("dialog saves pre-release flag", dlg.result_entry.include_prereleases is False)
dlg2 = AddEditAppDialog(); dlg2.name_edit.setText("New"); dlg2.url_edit.setText("http://x")
dlg2.prerelease_check.setChecked(True); dlg2._on_accept()
check("new-app dialog carries flag", dlg2.result_entry.include_prereleases is True)

# MainWindow + catalog update path (no network: refresh_catalog patched)
models.save_apps([local])
config.CATALOG_CACHE_FILE.write_text(json.dumps({"apps": [
    {"id": "ultracombo", "name": "UltraCombo", "asset_pattern": "newer-pattern"}]}))
with mock.patch("griffin_updater.core.systemd_manager.systemd_available", return_value=False):
    w = MainWindow()
    check("window title has version", __version__ in w.windowTitle())
    with mock.patch.object(catalog, "refresh_catalog", return_value=[{"id": "ultracombo"}]):
        w.update_catalog()
    check("update_catalog pushes change into tracked app", w.apps[0].asset_pattern == "newer-pattern")
    check("update_catalog persisted to my_apps.json",
          models.load_apps()[0].asset_pattern == "newer-pattern")
    check("status bar names the updated app", "UltraCombo" in w.statusBar().currentMessage())

print(f"\nALL {ok} CHECKS PASSED")
