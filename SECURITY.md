# Security Policy

Griffin Updater downloads and installs software on the user's behalf, in
some cases with root privileges. This document describes what it actually
does from a security standpoint, what it doesn't (yet) protect against, and
how to report a problem.

## Supported Versions

| Version | Supported |
|---|---|
| 2.0.x (current) | ✅ |
| Pre-release / dev builds | ❌ (fix forward, not backported) |

This is a single-maintainer project. Only the latest tagged release
gets security fixes; there's no long-term-support branch at this time.

## Reporting a Vulnerability

Please **don't open a public GitHub issue** for anything that could be
exploited before a fix ships (e.g. a way to make Griffin Updater run
arbitrary code, escalate privileges beyond what's documented below, or
escape its install directories).

Instead:

- Use **Discord**: https://discord.gg/CqEWWp4N2a
    Contact me directly with:
  - What you found and why it's exploitable
  - Steps to reproduce, or a PoC if you have one
  - Affected version/commit

You should get an acknowledgment within a few days. This is a solo-
maintained project, so response and fix time will vary with real life,
if something is under active exploitation, say so and it'll be prioritized.

Non-security bugs (crashes, a check that never settles, a mis-named file,
etc.) should go through normal public Issues, not this process.

## Threat Model / What Griffin Updater Actually Does

Being direct about this, since "an app that updates other apps for you" is
inherently a sensitive category of software:

### Privilege elevation
- `.deb` installs run as `pkexec apt-get install -y <path>`. `pkexec` pops
  the standard PolicyKit authentication dialog — Griffin Updater itself
  never stores, prompts for, or handles your password; that's entirely
  PolicyKit's job. Nothing else in the app runs as root.
- AppImage installs never elevate. They're just files copied into a
  directory you chose (default `~/Desktop`) and marked executable for your
  own user — same trust level as downloading and `chmod +x`-ing something
  yourself.

### What's trusted, and by whom
- **Per-app source URLs / GitHub owner-repo you configure yourself**:
  Griffin Updater will download and (for `.deb`) `pkexec`-install whatever
  comes back from that URL or from the matched GitHub release asset, on
  the schedule you set. This is by design, it's an updater, but it means
  the security of any given app entry is only as good as the URL/repo you
  pointed it at. Don't add sources you don't trust.
- **The shared catalog (`apps.json`)**: entries you add via "Browse
  Catalog" ultimately become the same kind of locally-trusted app entry
  described above. The catalog file itself is fetched over HTTPS from
  wherever `Settings → Catalog URL` points (raw GitHub content by
  default), but **it is not signed and Griffin Updater does not verify who
  wrote it** — it's a plain JSON file. Anyone with push/PR access to
  whatever repo you point the catalog at can add or modify entries that
  every Griffin Updater install pulling from it will subsequently offer as
  "Add"-able apps. If you maintain a catalog others rely on:
  - Turn on branch protection on `main` and require review before merge.
  - Don't accept catalog PRs that add a source you (as maintainer) haven't
    personally verified belongs to the project it claims to.
  - Treat catalog compromise as equivalent in severity to a supply-chain
    compromise, because for anyone who's added that entry, it is one.

### Integrity verification
- **Optional per-app SHA-256 pinning** exists (`sha256` field on an app
  entry, or in a catalog row). If set, the downloaded file's hash is
  checked before install; a mismatch aborts the install and the file is
  deleted, no exceptions. This is opt-in per app, and blank by default.
  - **Important caveat**: pinning a hash only makes sense for a fixed
    release you don't intend to auto-track past that build, since every
    new upstream version has a different hash by definition. For apps you
    want to keep auto-updating indefinitely (which is the normal use case
    here), leave `sha256` blank, there's currently no mechanism to pin a
    hash per-version automatically.
- There is **no code signing / GPG verification** of `.deb` packages or
  AppImages beyond what `apt`/`dpkg` themselves already do (e.g. `apt`
  will still enforce repository-level signature checks for *packages
  installed the normal way*; `pkexec apt-get install -y <local file>`
  installs a local file directly and does not require it to be signed).
  This mirrors how manually downloading and installing a `.deb` yourself
  works today - Griffin Updater doesn't add a new hole, but it also
  doesn't close the existing one. Use the optional checksum field above,
  or a source with its own signing story, where that matters to you.
- GitHub Releases lookups go through the public, unauthenticated
  `api.github.com` REST API. No token is stored or required; this does
  mean check frequency is subject to GitHub's unauthenticated rate limits.

### Local storage
- Nothing sensitive (passwords, tokens, secrets) is stored by Griffin
  Updater. Local files are your app list (`~/.config/griffin-updater/`),
  cached catalog + per-app state/logs (`~/.local/share/griffin-updater/`),
  and generated `systemd --user` unit files. All are plain, human-readable
  JSON/INI-style text, not encrypted, and not intended to hold secrets -
  don't put credentials in a URL field, for instance.
- Scheduled checks run as `systemd --user` units, i.e. with your own user's
  permissions and D-Bus session - not root, not another user's session.

### Known gaps / not yet mitigated
- No sandboxing of the download → install pipeline beyond what `apt`/`dpkg`
  provide natively for `.deb`s.
- No built-in allowlist/denylist of domains for the "Static URL" or
  "GitHub Repo" source types - any app entry can point anywhere.
- The catalog has no maintainer-signing or provenance mechanism (see
  above) - it's a bare JSON file today, by design simplicity, not by an
  oversight that's been decided against fixing. If catalog adoption grows
  beyond "friends trusting friends," this is the first thing that should
  change (e.g. requiring signed commits, or a maintainer-curated
  allowlist rather than open community PRs).

If you find a way to turn any of the above into something better than what's
described, e.g., a way to get code execution *without* going through the
PolicyKit prompt, or a way to make Griffin Updater write outside the
directories it's supposed to - that's exactly what the reporting process
above is for.
