import os
import shutil
import sys
from typing import Dict, Union

import yaml
from appdirs import user_config_dir

DEFAULT_CONFIG_DIR = user_config_dir("linak-controller")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.yaml")

DEFAULT_CONFIG = {
    "mac_address": "",
    "base_height": 620,
    "movement_range": 650,
    "adapter_name": "hci0",
    "scan_timeout": 5,
    "connection_timeout": 10,
    "movement_timeout": 30,
    "server_address": "127.0.0.1",
    "server_port": 9123,
    "favourites": {},
}


class UserConfig:
    def __init__(self, args: Dict[str, Union[str, dict, int, None]]):
        self._copy_default_config()

        self.config = DEFAULT_CONFIG

        config_path = os.path.join(args["config"])
        if config_path and os.path.isfile(config_path):
            self._read_custom_file(config_path)
        else:
            print("No custom config file provided or not found!")

        self.config.update(args)

    @staticmethod
    def _copy_default_config():
        if not os.path.isfile(DEFAULT_CONFIG_PATH):
            os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
            shutil.copyfile(
                os.path.join(os.path.dirname(__file__), "example", "config.yaml"),
                DEFAULT_CONFIG_PATH,
            )

    def _read_custom_file(self, path):
        with open(path, "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print("Reading config.yaml failed:")
                print(e)
                exit(1)

        self.config.update(config_file)

    def _validate_config(self):
        if not self.config["mac_address"]:
            self._log_error("Mac address must be provided")

        if "sit_height_offset" in self.config:
            if not (0 <= self.config["sit_height_offset"] <= self.config["movement_range"]):
                self._log_error(
                    "Sit height offset must be within [0, {}]".format(self.config["movement_range"])
                )
            self.config["sit_height"] = self.config["base_height"] + self.config["sit_height_offset"]

        if "stand_height_offset" in self.config:
            if not (0 <= self.config["stand_height_offset"] <= self.config["movement_range"]):
                self._log_error(
                    "Stand height offset must be within [0, {}]".format(
                        self.config["movement_range"]
                    )
                )
            self.config["stand_height"] = self.config["base_height"] + self.config["stand_height_offset"]

        self.config["mac_address"] = self.config["mac_address"].upper()

        if sys.platform == "win32":
            # Windows doesn't use this parameter so rename it, so it looks nice for the logs
            self.config["adapter_name"] = "default adapter"

    @staticmethod
    def _log_error(message):
        print(message)
        exit(1)

    def __getitem__(self, item) -> Union[int, str, dict, None]:
        return self.config[item]

    def __contains__(self, item):
        return self.config.__contains__(item)
