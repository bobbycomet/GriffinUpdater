# Griffin Updater — Install and keep third-party Linux apps updated

## Why this exists

If you've moved from Windows to Linux, you're used to apps quietly checking for their own updates. On Linux, that's true for anything installed through your distro's package manager, but the moment you grab a standalone `.deb` from a vendor's site or an AppImage from GitHub, you're on your own. Either you remember to go check for a new version yourself, or you write a one-off script and wire it into a systemd timer by hand.

That second approach actually works; it's how a lot of unofficial Discord updaters function on Linux: a script checks a permanent download link, compares versions, installs if needed, and a timer runs it on a schedule. Griffin Updater takes that pattern and turns it into a real application: a GUI that works for *any* `.deb`, AppImage, or archive, not just Discord, so you never have to write or maintain a shell script yourself.

**Add an app once, tell it how often to check, and forget about it.** Everything else — version comparison, downloading, installing, notifying you, and the systemd wiring behind it happens on its own.

## What you get

- **Install** — Clicking **Check now** will install anything you choose; no need to find and download it if it is in the `apps.json`; it is also a manual way to update
- **Track anything** — paste a direct download link, or point it at a GitHub or Codeberg/Gitea repo
- **Real schedules, not just a GUI timer** — each app gets its own `systemd --user` timer, so checks still run when the app isn't open
- **`.deb`, AppImage, and archive support** — including apps like Godot that ship as a bare zip/tar.xz with no package manager involved
- **Nothing installs behind your back** — a background timer that finds a `.deb` update sends a notification with an "Install Now" button first; it never jumps straight to a password prompt on its own
- **A shared catalog** — pull a community-maintained list of pre-configured apps with one click, or add your own
- **Griffin Dark Theme** — a gold-on-charcoal, Steam-style look

<img width="1920" height="1080" alt="Screenshot_20260721_164331" src="https://github.com/user-attachments/assets/f688c750-e54a-4c9b-81e7-3b07844aa5d3" />
<img width="1920" height="1080" alt="Screenshot_20260721_164344" src="https://github.com/user-attachments/assets/8804bba8-d9e7-4c3f-b71f-b3a531156a81" />
<img width="1920" height="1080" alt="Screenshot_20260721_164356" src="https://github.com/user-attachments/assets/9e7c6234-1fb6-4a1d-b867-a17865bace90" />
<img width="1920" height="1080" alt="Screenshot_20260721_164406" src="https://github.com/user-attachments/assets/1a13f8ce-0687-4ad1-85da-52773c5605ad" />

## 2.0 → 2.1: what actually changed

Version 2.0 was the original core idea: scheduled `.deb`/AppImage updates via systemd timers, PolicyKit-elevated installs, a shared catalog, and the dark theme.

2.1 is the same app grown up. It's not one feature; it's everything that landed on top of that core since:

| | 2.0 | 2.1 |
|---|---|---|
| Sources | GitHub releases only | GitHub **and** Codeberg/self-hosted Gitea |
| App types | `.deb`, AppImage | `.deb`, AppImage, **and plain archives** |
| Safety | Straight `pkexec` prompt | **Notify-first consent** for unattended installs |
| Update timing | Installs the moment it's found | Optional **update hold** (wait a few days before a fresh update installs, in case it's buggy) |
| Catalog entries | One format per app | **Multi-variant** entries (choose `.deb` or AppImage for apps that ship both) |
| Trust | Plain HTTPS only | Optional **Ed25519 signing** on the shared catalog |
| Keeping itself current | Manual | **Self-update** |
| Packaging | AppImage only | AppImage **and a real Debian package/PPA** |
| Maintenance | Manual timer fixes | **Regenerate Timers** repairs or rebuilds every app's systemd units in one click |

If you're on 2.0, none of your setup breaks moving to 2.1; it's additive the whole way.

## Two ways to track a version

**Static URL mode** is for apps with a permanent download link, like Discord's `https://discord.com/api/download?platform=linux&format=deb`. It always redirects to the current build, and Griffin Updater pulls the version straight out of the resulting filename.

**GitHub/Gitea Repo mode** is for apps whose release filenames change with every version, like `opentabletdriver_0.6.7-1_x64.deb`. Instead of a link, you give it an owner/repo (and host, for Codeberg or self-hosted Gitea) plus a filename pattern, and it asks the releases API for whatever the current asset actually is, so it never goes stale.

You can switch a tracked app between modes, or edit its details, at any time from Edit.

## The shared catalog

A single `apps.json` file, hosted on GitHub, that anyone running Griffin Updater can pull with **Update Catalog**, browse, and add from. You're always free to add your own untracked apps directly instead.

Want your app added? Join the Discord and drop it in the feature-request channel; that's faster for me to see than a pull request, though `apps.json` is protected by CODEOWNERS so PRs do get reviewed.

<details>
<summary><strong>Catalog format, for anyone maintaining or contributing entries</strong></summary>

```json
{
  "version": 1,
  "apps": [
    {
      "id": "discord",
      "name": "Discord",
      "category": "deb",
      "source_type": "static_url",
      "description": "Voice, video, and text chat.",
      "url": "https://discord.com/api/download?platform=linux&format=deb",
      "version_regex": "discord-([0-9.]+)\\.deb",
      "package_name": "discord"
    },
    {
      "id": "opentabletdriver",
      "name": "OpenTabletDriver",
      "category": "deb",
      "source_type": "github_release",
      "description": "Open source, cross-platform tablet driver.",
      "github_owner": "OpenTabletDriver",
      "github_repo": "OpenTabletDriver",
      "asset_pattern": "x64\\.deb$",
      "package_name": "opentabletdriver"
    }
  ]
}
```

- `id` — unique slug, required.
- `name` — display name in the catalog browser.
- `category` — `deb`, `appimage`, or `archive`.
- `source_type` — `static_url`, `github_release`, or `gitea_release`.
- `description` — shown in the catalog browser.
- `url` — static_url only; the always-current download link.
- `version_regex` — static_url only; optional, defaults to an N.N.N-style token.
- `github_owner` / `github_repo` — github_release only.
- `gitea_host` (defaults to `codeberg.org`) / `gitea_owner` / `gitea_repo` — gitea_release only.
- `asset_pattern` — github_release/gitea_release only; regex matched against release asset filenames. Be specific if a release ships more than one asset of the same file type (e.g. per-architecture `.deb`s) — Griffin Updater takes the first match, so a loose pattern can silently grab the wrong one.
- `package_name` — deb entries only; defaults to `id`.

Apps that ship both a `.deb` and an AppImage can use a `variants` list instead of top-level fields — Griffin Updater will ask which one you want tracked when you add it.

Local-only settings (schedule, install folder, enabled/notify toggles) aren't part of the catalog; those are filled in per-person when an app is added, since they're preferences, not facts about the app.

If **Update Catalog** fails right after a new `apps.json` is pushed, that's usually just GitHub's raw-content CDN catching up, not a broken file; worth a moment and a retry.

If you want stronger guarantees than plain HTTPS, the catalog supports Ed25519 signing (`packaging/sign_catalog.py`, `SECURITY.md`), off by default.

Griffin Updater points at `https://raw.githubusercontent.com/bobbycomet/Discordupdater/main/apps.json` by default; change it any time in Settings.

</details>

## Known limitations

- AppImages and archives have no OS-level version record like `dpkg` does, so their state lives in `~/.local/share/griffin-updater/state.json`. Deleting that file makes the next check treat the app as a fresh install.
- `.deb` installs from a scheduled timer wait for you to click "Install Now" on the notification. If nobody's logged into the graphical session when the timer fires, or the notification's ignored, that install is skipped and retried next time.
- The default version-detection regex expects an N.N.N-style version. Unusual version schemes may need a custom regex, which is why that field is editable per app.

## Download

Grab the latest AppImage from the [Releases page](https://github.com/bobbycomet/GriffinUpdater/releases), or use the direct link:

[Download Griffin Updater v2.1.0](https://github.com/bobbycomet/GriffinUpdater/releases/download/v2.1.0/Griffin-Updater-x86_64.AppImage)

```bash
chmod +x Griffin-Updater-x86_64.AppImage
./Griffin-Updater-x86_64.AppImage
```

<details>
<summary><strong>Installing from source</strong></summary>

Debian and Ubuntu's system Python is externally managed under PEP 668, so a venv is the recommended path — created with `--system-site-packages` so it can see the apt-installed PyQt6 instead of pulling a second copy from PyPI:

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate

cd griffin-updater
pip install -r requirements.txt
pip install -e .
```

Skipping the venv and installing straight against system Python also works, but needs `--break-system-packages` on both installs, and shares that Python with everything else on the system (use caution with break system packages):

```bash
cd griffin-updater
pip install -r requirements.txt --break-system-packages
pip install -e . --break-system-packages
```

Launch it with `griffin-updater`, or run it straight from the source tree without installing:

```bash
python3 -m griffin_updater.main
```

Drop `packaging/griffin-updater.desktop` into `~/.local/share/applications/` (adjust `Icon=` once a real PNG is in place) to get it in your app launcher.

</details>

<details>
<summary><strong>Building the AppImage yourself</strong></summary>

Everything's already wired up: `packaging/griffin-updater.spec` is the PyInstaller spec, `packaging/run_griffin_updater.py` is the entry-point shim, `packaging/AppRun` handles launch behavior, and `packaging/build-appimage.sh` runs the whole process end to end.

```bash
bash packaging/build-appimage.sh
```

This creates an isolated venv under `build/venv`, installs `requirements.txt` plus PyInstaller into it (kept separate from your system PyQt6 so the AppImage bundles its own Qt), runs PyInstaller against the spec to produce a onedir bundle in `dist/griffin-updater/`, assembles `build/AppDir/`, and downloads `appimagetool` (cached under `build/tools/`) to produce `Griffin-Updater-x86_64.AppImage` in the project root.

PyInstaller will warn — not fail — if `libxcb-cursor0` and `libtiff5`/`libtiff6` aren't present on the build machine; it just won't bundle them, so whatever machine runs the AppImage needs them installed already. Both are extremely common on any desktop Kubuntu or Griffin Linux install, but for a fully self-contained build, run `apt install libxcb-cursor0 libtiff6` first.

</details>

<details>
<summary><strong>Scheduling internals and CLI</strong></summary>

Each enabled app gets its own pair of unit files:

```
~/.config/systemd/user/griffin-updater-<id>.service
~/.config/systemd/user/griffin-updater-<id>.timer
```

The service runs `python -m griffin_updater.cli check --id <id>`; the timer's `OnCalendar=` is generated from your schedule choice (e.g. "weekly, Sunday, 13:00" becomes `OnCalendar=Sun *-*-* 13:00:00`). `systemctl --user enable --now` runs automatically whenever an app is saved, and disabling or removing an app tears down its unit files.

Because these are user units, they inherit your desktop session's D-Bus address automatically, so `notify-send` just works with no sudo-per-user workaround needed.

If units ever get deleted or corrupted outside of Griffin Updater, **Regenerate Timers** in the toolbar (or `griffin-updater-cli install-timers`) rebuilds every app's units from scratch and cleans up any orphaned leftovers.

The same logic behind the timers is available by hand:

```bash
griffin-updater-cli check --id discord       # check and update one app
griffin-updater-cli check-all                # check and update every enabled app
griffin-updater-cli install-timers           # regenerate all systemd units from your saved app list
```

</details>

## Requesting an app be added

Join the Discord and drop it in the feature-request channel — that's faster for me to see than a PR, though `apps.json` is protected by CODEOWNERS so pull requests do get reviewed too. If you maintain a project and want it catalog-ready, make sure your release filenames/versions stay consistent, or the updater will loop on false positives — see [SECURITY.md](https://github.com/bobbycomet/GriffinUpdater/blob/main/SECURITY.md).

---

Griffin Updater is the official application updater for the [Griffin Linux project](https://bobbycomet.github.io/Griffin-Linux-Landing-Page/). The name Griffin Updater, the Griffin Linux name, and associated icons are protected under the GPLv3 to preserve the integrity of the branding in all distributed versions.

**Community and support:**
- Discord: [Join here](https://discord.gg/7fEt5W7DPh)
- Patreon (beta builds): [Patreon](https://www.patreon.com/c/BobbyComet/membership)
- Support the project: [Ko-fi](https://ko-fi.com/bobby60908)
