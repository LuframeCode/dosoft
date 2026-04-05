import win32gui
import win32con
import ctypes
import win32process
import time

class DofusLogic:
    def __init__(self, config):
        self.config = config
        self.all_accounts = []
        self.leader_hwnd = None

    def scan_slots(self):
        game_version = self.config.data.get("game_version", "Unity")
        windows_trouvees = []

        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                titre = win32gui.GetWindowText(hwnd)
                if not titre.strip(): return True
                
                if game_version == "Unity":
                    if win32gui.GetClassName(hwnd) == "UnityWndClass":
                        windows_trouvees.append((hwnd, titre))
                elif game_version == "Rétro":
                    if "Dofus Retro" in titre:
                        windows_trouvees.append((hwnd, titre))
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        nouveaux_comptes = []
        menu_counter = 1 # Compteur pour différencier les fenêtres sans perso

        for hwnd, titre in windows_trouvees:
            titre_clean = titre.strip()
            is_menu = False
            
            if game_version == "Unity":
                # Si le titre commence par "dofus" (ex: "Dofus", "Dofus 3.0"), c'est souvent la page de connexion sans perso
                if titre_clean.lower().startswith("dofus"): 
                    pseudo = f"Menu Unity {menu_counter}"
                    classe = "Inconnu"
                    is_menu = True
                    menu_counter += 1
                else:
                    parts = titre_clean.split(" - ")
                    pseudo = parts[0].strip()
                    classe = parts[1].strip() if len(parts) > 1 else "Inconnu"
            else:
                # Mode Rétro : Si ça commence par "Dofus Retro" sans pseudo devant
                if titre_clean.startswith("Dofus Retro") or " - " not in titre_clean:
                    pseudo = f"Menu Rétro {menu_counter}"
                    classe = "Inconnu"
                    is_menu = True
                    menu_counter += 1
                else:
                    parts = titre_clean.split(" - Dofus Retro")
                    pseudo = parts[0].strip()
                    classe = self.config.data["classes"].get(pseudo, "Inconnu")
                
            self.config.data["classes"][pseudo] = classe
            etat_actif = self.config.data["accounts_state"].get(pseudo, True)
            equipe = self.config.data["accounts_team"].get(pseudo, "Team 1")
            
            # On ajoute la clé "is_menu" pour indiquer à l'UI que c'est une page de connexion
            nouveaux_comptes.append({'name': pseudo, 'hwnd': hwnd, 'active': etat_actif, 'team': equipe, 'classe': classe, 'is_menu': is_menu})

        custom_order = self.config.data.get("custom_order", [])
        
        for acc in nouveaux_comptes:
            if acc['name'] not in custom_order:
                custom_order.append(acc['name'])
                
        if len(custom_order) > 50:
            active_names = [acc['name'] for acc in nouveaux_comptes]
            inactive = [n for n in custom_order if n not in active_names]
            while len(custom_order) > 50 and inactive:
                to_remove = inactive.pop(0)
                if to_remove in custom_order:
                    custom_order.remove(to_remove)
                    
        self.config.data["custom_order"] = custom_order
        self.config.save()
        
        self.all_accounts = sorted(nouveaux_comptes, key=lambda x: custom_order.index(x['name']))
        
        self.leader_hwnd = None
        leader_name = self.config.data.get("leader_name", "")
        for acc in self.all_accounts:
            if acc['name'] == leader_name: self.leader_hwnd = acc['hwnd']
                
        return self.all_accounts

    def get_cycle_list(self):
        mode = self.config.data.get("current_mode", "ALL")
        return [acc for acc in self.all_accounts if acc['active'] and (mode == "ALL" or acc['team'] == mode)]

    def _update_global_order_from_active(self, active_accs):
        order = self.config.data.get("custom_order", [])
        indices = []
        valid_names = []
        for acc in active_accs:
            if acc['name'] in order:
                indices.append(order.index(acc['name']))
                valid_names.append(acc['name'])
                
        indices.sort()
        for i, name in zip(indices, valid_names):
            order[i] = name
            
        self.config.data["custom_order"] = order
        self.config.save()
        self.all_accounts.sort(key=lambda x: order.index(x['name']))

    def set_account_position(self, name, new_index):
        active_accs = self.get_cycle_list()
        names = [a['name'] for a in active_accs]
        if name not in names: return
        idx = names.index(name)
        acc_to_move = active_accs.pop(idx)
        active_accs.insert(new_index, acc_to_move)
        self._update_global_order_from_active(active_accs)

    def move_account(self, name, direction):
        active_accs = self.get_cycle_list()
        names = [a['name'] for a in active_accs]
        if name not in names: return
        idx = names.index(name)
        new_idx = idx + direction
        if 0 <= new_idx < len(names):
            active_accs[idx], active_accs[new_idx] = active_accs[new_idx], active_accs[idx]
            self._update_global_order_from_active(active_accs)

    def toggle_account(self, name, is_active):
        for acc in self.all_accounts:
            if acc['name'] == name: acc['active'] = is_active
        self.config.data["accounts_state"][name] = is_active
        self.config.save()

    def change_team(self, name, new_team):
        for acc in self.all_accounts:
            if acc['name'] == name: acc['team'] = new_team
        self.config.data["accounts_team"][name] = new_team
        self.config.save()

    def set_mode(self, mode):
        self.config.data["current_mode"] = mode
        self.config.save()

    def set_leader(self, name):
        self.leader_hwnd = None
        self.config.data["leader_name"] = name
        self.config.save()
        for acc in self.all_accounts:
            if acc['name'] == name: self.leader_hwnd = acc['hwnd']

    def close_account_window(self, name):
        for acc in self.all_accounts:
            if acc['name'] == name:
                hwnd = acc['hwnd']
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    ctypes.windll.kernel32.TerminateProcess(handle, 0)
                    ctypes.windll.kernel32.CloseHandle(handle)
                except Exception: pass
                break

    def close_all_active_accounts(self):
        active_accs = self.get_cycle_list()
        for acc in active_accs:
            hwnd = acc['hwnd']
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
            except: pass

    def focus_window(self, hwnd):
        if not hwnd: return
        try:
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            ctypes.windll.user32.AllowSetForegroundWindow(pid)
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            win32gui.SetForegroundWindow(hwnd)
        except: pass

    def sort_taskbar(self):
        active_accs = self.get_cycle_list()
        if not active_accs: return
        try:
            for acc in active_accs:
                win32gui.ShowWindow(acc['hwnd'], win32con.SW_HIDE)
            time.sleep(0.3)
            for acc in active_accs:
                win32gui.ShowWindow(acc['hwnd'], win32con.SW_SHOW)
                time.sleep(0.1) 
            if self.leader_hwnd:
                self.focus_window(self.leader_hwnd)
        except Exception: pass

    def execute_advanced_bind(self, source, identifier):
        """ Gère le focus dynamique et retourne le nouvel index pour la boucle. """
        active_list = self.get_cycle_list()
        if not active_list: return -1

        target_hwnd = None
        new_global_idx = -1

        if source == "cycle":
            row_index = int(identifier)
            if row_index < len(active_list):
                target_hwnd = active_list[row_index]['hwnd']
                new_global_idx = row_index

        elif source == "bind":
            target_pseudo = str(identifier)
            for index, acc in enumerate(active_list):
                if acc['name'] == target_pseudo:
                    target_hwnd = acc['hwnd']
                    new_global_idx = index
                    break
        
        if target_hwnd:
            self.focus_window(target_hwnd)
            return new_global_idx 
        return -1