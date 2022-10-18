from argparse import ArgumentParser

from linak_ble_controller.config import DEFAULT_CONFIG_PATH


class CustomArgumentParser(ArgumentParser):
    def __init__(self):
        super().__init__()

        self._init_arguments()

    def _init_arguments(self):
        self.add_argument(
            "--mac-address", dest="mac_address", type=str, help="Mac address of the Idasen desk"
        )
        self.add_argument(
            "--base-height",
            dest="base_height",
            type=int,
            help="The height of tabletop above ground at lowest position (mm)",
        )
        self.add_argument(
            "--movement-range",
            dest="movement_range",
            type=int,
            help="How far above base-height the desk can extend (mm)",
        )
        self.add_argument(
            "--adapter", dest="adapter_name", type=str, help="The bluetooth adapter device name"
        )
        self.add_argument(
            "--scan-timeout",
            dest="scan_timeout",
            type=int,
            help="The timeout for bluetooth scan (seconds)",
        )
        self.add_argument(
            "--connection-timeout",
            dest="connection_timeout",
            type=int,
            help="The timeout for bluetooth connection (seconds)",
        )
        self.add_argument(
            "--movement-timeout",
            dest="movement_timeout",
            type=int,
            help="The timeout for waiting for the desk to reach the specified height (seconds)",
        )
        self.add_argument(
            "--forward",
            dest="forward",
            action="store_true",
            help="Forward any commands to a server",
        )
        self.add_argument(
            "--server-address",
            dest="server_address",
            type=str,
            help="The address the server should run at",
        )
        self.add_argument(
            "--server_port",
            dest="server_port",
            type=int,
            help="The port the server should run on",
        )
        self.add_argument(
            "--config",
            dest="config",
            type=str,
            help="File path to the config file (Default: {})".format(DEFAULT_CONFIG_PATH),
            default=DEFAULT_CONFIG_PATH,
        )
        self.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            help="Print debug information"
        )

        cmd = self.add_mutually_exclusive_group()
        cmd.add_argument(
            "--watch",
            dest="watch",
            action="store_true",
            help="Watch for changes to desk height and speed and print them",
        )
        cmd.add_argument(
            "--move-to",
            dest="move_to",
            help="Move desk to specified height (mm) or to a favourite position",
        )
        cmd.add_argument(
            "--scan",
            dest="scan_adapter",
            action="store_true",
            help="Scan for devices using the configured adapter",
        )
        cmd.add_argument(
            "--server",
            dest="server",
            action="store_true",
            help="Run as a server to accept forwarded commands",
        )
        cmd.add_argument(
            "--tcp-server",
            dest="tcp_server",
            action="store_true",
            help="Run as a simple TCP server to accept forwarded commands",
        )

    def get_parsed_args(self):
        return {k: v for k, v in vars(self.parse_args()).items() if v is not None}


class UnitConverter:
    def __init__(self, base_height: int):
        self.base_height = base_height

    def mm_to_raw(self, mm):
        return (mm - self.base_height) * 10

    def raw_to_mm(self, raw):
        return (raw / 10) + self.base_height

    @staticmethod
    def raw_to_speed(raw):
        return raw / 100
