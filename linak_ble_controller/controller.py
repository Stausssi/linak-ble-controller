import asyncio
import json
import traceback
from concurrent.futures import CancelledError
from functools import partial

import aiohttp
from aiohttp import web

from linak_ble_controller.bluetooth import BluetoothAdapter
from linak_ble_controller.config import UserConfig
from linak_ble_controller.helper import CustomArgumentParser, UnitConverter


class LinakController:
    def __init__(self):
        self.argument_parser = CustomArgumentParser()
        self.user_config = UserConfig(self.argument_parser.get_parsed_args())
        self.unit_converter = UnitConverter(self.user_config["base_height"])
        self.bluetooth_adapter = BluetoothAdapter(self.unit_converter, self.user_config)

        try:
            asyncio.run(self.run())
        except (KeyboardInterrupt | CancelledError):
            print("Interrupted...")

    async def run(self):
        try:
            # Forward and scan don't require a connection so run them and exit
            if self.user_config["forward"]:
                await self.forward_command()
            elif self.user_config["scan_adapter"]:
                await self.bluetooth_adapter.scan()
            else:
                # Server and other commands do require a connection so set one up
                client = await self.bluetooth_adapter.connect()
                if self.user_config["server"]:
                    await self.run_server()
                elif self.user_config.config["tcp_server"]:
                    await self.run_tcp_server(client, self.user_config)
                else:
                    await self.bluetooth_adapter.run_command()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\nSomething unexpected went wrong: {e}")
            print(traceback.format_exc())
        finally:
            if self.bluetooth_adapter.client:
                print("\rDisconnecting\r", end="")
                await self.bluetooth_adapter.stop()
                await self.bluetooth_adapter.disconnect()
                print("Disconnected!")

    async def run_tcp_server(self, client, config):
        """Start a simple tcp server to listen for commands"""

        def disconnect_callback(_=None):
            print("Lost connection with {}".format(self.bluetooth_adapter.client.address))
            asyncio.create_task(self.bluetooth_adapter.connect())

        self.bluetooth_adapter.client.set_disconnected_callback(disconnect_callback)
        server = await asyncio.start_server(
            partial(self.run_tcp_forwarded_command, client, config),
            self.user_config["server_address"],
            self.user_config["server_port"],
        )
        print("TCP Server listening")
        await server.serve_forever()

    async def run_tcp_forwarded_command(self, reader, writer):
        """Run commands received by the tcp server"""
        print("Received command")
        request = (await reader.read()).decode("utf8")
        forwarded_config = json.loads(str(request))
        merged_config = {**self.user_config.config, **forwarded_config}
        await self.bluetooth_adapter.run_command(merged_config)
        writer.close()

    async def run_server(self):
        """Start a server to listen for commands via websocket connection"""

        def disconnect_callback(_=None):
            print("Lost connection with {}".format(self.bluetooth_adapter.client.address))
            asyncio.create_task(self.bluetooth_adapter.connect())

        self.bluetooth_adapter.client.set_disconnected_callback(disconnect_callback)

        app = web.Application()
        app.router.add_get("/", partial(self.run_forwarded_command, self.bluetooth_adapter.client))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.user_config["server_address"], self.user_config["server_port"])
        await site.start()
        print("Server listening")
        while True:
            await asyncio.sleep(1000)

    async def run_forwarded_command(self, request):
        """Run commands received by the server"""
        print("Received command")
        ws = web.WebSocketResponse()

        def log(message, end="\n"):
            print(message, end=end)
            asyncio.create_task(ws.send_str(str(message)))

        await ws.prepare(request)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                forwarded_config = json.loads(msg.data)
                merged_config = {**self.user_config.config, **forwarded_config}
                await self.bluetooth_adapter.run_command(merged_config, log)
            break
        await asyncio.sleep(1)  # Allows final messages to send on web socket
        await ws.close()
        return ws

    async def forward_command(self):
        """Send commands to a server instance of this script"""
        allowed_keys = ["move_to"]
        forwarded_config = {key: self.user_config[key] for key in allowed_keys if key in self.user_config}
        session = aiohttp.ClientSession()
        ws = await session.ws_connect(
            f'http://{self.user_config["server_address"]}:{self.user_config["server_port"]}'
        )
        await ws.send_str(json.dumps(forwarded_config))
        while True:
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.text:
                print(msg.data)
            elif msg.type in [aiohttp.WSMsgType.closed, aiohttp.WSMsgType.error]:
                break
        await ws.close()
        await session.close()

