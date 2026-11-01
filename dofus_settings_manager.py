"""Safe local backup and master-profile support for Dofus Unity settings."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unicodedata
import zipfile
from datetime import datetime, timezone

from log_utils import append_rotating


PROFILE_SCHEMA = 1
PROFILE_NAME = "JEU CLASSIQUE"

# Shared options are truly global. They are intentionally limited to display,
# input, audio and interface behavior; connection data is never captured.
SHARED_UI_KEYS = {
    "channelLocked", "displayTime", "displayShortcut", "displayInfoPrefix",
    "chatColorOptions", "chatShowDamageElementIcon", "lockUI",
    "snappingDistance", "snappingGap", "notificationsAlphaWindows",
    "notificationsMode", "notificationsDisplayDuration", "volumeGlobal",
    "volumeMenu", "volumeAmbiance", "volumeBarks", "volumeSfx",
    "volumeMusic", "playSoundAtTurnStart", "playSoundOnPrivateMessage",
    "playSoundOnTeamMessage", "playSoundOnGuildMessage",
    "playSoundOnAllianceMessage", "playSoundOnPartyMessage", "allowAnimShake",
    "bindingOverrides", "displaySlaveUIs", "updateUiFromSlaves",
    "windowDisplayMode", "windowResolutionMode", "displayAuras",
    "alwaysShowAuraOnFront", "fps", "vsync", "hdrEnabled",
    "antiAliasingMode", "msaaQuality", "smaaQuality", "dofusQuality",
    "currentTexturePack", "renderingScale", "allowMapEffects",
    "mapArrowColor", "currentTheme", "globalFontSize", "uiScale",
    "useDefaultScale", "displayBreedPictoForWindow",
}

# These names and fragments cover account-scoped interface state while keeping
# histories, social data, favorites and character progression untouched.
ACCOUNT_UI_KEYS = {
    "autoFocusApp", "enableDelayBeforeSkipTurn", "actionBarPageIndex",
    "statsActions", "tabsPerChat", "currentChatTheme", "defaultHeight",
    "extendedHeight", "keyboardLang", "turnPicture", "seePings",
    "mapCoordinates", "showTooltipShortcuts", "showItemTooltipDescription",
    "showItemTooltipAvgPrice", "remindTurn", "showUsedPaPm",
    "largeTooltipDelay", "itemTooltipDelay",
    "alwaysDisplayTheoreticalEffectsInTooltip",
    "cumulateBonusInSpellTooltips", "displayTooltips", "bigMenuButton",
    "allowSpellEffects", "showMovementDistance", "showMovementArea",
    "showTurnsRemaining", "mapUIFilters", "mapFiltersMiniMap", "showMapGrid",
    "showMiniMapGrid", "fightEntityTooltipShowPing",
    "fightEntityTooltipShowClass", "fightEntityTooltipShowEntity",
    "fightEntityTooltipShowVitalGauges", "fightEntityTooltipShowVitalValues",
    "fightEntityTooltipShowStates", "fightEntityTooltipShowVitalPercent",
    "showPermanentTargetsTooltips", "animateFightPreviewTooltips",
    "showDamagesPreview", "showMovePreview",
    "spectatorAutoShowCurrentFighterInfo", "entityStatesDisplayMode",
    "healthBarDisplayMode", "hBarIsHideWhenFull", "widgetsSettings",
    "questListWidgetOptions", "treasureHuntWidgetSettings",
    "infiniteDreamWidgetSettings", "actionBarsWidgetOptions",
    "partyWidgetOptions", "characterInfosWidgetOptions", "chatWidgetOptions",
    "dialogFontSize", "dialogAnimationEnabled", "gaugesWidgetColors",
    "gaugesWidgetOptions", "timelineTileSize", "timelineGaugePlacement",
    "timelineOrientation", "timelineSizedAutomatically",
    "timelineShowDeadFighters", "timelineShowSummonedFighters",
    "timelineShowFightersOrder", "timelineFollowPlayingEntity",
    "challengeSelectionIsInHorizontalOrientation",
    "companionSlaveUIOrientationIsHorizontal", "summonedSlaveUiGrouped",
    "buffsUISizedAutomatically", "buffsUiSelectedTab", "foldedChat",
    "pointsOverhead", "creaturesMode", "alwaysShowGrid",
    "alwaysShowGridFight", "transparentOverlayMode",
    "transparentOverlayModeFight", "creatureModeRoleplay",
    "creatureModeFight", "hideBlackBorder", "worldmapMenuIsHidden",
    "notificationPosition", "spellUiSize", "fighterInfosPosition",
    "bannerMenuButtonPosition", "bannerMenuButtonPositionTemporis",
}


class DofusSettingsError(RuntimeError):
    pass


class DofusSettingsManager:
    def __init__(self, game_root: Path | None = None, data_root: Path | None = None,
                 branch: str = "RELEASE", translator=None):
        self._translator = translator
        local_low = Path.home() / "AppData" / "LocalLow"
        self.game_root = Path(game_root or (local_low / "Ankama" / "Dofus"))
        self.branch = branch.upper()
        self.settings_root = self.game_root / self.branch
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        self.data_root = Path(data_root or (appdata / "DOSOFT" / "dofus-display"))
        self.profile_dir = self.data_root / "profiles"
        self.backup_dir = self.data_root / "backups" / self.branch
        self.profile_path = self.profile_dir / f"{PROFILE_NAME}.json"
        self.log_path = self.data_root / "dofus-display-debug.log"

    def _record(self, message):
        append_rotating(self.log_path, f"{datetime.now().isoformat(timespec='seconds')} {message}")

    def _t(self, key, default, **values):
        text = self._translator(key, default) if callable(self._translator) else default
        try:
            return text.format(**values)
        except (KeyError, ValueError, IndexError):
            return text

    def _read_json(self, path: Path, attempts=5, retry_delay=0.12):
        """Read a Dofus JSON after its atomic rewrite window has settled.

        Dofus can truncate a file just before replacing its contents. A read in
        that very short interval previously produced the unhelpful
        ``Expecting value: line 1 column 1`` error seen by the user.
        """
        last_error = None
        for attempt in range(max(1, int(attempts))):
            try:
                raw = path.read_text(encoding="utf-8-sig")
                if not raw.strip():
                    raise json.JSONDecodeError("fichier momentanément vide", raw, 0)
                return json.loads(raw)
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                last_error = error
                if attempt + 1 < attempts:
                    time.sleep(retry_delay)
        self._record(f"READ_FAILED path={path} attempts={attempts} error={last_error}")
        raise DofusSettingsError(self._t(
            "dofus_error_invalid_file",
            "Fichier Dofus invalide après {attempts} tentatives :\n{path}\n\nDétail : {error}\nFermez complètement Dofus puis réessayez.",
            attempts=attempts, path=path, error=last_error,
        )) from last_error

    @staticmethod
    def _write_json_atomic(path: Path, value):
        data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        json.loads(data)
        DofusSettingsManager._write_bytes_atomic(path, data)

    @staticmethod
    def _write_bytes_atomic(path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix=path.name + ".dosoft-", suffix=".tmp", dir=path.parent)
        temporary = Path(filename)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _shared_options(self):
        """An empty shared options file does not invalidate account presets.

        Do not invent defaults or fall back silently for a non-empty malformed
        document. The existing master profile can retain its allowlisted
        shared entries when capturing while this optional file is empty.
        """
        path = self.settings_root / "Shared" / "dofus.json"
        try:
            empty = not path.read_bytes().decode("utf-8-sig").strip()
        except FileNotFoundError:
            empty = True
        if empty:
            self._record("SHARED_OPTIONS_EMPTY: account presets remain usable")
            return {}, True
        return self._read_json(path), False

    def _commit_files(self, updates, label):
        """Preflight every JSON and retain exact originals for error rollback."""
        for path, data in updates.items():
            if path.suffix.casefold() == ".json":
                json.loads(data.decode("utf-8-sig"))
        rollback = self.create_backup(label)
        self._require_closed()
        originals = {path: path.read_bytes() if path.exists() else None for path in updates}
        written = []
        try:
            for path, data in updates.items():
                self._write_bytes_atomic(path, data)
                written.append(path)
        except Exception:
            failures = []
            for path in reversed(written):
                try:
                    if originals[path] is None:
                        path.unlink(missing_ok=True)
                    else:
                        self._write_bytes_atomic(path, originals[path])
                except OSError as error:
                    failures.append(f"{path}: {error}")
            self._record(f"WRITE_FAILED rollback={rollback} recovery_errors={failures}")
            if failures:
                raise DofusSettingsError(self._t(
                    "dofus_error_rollback_failed",
                    "Écriture interrompue. La récupération automatique est incomplète. Vos fichiers originaux sont conservés dans : {path}",
                    path=rollback,
                ))
            raise
        self._record(f"WRITE_OK files={len(updates)} rollback={rollback.name}")
        return rollback

    @staticmethod
    def _json_bytes(value):
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    @staticmethod
    def _unwrap(container, key, default=None):
        entry = container.get(key)
        if isinstance(entry, dict) and "value" in entry:
            return entry["value"]
        return entry if entry is not None else default

    @staticmethod
    def _set_value(container, key, value, source_entry=None):
        if isinstance(container.get(key), dict) and "value" in container[key]:
            container[key]["value"] = copy.deepcopy(value)
        elif isinstance(source_entry, dict):
            container[key] = copy.deepcopy(source_entry)
        else:
            container[key] = {"value": copy.deepcopy(value)}

    @staticmethod
    def _normalized(value):
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        return " ".join(
            "".join(character for character in normalized if not unicodedata.combining(character))
            .casefold().replace("à", "a").split()
        )

    @staticmethod
    def _sha256(data: bytes):
        return hashlib.sha256(data).hexdigest()

    def is_dofus_running(self):
        try:
            completed = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=4, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for row in csv.reader(io.StringIO(completed.stdout)):
                executable = row[0].strip('"').casefold() if row else ""
                if executable == "dofus.exe" or (
                    executable.startswith("dofus") and executable.endswith(".exe")
                ):
                    return True
        except (OSError, subprocess.SubprocessError):
            pass
        return False

    def _require_closed(self):
        if self.is_dofus_running():
            raise DofusSettingsError(self._t(
                "dofus_error_close_clients",
                "Fermez tous les clients Dofus avant cette opération. Un client ouvert pourrait réécrire les anciens réglages.",
            ))

    def _account_dirs(self):
        accounts = self.settings_root / "Accounts"
        return sorted((item for item in accounts.iterdir() if item.is_dir()), key=lambda p: p.name) \
            if accounts.exists() else []

    def _reference_account(self):
        candidates = []
        for account in self._account_dirs():
            dofus_file = account / "dofus.json"
            preset_file = account / "preset.json"
            if dofus_file.exists() and preset_file.exists():
                candidates.append((max(dofus_file.stat().st_mtime, preset_file.stat().st_mtime), account))
        if not candidates:
            raise DofusSettingsError(self._t("dofus_error_no_account", "Aucun compte Dofus configuré n'a été trouvé."))
        return max(candidates, key=lambda item: item[0])[1]

    def _version(self):
        path = self.settings_root / "version"
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return "inconnue"

    def status(self):
        accounts = self._account_dirs() if self.settings_root.exists() else []
        backups = sorted(self.backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True) \
            if self.backup_dir.exists() else []
        return {
            "available": self.settings_root.exists(),
            "running": self.is_dofus_running(),
            "version": self._version(),
            "accounts": len(accounts),
            "profile_exists": self.profile_path.exists(),
            "last_backup": backups[0].name if backups else "Aucune",
        }

    def _settings_files(self):
        """Return only global and account-level settings managed by DOSOFT.

        ``Accounts/<id>/Characters`` contains per-character cache/state. It is
        deliberately excluded: JEU CLASSIQUE must neither validate nor restore
        those files, and Dofus installations commonly contain old empty JSON
        files there.
        """
        files = []
        version = self.settings_root / "version"
        if version.exists():
            files.append(version)
        shared = self.settings_root / "Shared"
        if shared.exists():
            files.extend(path for path in shared.rglob("*") if path.is_file())
        for account in self._account_dirs():
            files.extend(path for path in account.iterdir() if path.is_file())
        return sorted(files)

    def create_backup(self, label="manuel"):
        self._require_closed()
        if not self.settings_root.exists():
            raise DofusSettingsError(self._t("dofus_error_settings_missing", "Le dossier de réglages Dofus RELEASE est introuvable."))
        files = self._settings_files()
        if not files:
            raise DofusSettingsError(self._t("dofus_error_nothing_to_backup", "Aucun réglage Dofus à sauvegarder."))
        # A safety snapshot must work even when the state being repaired is
        # damaged. Keep those exact bytes in quarantine, never in the set of
        # files eligible for restoration. Read once to hash what is archived.
        snapshot = {path: path.read_bytes() for path in files}
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        safe_label = "".join(c if c.isalnum() or c in "-_" else "-" for c in label).strip("-")
        destination = self.backup_dir / f"Dofus-{self.branch}-{self._version()}-{timestamp}-{safe_label}.zip"
        temporary = destination.with_suffix(".zip.tmp")
        manifest = {
            "schema": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "branch": self.branch,
            "game_version": self._version(),
            "files": {},
            "quarantined_files": {},
        }
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for path, data in snapshot.items():
                    relative = path.relative_to(self.settings_root).as_posix()
                    if path.suffix.casefold() == ".json":
                        try:
                            json.loads(data.decode("utf-8-sig"))
                        except (UnicodeError, json.JSONDecodeError) as error:
                            quarantine = "DOSOFT-QUARANTINE/" + relative
                            archive.writestr(quarantine, data)
                            manifest["quarantined_files"][relative] = {
                                "archive_path": quarantine,
                                "sha256": self._sha256(data),
                                "error": str(error),
                            }
                            self._record(f"BACKUP_QUARANTINE path={relative} bytes={len(data)}")
                            continue
                    manifest["files"][relative] = self._sha256(data)
                    archive.writestr(relative, data)
                archive.writestr(
                    "DOSOFT-MANIFEST.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
                )
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        self._record(f"BACKUP_OK name={destination.name} valid={len(manifest['files'])} quarantined={len(manifest['quarantined_files'])}")
        return destination

    def backup_warning(self, archive_path):
        with zipfile.ZipFile(archive_path, "r") as archive:
            manifest = json.loads(archive.read("DOSOFT-MANIFEST.json"))
        count = len(manifest.get("quarantined_files", {}))
        if not count:
            return ""
        return self._t(
            "dofus_display_quarantine_warning",
            "{count} fichier(s) vide(s) ou invalide(s) conservé(s) à part dans l'archive ; ils ne seront pas restaurés. Détails : dofus-display-debug.log.",
            count=count,
        )

    @staticmethod
    def _pick_preset(saved, wanted, fallback):
        wanted_normalized = {DofusSettingsManager._normalized(name) for name in wanted}
        for preset in saved:
            if DofusSettingsManager._normalized(preset.get("presetName")) in wanted_normalized:
                return copy.deepcopy(preset)
        return copy.deepcopy(fallback) if isinstance(fallback, dict) else None

    def capture_master_profile(self):
        self._require_closed()
        reference = self._reference_account()
        shared_dofus_path = self.settings_root / "Shared" / "dofus.json"
        shared_preset_path = self.settings_root / "Shared" / "preset.json"
        shared_dofus, shared_empty = self._shared_options()
        shared_preset = self._read_json(shared_preset_path)
        account_dofus = self._read_json(reference / "dofus.json")
        account_preset = self._read_json(reference / "preset.json")
        saved_presets = self._unwrap(shared_preset, "savedPresets", []) or []
        current = self._unwrap(account_preset, "currentPreset")
        current_fight = self._unwrap(account_preset, "currentFightPreset")
        normal_preset = self._pick_preset(
            saved_presets, ("Affichage classique", "JEU CLASSIQUE"), current
        )
        fight_preset = self._pick_preset(
            saved_presets, ("Combat a 8", "Combat à 8"), current_fight
        )
        if not normal_preset or not fight_preset:
            raise DofusSettingsError(self._t(
                "dofus_error_presets_incomplete",
                "Les presets normal et combat sont incomplets. Enregistrez-les d'abord dans Dofus.",
            ))
        shared_entries = {
            key: copy.deepcopy(shared_dofus[key]) for key in SHARED_UI_KEYS if key in shared_dofus
        }
        warnings = []
        if shared_empty:
            # Preserve the last known good global options instead of erasing
            # them in the master when the live shared file is truncated.
            if self.profile_path.exists():
                previous = self._read_json(self.profile_path)
                if previous.get("schema") != PROFILE_SCHEMA or previous.get("branch") != self.branch:
                    raise DofusSettingsError(self._t("dofus_error_master_incompatible", "Le profil maître utilise une version incompatible."))
                shared_entries = {
                    key: copy.deepcopy(entry) for key, entry in previous.get("shared_entries", {}).items()
                    if key in SHARED_UI_KEYS
                }
            warnings.append(self._t(
                "dofus_display_shared_empty",
                "Le fichier global Dofus est vide ou absent. Les interfaces des comptes sont enregistrées ; les réglages globaux du profil précédent sont conservés s'ils existent.",
            ))
        profile = {
            "schema": PROFILE_SCHEMA,
            "name": PROFILE_NAME,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "branch": self.branch,
            "game_version": self._version(),
            "shared_entries": shared_entries,
            "account_entries": {
                key: copy.deepcopy(account_dofus[key])
                for key in ACCOUNT_UI_KEYS if key in account_dofus
            },
            "normal_preset": normal_preset,
            "fight_preset": fight_preset,
        }
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        if self.profile_path.exists():
            # Keep the former master before replacing it with a newly captured
            # layout (the game may already have reset that new layout).
            backup = self.profile_path.with_name(f"JEU CLASSIQUE-{datetime.now():%Y%m%d-%H%M%S-%f}.json")
            self._write_bytes_atomic(backup, self.profile_path.read_bytes())
        self._write_json_atomic(self.profile_path, profile)
        self._record(f"CAPTURE_OK reference={reference.name} shared={len(shared_entries)} account={len(profile['account_entries'])} shared_empty={shared_empty}")
        return {
            "path": self.profile_path,
            "shared": len(profile["shared_entries"]),
            "account": len(profile["account_entries"]),
            "normal": normal_preset.get("presetName", "Interface normale"),
            "fight": fight_preset.get("presetName", "Interface de combat"),
            "warnings": warnings,
        }

    @staticmethod
    def _upsert_preset(saved, preset):
        target_name = DofusSettingsManager._normalized(preset.get("presetName"))
        target_uid = preset.get("uid")
        for index, existing in enumerate(saved):
            if ((target_uid is not None and existing.get("uid") == target_uid)
                    or DofusSettingsManager._normalized(existing.get("presetName")) == target_name):
                saved[index] = copy.deepcopy(preset)
                return
        saved.append(copy.deepcopy(preset))

    def apply_master_profile(self):
        self._require_closed()
        if not self.profile_path.exists():
            raise DofusSettingsError(self._t("dofus_error_master_missing", "Créez d'abord le profil maître JEU CLASSIQUE."))
        profile = self._read_json(self.profile_path)
        if profile.get("schema") != PROFILE_SCHEMA or profile.get("branch") != self.branch:
            raise DofusSettingsError(self._t("dofus_error_master_incompatible", "Le profil maître utilise une version incompatible."))
        updates = {}
        shared_dofus_path = self.settings_root / "Shared" / "dofus.json"
        shared_dofus, _ = self._shared_options()
        for key, entry in profile.get("shared_entries", {}).items():
            if key in SHARED_UI_KEYS:
                self._set_value(shared_dofus, key, self._unwrap({key: entry}, key), entry)
        if shared_dofus:
            updates[shared_dofus_path] = self._json_bytes(shared_dofus)

        shared_preset_path = self.settings_root / "Shared" / "preset.json"
        shared_preset = self._read_json(shared_preset_path)
        saved = list(self._unwrap(shared_preset, "savedPresets", []) or [])
        self._upsert_preset(saved, profile["normal_preset"])
        self._upsert_preset(saved, profile["fight_preset"])
        self._set_value(shared_preset, "savedPresets", saved, shared_preset.get("savedPresets"))
        updates[shared_preset_path] = self._json_bytes(shared_preset)

        updated = 0
        for account in self._account_dirs():
            dofus_path = account / "dofus.json"
            preset_path = account / "preset.json"
            if not dofus_path.exists() or not preset_path.exists():
                continue
            account_dofus = self._read_json(dofus_path)
            for key, entry in profile.get("account_entries", {}).items():
                if key in ACCOUNT_UI_KEYS:
                    self._set_value(account_dofus, key, self._unwrap({key: entry}, key), entry)
            updates[dofus_path] = self._json_bytes(account_dofus)

            account_preset = self._read_json(preset_path)
            self._set_value(
                account_preset, "currentPreset", profile["normal_preset"],
                account_preset.get("currentPreset"),
            )
            self._set_value(
                account_preset, "currentFightPreset", profile["fight_preset"],
                account_preset.get("currentFightPreset"),
            )
            fight_uid = profile["fight_preset"].get("uid")
            current_fight_id = self._unwrap(account_preset, "fightPresetId")
            if fight_uid is not None and (current_fight_id is None or isinstance(fight_uid, type(current_fight_id))):
                self._set_value(
                    account_preset, "fightPresetId", fight_uid,
                    account_preset.get("fightPresetId"),
                )
            # Reapplying saved positions while leaving a pending reset request
            # enabled allows the client to discard them on its next launch.
            self._set_value(account_preset, "resetUIPositions", False)
            updates[preset_path] = self._json_bytes(account_preset)
            updated += 1
        if not updated:
            raise DofusSettingsError(self._t("dofus_error_no_account", "Aucun compte Dofus configuré n'a été trouvé."))
        rollback = self._commit_files(updates, "avant-application-jeu-classique")
        self._record(f"APPLY_OK accounts={updated} resetUIPositions=false")
        return {"accounts": updated, "rollback": rollback}

    def latest_backup(self):
        if not self.backup_dir.exists():
            return None
        backups = sorted(self.backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        return backups[0] if backups else None

    def _validated_archive(self, archive_path):
        archive_path = Path(archive_path)
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                manifest = json.loads(archive.read("DOSOFT-MANIFEST.json").decode("utf-8"))
                validated = {}
                if manifest.get("branch") != self.branch:
                    raise DofusSettingsError(self._t("dofus_error_master_incompatible", "Le profil maître utilise une version incompatible."))
                for relative, info in manifest.get("quarantined_files", {}).items():
                    # Preserve damaged originals for manual recovery, but never
                    # consider them usable game configuration.
                    expected_path = "DOSOFT-QUARANTINE/" + relative
                    if info.get("archive_path") != expected_path:
                        raise DofusSettingsError(self._t("dofus_error_unsafe_archive_path", "Archive refusée : chemin de fichier non sûr."))
                    if self._sha256(archive.read(expected_path)) != info.get("sha256"):
                        raise DofusSettingsError(self._t("dofus_error_corrupt_archive", "Archive corrompue : {path}", path=relative))
                for relative, expected_hash in manifest.get("files", {}).items():
                    relative_path = Path(relative)
                    if relative_path.is_absolute() or ".." in relative_path.parts:
                        raise DofusSettingsError(self._t("dofus_error_unsafe_archive_path", "Archive refusée : chemin de fichier non sûr."))
                    is_shared = len(relative_path.parts) >= 2 and relative_path.parts[0] == "Shared"
                    is_account_root = (
                        len(relative_path.parts) == 3
                        and relative_path.parts[0] == "Accounts"
                    )
                    if not is_shared and not is_account_root and relative != "version":
                        # Compatibility with backups produced before DOSOFT
                        # stopped archiving per-character state. Verify their
                        # hash, but never restore them.
                        data = archive.read(relative)
                        if self._sha256(data) != expected_hash:
                            raise DofusSettingsError(self._t("dofus_error_corrupt_archive", "Archive corrompue : {path}", path=relative))
                        continue
                    if not relative.startswith(("Shared/", "Accounts/")) and relative != "version":
                        raise DofusSettingsError(self._t("dofus_error_archive_content", "Archive refusée : contenu inattendu."))
                    data = archive.read(relative)
                    if self._sha256(data) != expected_hash:
                        raise DofusSettingsError(self._t("dofus_error_corrupt_archive", "Archive corrompue : {path}", path=relative))
                    if relative_path.suffix.casefold() == ".json":
                        json.loads(data.decode("utf-8-sig"))
                    validated[relative] = data
                return manifest, validated
        except (OSError, UnicodeError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as error:
            raise DofusSettingsError(self._t("dofus_error_backup_unreadable", "Sauvegarde illisible : {error}", error=error)) from error

    def restore_latest_backup(self):
        self._require_closed()
        target = self.latest_backup()
        if target is None:
            raise DofusSettingsError(self._t("dofus_display_no_backup", "Aucune sauvegarde DOSOFT n'est disponible."))
        manifest, files = self._validated_archive(target)
        # Keep the current game's version marker. Restoring old JSON through a
        # patch update is safer than pretending an older client version is live.
        updates = {}
        for relative, data in files.items():
            if relative == "version":
                continue
            destination = self.settings_root / Path(relative)
            if destination.name == "preset.json" and relative.startswith("Accounts/"):
                preset = json.loads(data.decode("utf-8-sig"))
                self._set_value(preset, "resetUIPositions", False)
                data = self._json_bytes(preset)
            updates[destination] = data
        if not updates:
            raise DofusSettingsError(self._t("dofus_error_nothing_to_backup", "Aucun réglage Dofus à sauvegarder."))
        rollback = self._commit_files(updates, "avant-restauration")
        self._record(f"RESTORE_OK source={target.name} files={len(updates)}")
        return {
            "archive": target,
            "rollback": rollback,
            "game_version": manifest.get("game_version", "inconnue"),
            "files": len(files) - (1 if "version" in files else 0),
        }
