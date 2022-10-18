import asyncio
import struct
from enum import Enum
from functools import partial
from typing import Optional

from bleak import BleakError, BleakScanner, BleakClient

from linak_ble_controller.config import UserConfig
from linak_ble_controller.helper import UnitConverter


class GattCharacteristics(str, Enum):
    UUID_HEIGHT = "99fa0021-338a-1024-8a49-009c0215f78a"
    UUID_COMMAND = "99fa0002-338a-1024-8a49-009c0215f78a"
    UUID_REFERENCE_INPUT = "99fa0031-338a-1024-8a49-009c0215f78a"


class BluetoothAdapter:
    def __init__(self, unit_converter: UnitConverter, config: UserConfig):
        self.unit_converter = unit_converter
        self.config = config

        self.stop_command = bytearray(struct.pack("<H", 255))
        self.wake_command = bytearray(struct.pack("<H", 254))

        self.client: Optional[BleakClient] = None

    async def get_height_speed(self):
        return struct.unpack("<Hh", await self.client.read_gatt_char(GattCharacteristics.UUID_HEIGHT))

    def get_height_data_from_notification(self, data):
        height, speed = struct.unpack("<Hh", data)
        print(
            "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(
                self.unit_converter.raw_to_mm(height), self.unit_converter.raw_to_speed(speed)
            )
        )

    async def wake_up(self):
        await self.client.write_gatt_char(GattCharacteristics.UUID_COMMAND, self.wake_command)

    async def move_to_target(self, target):
        encoded_target = bytearray(struct.pack("<H", int(target)))
        await self.client.write_gatt_char(GattCharacteristics.UUID_REFERENCE_INPUT, encoded_target)

    async def stop(self):
        try:
            await self.client.write_gatt_char(GattCharacteristics.UUID_COMMAND, self.stop_command)
        except BleakError:
            # This seems to result in an error on Raspberry Pis, but it does not affect movement
            # bleak.exc.BleakDBusError: [org.bluez.Error.NotPermitted] Write acquired
            pass

    async def subscribe(self, uuid, callback):
        """Listen for notifications on a characteristic"""
        await self.client.start_notify(uuid, callback)

    async def unsubscribe(self, uuid):
        """Stop listening for notifications on a characteristic"""
        try:
            await self.client.stop_notify(uuid)
        except KeyError:
            # This happens on Windows, I don't know why
            pass

    async def scan(self):
        """
        Scan for a bluetooth device with the configured address and return it or return all devices if no address
        specified
        """

        print("Scanning\r", end="")
        devices = await BleakScanner().discover(
            device=self.config["adapter_name"], timeout=self.config["scan_timeout"]
        )
        print("Found {} devices using {}".format(len(devices), self.config["adapter_name"]))
        for device in devices:
            print(device)

        return devices

    async def move_to(self, target, log=print):
        """
        Move the desk to a specified height
        """

        initial_height, speed = struct.unpack(
            "<Hh", await self.client.read_gatt_char(GattCharacteristics.UUID_HEIGHT)
        )

        if initial_height == target:
            return

        await self.wake_up()
        await self.stop()

        current_height = initial_height

        while current_height < target:
            await self.move_to_target(target)
            await asyncio.sleep(0.5)
            height, speed = await self.get_height_speed()
            log(
                "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(
                    self.unit_converter.raw_to_mm(height), self.unit_converter.raw_to_speed(speed)
                )
            )

            # if speed == 0:
            #     break

    async def connect(self):
        """Attempt to connect to the desk"""
        try:
            print("Connecting\r", end="")
            if not self.client:
                self.client = BleakClient(self.config["mac_address"], device=self.config["adapter_name"])
            await self.client.connect(timeout=self.config["connection_timeout"])
            print("Connected {}".format(self.config["mac_address"]))

            services = await self.client.get_services()
            print("Received the services:")
            for s in services.services.values():
                print(f"{s.uuid}:")
                for c in s.characteristics:
                    print(f"  - {c.uuid}:{c.description}")

            return self.client
        except BleakError as e:
            print("Connecting failed")
            print(e)
            exit(1)

    async def disconnect(self):
        """Attempt to disconnect cleanly"""
        if self.client.is_connected:
            await self.client.disconnect()

    async def run_command(self, config, log=print):
        """Begin the action specified by command line arguments and config"""
        # Always print current height
        initial_height, speed = struct.unpack(
            "<Hh", await self.client.read_gatt_char(GattCharacteristics.UUID_HEIGHT)
        )
        log("Height: {:4.0f}mm".format(self.unit_converter.raw_to_mm(initial_height)))
        target = None
        if config.get("watch"):
            # Print changes to height data
            log("Watching for changes to desk height and speed")
            await self.subscribe(
                GattCharacteristics.UUID_HEIGHT, partial(self.get_height_data_from_notification)
            )
            wait = asyncio.get_event_loop().create_future()
            await wait
        elif config.get("move_to"):
            # Move to custom height
            favourite_value = config.get("favourites", {}).get(config["move_to"])
            if favourite_value:
                target = self.unit_converter.mm_to_raw(favourite_value)
                log(f'Moving to favourite height: {config["move_to"]}')
            else:
                try:
                    target = self.unit_converter.mm_to_raw(int(config["move_to"]))
                    log(f'Moving to height: {config["move_to"]}')
                except ValueError:
                    log(f'Not a valid height or favourite position: {config["move_to"]}')
                    return
            await self.move_to(target, log=log)
        if target:
            final_height, speed = struct.unpack(
                "<Hh", await self.client.read_gatt_char(GattCharacteristics.UUID_HEIGHT)
            )
            # If we were moving to a target height, wait, then print the actual final height
            log(
                "Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(
                    self.unit_converter.raw_to_mm(final_height), self.unit_converter.raw_to_mm(target)
                )
            )
