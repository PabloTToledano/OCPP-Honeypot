import asyncio
import websockets
from aiohttp import web
from functools import partial
from datetime import datetime
import logging
import ssl
import json
import os
from ocpp.v201 import datatypes
from CSMS import ChargePoint, LoggerLogstash, TLSCheckCert, UserInfoProtocol


class CentralSystem:
    def __init__(self):
        self._chargers = {}

    def register_charger(self, cp: ChargePoint) -> asyncio.Queue:
        """Register a new ChargePoint at the CSMS. The function returns a
        queue.  The CSMS will put a message on the queue if the CSMS wants to
        close the connection.
        """
        queue = asyncio.Queue(maxsize=1)

        # Store a reference to the task so we can cancel it later if needed.
        task = asyncio.create_task(self.start_charger(cp, queue))
        self._chargers[cp] = task

        return queue

    async def start_charger(self, cp, queue):
        """Start listening for message of charger."""
        try:
            await cp.start()
        except Exception as e:
            print(f"Charger {cp.id} disconnected: {e}")
        finally:
            # Make sure to remove referenc to charger after it disconnected.
            del self._chargers[cp]

            # This will unblock the `on_connect()` handler and the connection
            # will be destroyed.
            await queue.put(True)

    # async def change_configuration(self, key: str, value: str):
    #     for cp in self._chargers:
    #         await cp.change_configuration(key, value)

    async def change_variables(self, id: str,variable_data: list ):
        for cp in self._chargers:
            if cp.id == id:
                await cp.send_set_variables(variable_data)


    async def get_variables(self, id: str,get_variable_data: list ):
        for cp in self._chargers:
            if cp.id == id:
                result = await cp.send_get_variables(get_variable_data)
                return result.get_variable_result

    async def get_connected_chargers(self):
        ids = []
        for cp in self._chargers:
            ids.append(cp.id)
        return ids

    def disconnect_charger(self, id: str):
        for cp, task in self._chargers.items():
            if cp.id == id:
                task.cancel()
                return

        raise ValueError(f"Charger {id} not connected.")


async def get_variables(request):
    """HTTP handler for getting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    variable_data = datatypes.GetVariableDataType(component=datatypes.ComponentType(name="evse"),variable=datatypes.VariableType(name="all"))
    result = await csms.get_variables(data["id"], data.get("variable_data",[variable_data]))

    return web.Response(text=json.dumps({"result":result}))

async def set_variables(request):
    """HTTP handler for getting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # {"attributeValue":"","component":"",variable:""}
    await csms.set_variables(data["id"], data.get("variable_data",[]))

    return web.Response(text="OK")

async def get_chargers(request):
    """HTTP handler for getting the ids of all charge points."""
    # data = await request.json()
    csms = request.app["csms"]

    ids = await csms.get_connected_chargers()

    return web.Response(text=json.dumps({"ids":ids}))


async def change_config(request):
    """HTTP handler for changing configuration of all charge points."""
    # data = await request.json()
    csms = request.app["csms"]

    # await csms.change_configuration(data["key"], data["value"])

    return web.Response(text="TEST")


async def disconnect_charger(request):
    """HTTP handler for disconnecting a charger."""
    data = await request.json()
    csms = request.app["csms"]

    try:
        csms.disconnect_charger(data["id"])
    except ValueError as e:
        print(f"Failed to disconnect charger: {e}")
        return web.Response(status=404)

    return web.Response()


async def on_connect(websocket, path, csms):
    """For every new charge point that connects, create a ChargePoint instance
    and start listening for messages.

    The ChargePoint is registered at the CSMS.

    """
    charge_point_id = path.strip("/")
    cp = ChargePoint(charge_point_id, websocket)

    print(f"Charger {cp.id} connected.")

    # If this handler returns the connection will be destroyed. Therefore we need some
    # synchronization mechanism that blocks until CSMS wants to close the connection.
    # An `asyncio.Queue` is used for that.
    queue = csms.register_charger(cp)
    await queue.get()


async def create_websocket_server(csms: CentralSystem, config: dict):

    address = config.get("IP", "0.0.0.0")
    port = config.get("port", "9000")
    security_profile = config.get("security_profile", 1)
    logstash_host = config.get("logstasth").get("ip")
    logstash_port = config.get("logstasth").get("port")

    # Add security profiles
    handler = partial(on_connect, csms=csms)
    logging.info(f"Security profile {security_profile}")

    if logstash_host is not None:
        instance = LoggerLogstash(
            logstash_port=logstash_port, logstash_host=logstash_host, logger_name="ocpp"
        )
        logger = instance.get()

    match security_profile:
        case 1:
            return await websockets.serve(
                handler,
                address,
                port,
                subprotocols=["ocpp2.0.1"],
                create_protocol=UserInfoProtocol,
            )
        case 2:
            if not os.path.isfile(config.get("ssl_key")) or not os.path.isfile(
                config.get("ssl_pem")
            ):
                logging.error("SSL certificated not found")
                exit(-1)
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(config.get("ssl_pem"), config.get("ssl_key"))
            return await websockets.serve(
                handler,
                address,
                port,
                subprotocols=["ocpp2.0.1"],
                ssl=ssl_context,
                create_protocol=UserInfoProtocol,
            )
        case 3:
            if not os.path.isfile(config.get("ssl_key")) or not os.path.isfile(
                config.get("ssl_pem")
            ):
                logging.error("SSL certificated not found")
                exit(-1)
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(config.get("ssl_pem"), config.get("ssl_key"))
            return await websockets.serve(
                handler,
                address,
                port,
                subprotocols=["ocpp2.0.1"],
                ssl=ssl_context,
                create_protocol=TLSCheckCert,
            )

    logging.info("Server Started listening to new connections...")


async def create_http_server(csms: CentralSystem):
    app = web.Application()
    app.add_routes([web.get("/", change_config)])
    app.add_routes([web.post("/disconnect", disconnect_charger)])
    app.add_routes([web.get("/ids", get_chargers)])
    app.add_routes([web.post("/variables", set_variables)])
    app.add_routes([web.get("/variables", get_variables)])

    # Put CSMS in app so it can be accessed from request handlers.
    # https://docs.aiohttp.org/en/stable/faq.html#where-do-i-put-my-database-connection-so-handlers-can-access-it
    app["csms"] = csms

    # https://docs.aiohttp.org/en/stable/web_advanced.html#application-runners
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    return site


async def main():
    csms = CentralSystem()
    with open("./config.json") as file:
        config = json.load(file)

    websocket_server = await create_websocket_server(csms, config)
    http_server = await create_http_server(csms)
    websocket_task = asyncio.create_task(websocket_server.wait_closed())
    http_task = asyncio.create_task(http_server.start())
    await asyncio.wait([websocket_task, http_task])


if __name__ == "__main__":
    asyncio.run(main())
