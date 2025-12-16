from .app import WifiMenuApp
from .nmcli import NmcliService
from .fuzzel import UI


def main() -> None:
    app = WifiMenuApp(NmcliService(), UI())
    app.run()


if __name__ == "__main__":
    main()
