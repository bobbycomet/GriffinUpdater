# Changelog

## v2.1.0

### Fixed
- **Appify's catalog deb pattern was wrong.** The one I built earlier was
  based on filenames found in an older Appify README (`Appify-1.0.5.2.deb`)
  - the project has clearly moved on since that doc was written. The real
  current release (v3.0.1-1) ships `appify-3.0.1-1.deb` (lowercase,
  different naming entirely). Corrected and reverified against the actual
  download URL rather than the README this time.

### Added
- **Fan-Hub** added to `resources/apps.json` as a multi-variant (deb +
  AppImage) entry, verified against real release asset filenames
  (`fanhub_1.6.0_amd64.deb`, `FanHub-1.6.0-x86_64.AppImage`). The
  project's `fanhub.tar.gz` (for developers) isn't included.

## v2.1.0

### Versioning
- Minor version bump (not another `2.0.6.N` sub-release) to reflect the
  actual scope of what's landed since 2.0: per-app systemd scheduling
  with repair tooling, GitHub/Gitea release tracking, the archive
  category, update holds, self-update, catalog signing, notify-first
  consent, multi-variant catalog entries, and Debian/PPA packaging.

### Added
- **OpenRGB** and **Appify** added to `resources/apps.json` as
  multi-variant entries (both ship a `.deb` and an AppImage). Verified
  every asset pattern against real, confirmed filenames before adding
  either:
  - OpenRGB (Codeberg/Gitea): `openrgb_..._amd64_bookworm_<hash>.deb` and
    `OpenRGB_..._x86_64_<hash>.AppImage`, both taken from the actual
    release URLs provided rather than guessed.
  - Appify (GitHub): `Appify-x86_64.AppImage` and `Appify-<version>.deb`,
    taken directly from Appify's own README install instructions.
  - `package_name` for both is a best-guess (`openrgb`, `appify`) pending
    the usual `dpkg-deb -f <file> Package` confirmation once installed -
    same caveat as every other deb entry in this catalog.

## v2.0.6.3

### Fixed
- **Versioning scheme changed from hyphens to dots for sub-releases**
  (`2.0.6-01`/`2.0.6-02` → `2.0.6.1`/`2.0.6.2`, this release is `2.0.6.3`).
  Not a style preference - a hyphen in a Debian **native** package version
  is a hard policy violation, confirmed directly with `lintian`:
  `E: malformed-debian-changelog-version 2.0.6-02 (for native)`. It also
  caused `debuild -S` to interactively prompt about a missing
  `.orig.tar.gz` it had no reason to expect, since a hyphen made it think
  the package was non-native. Verified the dot-based scheme still orders
  correctly with `dpkg --compare-versions` (numerically, not lexically -
  `2.0.6.10 > 2.0.6.9` - and a real version bump still outranks any
  sub-release), and confirmed it's already valid PEP 440 with no
  normalization needed, unlike the old hyphenated form which silently
  became `2.0.6.post1` internally. `griffin_updater.__version__`,
  `setup.py`, and `debian/changelog` were all updated together and
  reverified to agree exactly (`dpkg -s griffin-updater` and the running
  app's own reported version now match) - letting these drift apart would
  hit the exact tag-vs-internal-version bug that caused the Process-Sentry
  infinite-reinstall loop earlier in this project.

## v2.0.6-02

### Added
- **Real Debian packaging** (`debian/control`, `debian/rules`,
  `debian/changelog`, `debian/copyright`, `debian/*.install`,
  `debian/source/format`) for building a `.deb` and publishing to a
  Launchpad PPA. Not just written and assumed to work - built it with
  `dpkg-buildpackage -us -uc -b`, installed the resulting `.deb` for real
  via `apt-get install`, confirmed every dependency resolved cleanly from
  Ubuntu's own archives (no bundling - deliberately different from the
  AppImage build's isolated venv approach), and confirmed the installed
  `griffin-updater`/`griffin-updater-cli` commands, desktop entry, and
  icon all actually work post-install.
- Added a top-level `LICENSE` (MIT) and `debian/copyright` - there wasn't
  a license file anywhere before this. Defaulted to MIT as a reasonable
  permissive choice since none was specified; flagged clearly as an
  assumption to revisit, not a firm decision made on your behalf.
- Documented the full PPA upload path in `README.md`, including the bits
  that can't be automated (Launchpad account/GPG key/PPA creation) and
  the multi-Ubuntu-series versioning convention (`~noble1`, `~jammy1`,
  etc.) for supporting more than one Ubuntu release from one PPA.

### Fixed
- **Icon resolution now checks real system install locations first.**
  `config.APP_ICON_PATH` previously only computed a path relative to the
  `griffin_updater` package's own directory (a sibling `resources/`
  folder) - correct for running from source or from the AppImage bundle,
  but silently wrong for a real `.deb`/`pip` install into
  `dist-packages`, which doesn't preserve that layout. Now checks the
  hicolor icon theme path, then `/usr/share/pixmaps/`, before falling
  back to the dev-tree-relative path. Found this while building the
  actual `.deb` package above and confirmed the fix by installing it for
  real rather than just reasoning about it.

## v2.0.6-01

### Added
- **Update hold**: an optional, per-app grace period (default 7 days,
  configurable 1-30) before a newly-detected update actually installs,
  giving release-day regressions time to surface and get fixed upstream
  first. Off by default - opt in per app via **Update Hold** in Add/Edit.
  - **Deliberately not a per-version timer.** The hold is anchored to a
    fixed deadline the moment it starts; a newer version showing up
    *during* the hold does not push that deadline back. This was the
    central design risk called out for this feature - a naive
    "restart the timer on every new release" implementation can never
    converge on a project with a busy release cadence, defeating the
    entire point of an auto-updater. Tested directly against the
    Day 0 (v2.0.0) / Day 3 (v2.0.1 bugfix) / Day 7 (hold expires,
    installs v2.0.1 - not v2.0.0, and not delayed to Day 10) scenario
    using a simulated clock, confirming the deadline never moves and the
    version installed at expiry is whatever's actually latest then.
  - **First-ever installs are exempt** - the hold only applies to
    upgrading something already installed; adding and installing a brand
    new app is never held, regardless of this setting.
  - **Forcing it sooner**: Check Now on a held app asks *"Are you sure
    you want to force an update? This release just came out, and the
    N-day hold is to account for possible bugs from this release."*
    Yes installs immediately and clears the hold; No leaves it as-is.
    Only offered from a single-app Check Now, never during Check All Now
    (which silently respects every hold - no per-app confirmation popups
    mid-batch).
  - `core/hold.py`'s `extend_hold()` (adds to the *existing* deadline,
    not a restart-from-now) is implemented and tested for the "user
    explicitly asks to wait longer" exception case, though there's no UI
    button wired to it yet - noted as a possible future addition, along
    with release-yanked/marked-broken detection, which none of Griffin
    Updater's current source types expose metadata for today.

### Versioning note
- Switched to `X.Y.Z-NN` version strings (this release is `2.0.6-01`)
  rather than continuing to bump the patch number every release - a
  deliberate choice, not a bug. Confirmed `dpkg --compare-versions`
  (which Griffin Updater already uses as its primary version-comparison
  method, including for self-update) handles this format correctly.

## v2.0.6

### Added
- **Multi-format catalog entries.** Some projects ship both a `.deb` and
  an AppImage for the same release - previously the only way to offer
  both in the catalog was two entirely separate app entries with
  different ids, which meant no connection between them and no way to
  steer someone toward picking just one. A catalog row can now carry a
  `variants` list instead of top-level `category`/`source_type`/etc.
  Clicking **Add** on a multi-variant row shows a choice dialog first -
  *"There is an AppImage and .deb version available for {name}. Choose
  what version you want to be tracked for updates. It will install if not
  yet already installed on your system."* - with one button per variant.
  Whichever gets picked becomes the actual tracked app; the normal
  Add/Edit dialog still follows afterward for schedule/install-location
  as usual. Rows without a `variants` list keep working exactly as
  before - fully backward compatible with every existing catalog entry.
  Tested the full flow: message wording for the 2-variant AppImage+.deb
  case, both variant choices resolving to correct AppEntry objects, the
  clean error when a multi-variant row is resolved without a variant
  chosen, an actual button click driving the dialog, and old-style
  single-format rows still working unchanged.

- **`gitea_release` source type**, for apps hosted on Codeberg or a
  self-hosted Gitea/Forgejo instance instead of GitHub. Codeberg runs
  different software with a different (if similarly-shaped) REST API, so
  it needed its own mode rather than reusing GitHub Repo. New per-app
  fields: `gitea_host` (defaults to `codeberg.org`), `gitea_owner`,
  `gitea_repo` - `asset_pattern` is shared with `github_release` since
  both APIs return assets in the same shape. Added OpenRGB to
  `resources/apps.json` as a real example.
- The GitHub/Gitea asset-picking logic was factored into one shared
  function (`_pick_asset`), so the regex-safety fix from v2.0.5 (malformed
  patterns raising a clean error instead of an uncaught `re.error`)
  automatically covers both source types instead of needing to be applied
  twice.

### Worth knowing if you add a Gitea/Codeberg app with multiple similar
### release assets (checked directly, not assumed)
- Griffin Updater picks the *first* asset matching your `asset_pattern`
  in whatever order the API returns them - unlike the archive category's
  executable-pattern matching, multiple matches here aren't treated as an
  error. Tested this against a simulated OpenRGB release (which ships
  separate `.deb` builds per Debian codename *and* per architecture side
  by side) with a loose pattern (`.*\.deb$`): it picked a different,
  wrong-architecture asset purely depending on API response ordering,
  with no error raised either time. A specific pattern like
  `^openrgb_.*_amd64_bookworm_[0-9a-f]+\.deb$` avoids this entirely by
  construction. Worth the same care on GitHub Repo entries whenever a
  release ships more than one asset of the same file type.

## v2.0.6

### Fixed
- **Catalog-lag message wrongly assumed the end user is the catalog
  maintainer.** The hint shown when Update Catalog fails used to say "if
  you just pushed a change to this file" - true for the maintainer, but
  confusing/inaccurate for the vast majority of people running Griffin
  Updater, who aren't the one editing `apps.json`. Reworded to "this can
  also just mean the maintainer recently updated apps.json," which is
  accurate regardless of who's looking at it.

## v2.0.6

### Added
- **"Regenerate Timers" button** in the toolbar (also available as
  `griffin-updater-cli install-timers`, which now does the same thing).
  Previously, if an app's `.service`/`.timer` files under
  `~/.config/systemd/user/` were deleted or corrupted by anything other
  than Griffin Updater's own Remove button, there was no way to get them
  back short of opening Edit and re-saving that one app manually. This
  regenerates every configured app's units from scratch in one pass.
- **Orphaned unit cleanup**, folded into the same action. If a
  `.service`/`.timer` pair exists on disk with no matching app in Griffin
  Updater's config at all (e.g. removed some way other than the GUI, or
  left over from an older version), Regenerate Timers now finds and
  removes those too, instead of leaving them to linger forever. Reports
  how many orphaned units were cleaned up alongside the regenerate result.

### Fixed
- **Removing an app didn't clear its stored state.** The systemd units
  were already being cleaned up correctly on Remove, but the app's
  installed-version/log history in `state.json` was left behind. Re-
  adding the same app later could silently inherit that stale state and
  report "already up to date" even though nothing had actually been
  installed since the re-add. Removing an app now clears its state too,
  so a full remove-and-re-add always starts genuinely fresh.

### Clarified (no code change needed)
- Double-checked whether Griffin Updater has an equivalent to the old
  standalone `appify-updater.sh`'s deb-vs-AppImage auto-detection bug
  (where having both installed for testing caused it to always assume
  `.deb`, even when AppImage was the one that should've been checked).
  It doesn't: `appimage_installer.py` and `archive_installer.py` never
  call `dpkg-query` at all, under any circumstance - app category is
  fixed by what you explicitly picked in Add/Edit, with no runtime
  auto-detection heuristic to get confused by having both installed
  side by side.

## v2.0.5

### Fixed
- **A malformed regex in `asset_pattern` or `version_regex` could crash
  the entire check, uncaught.** Both fields are user-editable (per-app, or
  via the shared catalog), and an easy typo like an unbalanced parenthesis
  previously caused a raw `re.error` to propagate straight out of version
  resolution instead of a clean, readable error - this surfaced while
  debugging an unrelated standalone script and turned out to apply here
  too. Both `resolve_static_url`'s `version_regex` and
  `resolve_github_release`'s `asset_pattern` now compile/match inside a
  try/except and raise a normal `VersionResolutionError` with the actual
  regex problem spelled out, instead of an uncaught exception.
- **One app's check could silently abort the rest of a `Check All`/
  `check-all` batch.** Before this fix, any *unexpected* exception during
  one app's check (the regex bug above, or anything else not already
  anticipated) would kill the whole run: in the CLI/systemd-timer path,
  every app after the failing one in that batch would simply never get
  checked, with no log entry explaining why; in the GUI, the background
  QThread would silently die mid-batch, leaving "Checking N apps..." and
  disabled buttons stuck forever, since the completion signal would never
  fire. Both the CLI's `check-all` and the GUI's Check All Now now isolate
  each app's check individually - a crash on one app is logged clearly
  and the rest of the batch still runs to completion.

### Also
- Confirmed (via a standalone script for a different, unrelated app that
  hit a parallel bug) that Griffin Updater's own GitHub-release asset
  matching already raised a clean error for "no asset matched," rather
  than the bash-specific footgun that prompted this investigation
  (a `grep -o | sed` pipeline returning nonzero under `set -e` when zero
  lines match, killing the script one line before it would have logged
  its own friendly error message - worth knowing about if you maintain
  similar bash tooling elsewhere in the Griffin suite).

## v2.0.4

### Added
- **Notify-first consent for background `.deb` installs.** When a `.deb`
  update is found by an unattended `systemd --user` timer (as opposed to
  clicking Check Now in the GUI), Griffin Updater no longer goes straight
  to the `pkexec` password prompt. It sends a plain desktop notification
  with an "Install Now" action first, and nothing privileged happens
  unless that's actually clicked. Dismissing/ignoring it just means the
  update doesn't happen this round - the next scheduled check asks again.
  GUI-triggered checks (Check Now / Check All) are unaffected and still go
  straight to the prompt, since you just explicitly asked for that.
- **Optional Ed25519 catalog signing.** `apps.json` can now be signed, and
  Griffin Updater will refuse to accept a catalog update at all unless the
  signature matches a hardcoded public key - a missing, stale, or
  tampered signature is a hard failure, not a warning. Off by default
  (leave `config.CATALOG_PUBLIC_KEY_HEX` blank to keep the old plain-HTTPS
  behavior). See `packaging/sign_catalog.py` to generate a keypair and
  sign a catalog, and `SECURITY.md` for the full writeup of what this
  does and doesn't protect against.

### Fixed
- **Status bar and table truncating long check results.** Long messages
  (e.g. the deb package-name-mismatch/version-drift notes added recently)
  were getting visually cut off in both the status bar and the table's
  Status column, with no way to see the rest. Status column cells now
  carry a full-text tooltip on hover, the column itself gets a fairer
  share of the window width, and finishing a check now auto-selects that
  app's row so the complete message is immediately visible in the
  Activity Log panel below - the status bar itself now truncates long
  messages with an explicit "see Activity Log below" pointer instead of
  just spilling off the edge of the window.
- **Catalog fetch failures right after a push now explain themselves.**
  If `Update Catalog` fails, the error now notes that a freshly-pushed
  `apps.json` can briefly fail to fetch simply because GitHub's
  raw-content CDN hasn't caught up yet - not because the file is actually
  broken - and suggests waiting a moment and trying again before assuming
  something's wrong.
- Corrected the "Features" wording for the archive category, which
  oversold executable detection as fully automatic. In practice most real
  archives (anything with more than one file inside, like Godot's .NET
  build) need an explicit executable pattern set; the same-file-with-exec-
  bit fallback only covers the simple single-file case.
- Source-install instructions now lead with a `--system-site-packages`
  venv as the recommended path, rather than `--break-system-packages`
  against the system Python (still documented as a fallback, with its
  tradeoffs spelled out, for anyone who specifically wants that instead).

## v2.0.3 and earlier

- Initial release: scheduled `.deb`/AppImage updates via per-app
  `systemd --user` timers, PolicyKit-elevated `.deb` installs, shared
  community catalog (`apps.json`) with browse/add/update-catalog support,
  Griffin Dark Theme.
- Added `.deb` package-name mismatch detection (compares the catalog's
  configured `package_name` against the actual `Package:` field inside
  the downloaded `.deb`, since a mismatch means dpkg can never confirm the
  install and every check looks like a fresh reinstall).
- Added detection for a release tag drifting from the `.deb`'s own
  internal control-file version (the Process-Sentry `v3.1.0`-tag-but-
  `3.0.0`-internal-version case) - stops an infinite reinstall loop when
  upstream forgets to bump the control file version to match a new tag.
- Added detection for a previously-installed AppImage/archive file being
  deleted or moved outside of Griffin Updater - previously this was
  incorrectly reported as "already up to date" since only the stored
  version was checked, never whether the file was actually still there.
- Added the **archive** category (zip/tar.xz extraction into a folder you
  choose, with executable-pattern matching and an optional stable symlink)
  for apps like Godot that ship as a bare archive with no package manager
  and no AppImage involved.
- Added Griffin Updater self-update (checks its own GitHub releases,
  atomically replaces the running AppImage, offers to relaunch).
- Added optional per-app SHA-256 checksum pinning.
- Added `github_release` catalog auto-conversion for `github.com/.../blob/...`
  URLs pasted into the Catalog URL setting.
