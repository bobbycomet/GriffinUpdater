# Griffin Updater

Griffin Updater is a desktop app that keeps your non-apt software up to date automatically. If you've switched from Windows to Linux, you're probably used to apps just checking for their own updates in the background. On Linux, that's true for anything installed through your distro's package manager, but the moment you install something as a standalone `.deb` from a vendor's website or an AppImage from GitHub, you're on your own. You either remember to go check for a new version yourself, or you write a one-off script and wire it into a systemd timer by hand.

That second approach actually works well. It's exactly how a lot of unofficial Discord updaters function on Linux: a small script checks Discord's permanent download link, compares versions, downloads and installs if needed, and a systemd timer runs it on a schedule. Griffin Updater takes that pattern and generalizes it into a real application with a GUI, so it works for any `.deb` or AppImage, not just Discord, and so you don't need to write or maintain shell scripts yourself.

The result is meant to feel like the update experience Windows switchers already expect: add an app once, tell it how often to check, and forget about it. Everything else, the version comparison, the download, the install, the notification, and the systemd wiring, happens in the background.

## Requests to be added

If you have an application that you want to get added to the `apps.json` join the Discord for Griffin and put it in the feature request channel. If you try to add it yourself, it is protected by CODEOWNERS, and I will check it out, but Discord is much faster for me to see. [GRIFFIN DISCORD](https://discord.gg/fMCpeNCxhv)

If you are a developer and want to be added to the `apps.json` you will need to be sure your control files are versioned correctly with releases, otherwise false positives will loop in the updater.

## Download

Grab the latest AppImage from the Releases page, or use this direct link:

[DOWNLOAD](https://github.com/bobbycomet/GriffinUpdater/releases/download/v2.0.0/Griffin-Updater-x86_64.AppImage)

Make it executable and run it:

```bash
chmod +x Griffin-Updater-x86_64.AppImage
./Griffin-Updater-x86_64.AppImage
```

## What it does

Griffin Updater watches apps that live outside your distro's package repositories and keeps them current without you having to think about it.

Add any app by pasting a download link, or by pointing it at a GitHub repo. See "Two ways to track a version" below for when to use each.

Each app gets its own schedule, daily, weekly, monthly, or custom, like "check Discord weekly on Sunday at 1 PM." Under the hood this becomes a dedicated `systemd --user` service and timer pair, so checks run on schedule even when the GUI isn't open.

`.deb` apps are checked against the version already installed via `dpkg`, then downloaded and installed with `pkexec apt-get install -y <file>`, which prompts for authorization the same way Griffin Persona does, and resolves dependencies normally.

AppImages are downloaded into a folder you choose, defaulting to `~/Desktop`, with the option to automatically delete the previous version so old copies don't pile up.

You get a desktop notification through `notify-send` whenever an update finishes.

A shared catalog, `apps.json`, lets everyone running Griffin Updater pull the same list of pre-configured apps with one click of Update Catalog, browse them, and add whichever ones they use. You're always free to add your own untracked apps directly instead.

The interface uses Griffin's own dark theme, a flat, Steam-inspired look in gold on charcoal.

Check and Check All Now do exactly what they sound like: check a single app or every enabled app for updates on demand, outside of the scheduled runs.

## Installing from source

Debian and Ubuntu's system Python is externally managed under PEP 668, so both the requirements install and the editable install need the same flag:

```bash
cd griffin-updater
pip install -r requirements.txt --break-system-packages
pip install -e . --break-system-packages
```

If you'd rather not touch system site-packages at all, use a venv instead, just create it with `--system-site-packages` so it can see the apt-installed PyQt6 rather than pulling a second copy from PyPI:

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

Then launch it with:

```bash
griffin-updater
```

Or run it straight from the source tree without installing the package:

```bash
python3 -m griffin_updater.main
```

Drop `packaging/griffin-updater.desktop` into `~/.local/share/applications/` (and adjust `Icon=` once you've added the real PNG) to get it in your app launcher.

## Building the AppImage yourself

Everything needed is already wired up: `packaging/griffin-updater.spec` is the PyInstaller spec, `packaging/run_griffin_updater.py` is the entry-point shim, `packaging/AppRun` handles launch behavior, and `packaging/build-appimage.sh` runs the whole process end to end.

```bash
bash packaging/build-appimage.sh
```

This script creates an isolated venv under `build/venv` and installs `requirements.txt` plus PyInstaller into it, kept separate from your system PyQt6 on purpose so the AppImage bundles its own Qt and doesn't depend on what's installed on the machine that opens it. It then runs PyInstaller against the spec file, producing a onedir bundle in `dist/griffin-updater/`, assembles `build/AppDir/` with the AppRun script, desktop file, icon, and bundle, and finally downloads `appimagetool`, caching it under `build/tools/` after the first run, to produce `Griffin-Updater-x86_64.AppImage` in the project root.

One thing worth knowing: PyInstaller will warn, not fail, if `libxcb-cursor0` and `libtiff5` or `libtiff6` aren't present on the build machine. It just won't bundle them, which means whatever machine eventually runs the AppImage needs them installed already. Both are extremely common on any desktop-installed Kubuntu or Griffin Linux system, so this is unlikely to cause problems in practice, but if you want a fully self-contained AppImage, run `apt install libxcb-cursor0 libtiff6` before building.

## Two ways to track a version

Discord's download link, `https://discord.com/api/download?platform=linux&format=deb`, is a permanent endpoint. It always redirects to whatever the current build is, and the version shows up in the resulting filename. That's Static URL mode: Griffin Updater follows the redirect and pulls the version out of the final URL with a regex.

OpenTabletDriver's asset works differently. GitHub's `releases/latest/download/<filename>` pattern only works if `<filename>` stays identical release to release, but OpenTabletDriver's filename embeds the version, like `opentabletdriver_0.6.7-1_x64.deb`, so a link like that goes stale the moment `0.6.8` ships. GitHub Repo mode avoids this: you give it an owner and repo, `OpenTabletDriver` / `OpenTabletDriver`, and an asset-name regex, `x64\.deb$`, and it asks the GitHub Releases API for whatever the actual latest asset is, every time. Reach for this mode whenever a project's filenames change per release.

You can switch an app between modes, or edit its URL, owner, repo, or pattern, at any time from Edit.

## The shared catalog

Push a file shaped like this to your `Discordupdater` repo. A starter copy with Discord and OpenTabletDriver already in it lives at `resources/apps.json`.

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

Here's what each field means. `id` is a unique slug for the app, required on every entry. `name` is the display name shown in the catalog browser. `category` is either `deb` or `appimage`. `source_type` is either `static_url` or `github_release`. `description` shows up in the catalog browser. `url` applies to static_url entries and is the always-current download link. `version_regex` also applies to static_url entries; it's optional and defaults to extracting an N.N.N-style token. `github_owner` and `github_repo` apply to github_release entries and specify which repo to query. `asset_pattern` applies to github_release entries and is a regex matched against release asset filenames. `package_name` applies to deb entries and defaults to `id` if left out. **Do not use spaces in the names; use a dash "-" or em dash "—".**

Local-only fields like schedule, install location, and enabled or notify toggles aren't part of the catalog. Those get filled in by whoever adds the app, since they're personal preferences rather than facts about the app itself.

Griffin Updater points at `https://raw.githubusercontent.com/bobbycomet/Discordupdater/main/apps.json` by default. You can change this any time from Settings.

Clicking Add on a catalog row opens the normal Add/Edit dialog pre-filled, so you can still set your own schedule and, for AppImages, install folder before saving.

## How scheduling actually runs

Each enabled app gets its own pair of unit files:

```
~/.config/systemd/user/griffin-updater-<id>.service
~/.config/systemd/user/griffin-updater-<id>.timer
```

The service just runs `python -m griffin_updater.cli check --id <id>`. The timer's `OnCalendar=` value is generated from your schedule choice, so "weekly, Sunday, 13:00" becomes `OnCalendar=Sun *-*-* 13:00:00`. `systemctl --user enable --now` is called automatically whenever you save an app, so nothing extra needs to be run by hand.

Because these are user units rather than root or system units like the original Discord updater script relied on, they inherit your desktop session's D-Bus address automatically. That means `notify-send` just works, with no sudo-per-logged-in-user loop needed like the original script had to do.

Disabling or removing an app tears down its timer and service and deletes the unit files.

## CLI

The same logic as the timers call is available by hand:

```bash
griffin-updater-cli check --id discord       # check and update one app
griffin-updater-cli check-all                # check and update every enabled app
griffin-updater-cli install-timers           # regenerate all systemd units from your saved app list
```

## Known limitations

AppImages have no OS-level source of truth for their installed version, unlike `dpkg`, so that state is tracked in `~/.local/share/griffin-updater/state.json`. If that file is deleted, the next check will treat the app as a fresh install.

`pkexec` shows a graphical auth prompt for `.deb` installs, including during scheduled, non-interactive runs. If no one is logged into the graphical session when the timer fires, that install will simply fail and get logged and retried at the next scheduled check.

Static URL mode's default version regex looks for an N.N.N-style token. Some odd version schemes may need a custom regex per app, which is exactly why that field is available in Add/Edit.
