from __future__ import annotations
from enum import Enum, auto

from .nmcli import NmcliService
from .fuzzel import UI
from .model import NetworkState


class TopAction(Enum):
    TOGGLE_WIFI = auto()
    NETWORKS = auto()
    DISCONNECT = auto()
    ADVANCED = auto()


class WifiMenuApp:
    def __init__(self, nm: NmcliService, ui: UI) -> None:
        self._nm = nm
        self._ui = ui

    def _top_menu(self, state: NetworkState) -> list[tuple[TopAction, str]]:
        wifi_status = "on" if state.wifi_enabled else "off"
        return [
            (TopAction.TOGGLE_WIFI, f"Toggle WI-Fi (currently: {wifi_status})"),
            (TopAction.NETWORKS, "Available Networks..."),
            (TopAction.DISCONNECT, "Disconnect"),
            (TopAction.ADVANCED, "Advanced"),
        ]

    def _net_menu(self, state: NetworkState) -> tuple[list[str], list[str]]:
        labels: list[str] = []
        ssids: list[str] = []
        for network in state.networks:
            prefix = "* " if network.in_use else "  "
            label = network.ssid or "<hidden>"
            labels.append(f"{prefix}{label}   ({network.signal}%)")
            ssids.append(network.ssid)

        return labels, ssids

    def run(self) -> None:
        while True:
            state = self._nm.get_state()

            menu = self._top_menu(state)
            labels = [label for _, label in menu]
            picked = self._ui.choose(labels)
            if picked is None:
                return

            action = menu[picked.index][0]
            if action is TopAction.TOGGLE_WIFI:
                result = self._nm.toggle_wifi(not state.wifi_enabled)
                if not result.ok and result.message:
                    # TODO: find a way to send notif in this case
                    print("err:", result.message)
                return

            if action is TopAction.DISCONNECT:
                result = self._nm.disconnect_wifi()
                if not result.ok and result.message:
                    print("err:", result.message)
                return

            if action is TopAction.NETWORKS:
                net_labels, ssids = self._net_menu(state)
                net_pick = self._ui.choose(net_labels)
                if net_pick is None:
                    continue

                ssid = ssids[net_pick.index]
                net = next((n for n in state.networks if n.ssid == ssid))
                security = (net.security if net else "").strip()
                is_open = security == "" or security == "--"

                password = None
                if not is_open:
                    password = self._ui.prompt_password()
                    if not password:
                        continue

                result = self._nm.connect(
                    ssid, password=password, security_hint=security
                )
                if not result.ok and result.message:
                    print("err:", result.message)

            # TODO: implement advanced connectivity viewer
