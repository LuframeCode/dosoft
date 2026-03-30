import ctypes
import time
from typing import List, Dict, Tuple, Optional

import win32con
import win32gui
import win32process


class DofusLogic:
    def __init__(self, config):
        self.config = config
        self.all_accounts: List[Dict] = []
        self.leader_hwnd: Optional[int] = None


    def _save_config(self, force: bool = False):
        if hasattr(self.config, "touch"):
            try:
                self.config.touch()
            except Exception:
                pass

        try:
            self.config.save(force=force)
        except TypeError:
            self.config.save()

    def _list_game_windows(self, game_version: str) -> List[Tuple[int, str]]:
        windows_found: List[Tuple[int, str]] = []

        def enum_windows_callback(hwnd, extra):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True

                title = win32gui.GetWindowText(hwnd)
                if not title.strip():
                    return True

                if game_version == "Unity":
                    if win32gui.GetClassName(hwnd) == "UnityWndClass":
                        windows_found.append((hwnd, title))
                elif game_version == "Rétro":
                    if "- Dofus Retro" in title:
                        windows_found.append((hwnd, title))
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_windows_callback, None)
        return windows_found

    def _parse_account_from_window(self, hwnd: int, title: str, game_version: str) -> Optional[Dict]:
        clean_title = title.strip()
        if not clean_title:
            return None

        if game_version == "Unity":
            if clean_title.lower().startswith("dofus"):
                return None
            parts = clean_title.split(" - ")
            pseudo = parts[0].strip()
            classe = parts[1].strip() if len(parts) > 1 else "Inconnu"
        else:
            parts = clean_title.split(" - Dofus Retro")
            pseudo = parts[0].strip()
            classe = self.config.data.get("classes", {}).get(pseudo, "Inconnu")

        active_state = self.config.data.get("accounts_state", {}).get(pseudo, True)
        team = self.config.data.get("accounts_team", {}).get(pseudo, "Team 1")

        return {
            "name": pseudo,
            "hwnd": hwnd,
            "active": active_state,
            "team": team,
            "classe": classe,
        }

    def _sync_classes(self, accounts: List[Dict]) -> bool:
        changed = False
        classes_map = self.config.data.setdefault("classes", {})

        for acc in accounts:
            pseudo = acc["name"]
            classe = acc.get("classe", "Inconnu")
            if classes_map.get(pseudo) != classe:
                classes_map[pseudo] = classe
                changed = True

        return changed

    def _sync_custom_order(self, accounts: List[Dict]) -> bool:
        changed = False
        custom_order = list(self.config.data.get("custom_order", []))
        account_names = [acc["name"] for acc in accounts]

        for name in account_names:
            if name not in custom_order:
                custom_order.append(name)
                changed = True

        if len(custom_order) > 50:
            inactive = [name for name in custom_order if name not in account_names]
            while len(custom_order) > 50 and inactive:
                to_remove = inactive.pop(0)
                if to_remove in custom_order:
                    custom_order.remove(to_remove)
                    changed = True

        if changed:
            self.config.data["custom_order"] = custom_order

        return changed

    def _sort_accounts(self, accounts: List[Dict]) -> List[Dict]:
        custom_order = self.config.data.get("custom_order", [])
        order_map = {name: idx for idx, name in enumerate(custom_order)}
        return sorted(accounts, key=lambda acc: order_map.get(acc["name"], 10**9))

    def _refresh_leader_handle(self):
        self.leader_hwnd = None
        leader_name = self.config.data.get("leader_name", "")
        for acc in self.all_accounts:
            if acc["name"] == leader_name:
                self.leader_hwnd = acc["hwnd"]
                break


    def scan_slots(self):
        game_version = self.config.data.get("game_version", "Unity")

        windows_found = self._list_game_windows(game_version)

        parsed_accounts: List[Dict] = []
        for hwnd, title in windows_found:
            account = self._parse_account_from_window(hwnd, title, game_version)
            if account is not None:
                parsed_accounts.append(account)

        classes_changed = self._sync_classes(parsed_accounts)
        order_changed = self._sync_custom_order(parsed_accounts)

        self.all_accounts = self._sort_accounts(parsed_accounts)
        self._refresh_leader_handle()

        if classes_changed or order_changed:
            self._save_config()

        return self.all_accounts


    def get_cycle_list(self):
        mode = self.config.data.get("current_mode", "ALL")
        return [
            acc
            for acc in self.all_accounts
            if acc.get("active", True) and (mode == "ALL" or acc.get("team") == mode)
        ]


    def _update_global_order_from_active(self, active_accs):
        order = list(self.config.data.get("custom_order", []))
        active_names = [acc["name"] for acc in active_accs]
        active_name_set = set(active_names)

        target_positions = [idx for idx, name in enumerate(order) if name in active_name_set]

        for pos, name in zip(target_positions, active_names):
            order[pos] = name

        self.config.data["custom_order"] = order
        self._save_config()

        order_map = {name: idx for idx, name in enumerate(order)}
        self.all_accounts.sort(key=lambda acc: order_map.get(acc["name"], 10**9))

    def set_account_position(self, name, new_index):
        active_accs = self.get_cycle_list()
        names = [acc["name"] for acc in active_accs]
        if name not in names:
            return

        old_index = names.index(name)
        acc_to_move = active_accs.pop(old_index)
        active_accs.insert(new_index, acc_to_move)
        self._update_global_order_from_active(active_accs)

    def move_account(self, name, direction):
        active_accs = self.get_cycle_list()
        names = [acc["name"] for acc in active_accs]
        if name not in names:
            return

        idx = names.index(name)
        new_idx = idx + direction
        if 0 <= new_idx < len(names):
            active_accs[idx], active_accs[new_idx] = active_accs[new_idx], active_accs[idx]
            self._update_global_order_from_active(active_accs)


    def toggle_account(self, name, is_active):
        for acc in self.all_accounts:
            if acc["name"] == name:
                acc["active"] = is_active
                break

        self.config.data.setdefault("accounts_state", {})[name] = is_active
        self._save_config()

    def change_team(self, name, new_team):
        for acc in self.all_accounts:
            if acc["name"] == name:
                acc["team"] = new_team
                break

        self.config.data.setdefault("accounts_team", {})[name] = new_team
        self._save_config()

    def set_mode(self, mode):
        self.config.data["current_mode"] = mode
        self._save_config()

    def set_leader(self, name):
        self.config.data["leader_name"] = name
        self._save_config()
        self._refresh_leader_handle()

    def _terminate_hwnd_process(self, hwnd):
        if not hwnd:
            return

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass

    def close_account_window(self, name):
        for acc in self.all_accounts:
            if acc["name"] == name:
                self._terminate_hwnd_process(acc["hwnd"])
                break

    def close_all_active_accounts(self):
        for acc in self.get_cycle_list():
            self._terminate_hwnd_process(acc["hwnd"])

    def focus_window(self, hwnd):
        if not hwnd:
            return

        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            ctypes.windll.user32.AllowSetForegroundWindow(pid)

            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def sort_taskbar(self):
        active_accs = self.get_cycle_list()
        if not active_accs:
            return

        try:
            for acc in active_accs:
                win32gui.ShowWindow(acc["hwnd"], win32con.SW_HIDE)
            time.sleep(0.3)

            for acc in active_accs:
                win32gui.ShowWindow(acc["hwnd"], win32con.SW_SHOW)
                time.sleep(0.1)

            if self.leader_hwnd:
                self.focus_window(self.leader_hwnd)
        except Exception:
            pass


    def execute_advanced_bind(self, source, identifier):
        cycle_list = self.get_cycle_list()
        if not cycle_list:
            return -1

        if source == "cycle":
            idx = identifier
            if 0 <= idx < len(cycle_list):
                self.focus_window(cycle_list[idx]["hwnd"])
                return idx
            return -1

        if source == "bind":
            pseudo = identifier
            for idx, acc in enumerate(cycle_list):
                if acc["name"] == pseudo:
                    self.focus_window(acc["hwnd"])
                    return idx

        return -1