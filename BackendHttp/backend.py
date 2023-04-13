import asyncio
import websockets
from aiohttp import web
from functools import partial
from datetime import datetime, timedelta
import logging
import ssl
import json
import os
from ocpp.v201 import datatypes, enums
from CSMS import ChargePoint, LoggerLogstash, TLSCheckCert, UserInfoProtocol
from centralsystem import CentralSystem


async def set_locallist(request):
    """HTTP handler for getting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    local_authorization_list = []
    local_authorization_list_dict = []
    for locallist_entry in data["locallist"]:
        local_authorization_list_dict.append(
            {
                "idToken": {
                    "idToken": locallist_entry["idToken"],
                    "type": locallist_entry["type"],
                },
                "idTokenInfo": {"status": locallist_entry["status"]},
            }
        )
        local_authorization_list.append(
            datatypes.AuthorizationData(
                id_token=datatypes.IdTokenType(
                    id_token=locallist_entry["idToken"], type=locallist_entry["type"]
                ),
                id_token_info=datatypes.IdTokenInfoType(
                    status=locallist_entry["status"]
                ),
            )
        )
    version_number = 1
    update_type = enums.UpdateType.differential
    result = await csms.send_sendlocallist(
        data["id"],
        version_number,
        update_type,
        local_authorization_list,
        local_authorization_list_dict,
    )

    return web.Response(text=json.dumps({"result": result}))


async def get_locallist(request):
    """HTTP handler for getting the ids of all charge points."""
    # data = await request.json()
    csms = request.app["csms"]
    data = await request.json()
    locallist = await csms.get_locallist(data["id"])

    return web.Response(text=json.dumps({"LocalList": locallist}))


async def get_variables(request):
    """HTTP handler for getting variables."""
    data = await request.json()
    csms = request.app["csms"]
    variable_data = datatypes.GetVariableDataType(
        component=datatypes.ComponentType(name="evse"),
        variable=datatypes.VariableType(name="all"),
    )
    result = await csms.get_variables(
        data["id"], data.get("variable_data", [variable_data])
    )

    return web.Response(text=json.dumps({"result": result}))


async def set_variables(request):
    """HTTP handler for setting variables."""
    data = await request.json()
    csms = request.app["csms"]
    # {"attributeValue":"","component":"",variable:""}
    payload = datatypes.SetVariableDataType(
        attribute_value=data.get("value"),
        component=datatypes.ComponentType(name=data.get("component")),
        variable=datatypes.VariableType(data.get("variable")),
    )
    await csms.set_variables(data["id"], [payload])

    return web.Response(text="OK")


async def update_firmware(request):
    """HTTP handler for updating the CP."""
    data = await request.json()
    csms = request.app["csms"]
    # {"attributeValue":"","component":"",variable:""}
    await csms.update_firmware(data["id"], data["firmwareURL"])
    return web.Response(text="OK")


async def set_display_message(request):
    """HTTP handler for getting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # id=data["id"], msg=data["msg"], msg_id=data["msgId"]
    message = datatypes.MessageInfoType(
        id=data["msgId"],
        priority=enums.MessagePriorityType.always_front,
        message=datatypes.MessageContentType(
            format=enums.MessageFormatType.utf8, content=data["msg"]
        ),
    )
    await csms.set_display_message(data["id"], message)
    return web.Response(text="OK")


async def get_display_message(request):
    """HTTP handler for getting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # id=data["id"], msg=data["msg"], msg_id=data["msgId"]
    await csms.get_display_message(data["id"])
    return web.Response(text="OK")


async def clear_display_message(request):
    """HTTP handler for deleting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # id=data["id"], msg=data["msg"], msg_id=data["msgId"]
    await csms.clear_display_message(data["id"], data["msgId"])
    return web.Response(text="OK")


async def start_transaction(request):
    """HTTP handler for deleting the ids of all charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # id=data["id"], msg=data["msg"], msg_id=data["msgId"]
    id_token = datatypes.IdTokenType(id_token=data["idToken"], type=data["idTokenType"])
    remote_start_id = 1
    await csms.start_transaction(
        data["id"], id_token=id_token, remote_start_id=remote_start_id
    )
    return web.Response(text="OK")


async def change_status(request):
    """HTTP handler for changing the status of the charge points."""
    data = await request.json()
    csms = request.app["csms"]
    # id=data["id"], msg=data["msg"], msg_id=data["msgId"]
    await csms.change_status(
        data["id"], data["operationalStatus"], int(data["connectorId"])
    )
    return web.Response(text="OK")


async def get_chargers(request):
    """HTTP handler for getting the ids of all charge points."""
    # data = await request.json()
    csms = request.app["csms"]

    chargers = await csms.get_connected_chargers()

    return web.Response(text=json.dumps(chargers))


async def home(request):
    """HTTP handler for changing configuration of all charge points."""
    # data = await request.json()
    csms = request.app["csms"]

    # await csms.change_configuration(data["key"], data["value"])

    return web.Response(text="OK")


async def reserve(request):
    """HTTP handler for reserving a charger."""
    data = await request.json()
    csms = request.app["csms"]
    expiry_date_time = data["expDate"]

    try:
        result = await csms.reserve_now(
            data["id"],
            datatypes.IdTokenType(
                id_token=data["idToken"], type=enums.IdTokenType.central
            ),
            expiry_date_time,
            data.get("connector", 1),
        )
    except ValueError as e:
        print(f"Failed to reserve charger: {e}")
        return web.Response(status=404)

    return web.Response(text=json.dumps({"result": result}))


async def cancel_reservation(request):
    """HTTP handler for canceling a reservation"""
    data = await request.json()
    csms = request.app["csms"]
    try:
        result = await csms.cancel_reserve(
            data["id"], connector=data.get("connector", 1)
        )
    except ValueError as e:
        print(f"Failed to cancel reservation reserve charger: {e}")
        return web.Response(status=404, text=f"{e}")

    return web.Response(text=json.dumps({"result": result}))


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
    app.add_routes([web.get("/", home)])
    app.add_routes([web.post("/reserve", reserve)])
    app.add_routes([web.post("/cancelReservation", cancel_reservation)])
    app.add_routes([web.get("/chargers", get_chargers)])
    app.add_routes([web.post("/variables", set_variables)])
    app.add_routes([web.get("/variables", get_variables)])
    app.add_routes([web.post("/displayMessage", set_display_message)])
    app.add_routes([web.get("/displayMessage", get_display_message)])
    app.add_routes([web.delete("/displayMessage", clear_display_message)])
    app.add_routes([web.get("/locallist", get_locallist)])
    app.add_routes([web.post("/locallist", set_locallist)])
    app.add_routes([web.post("/update", update_firmware)])
    app.add_routes([web.post("/status", change_status)])
    app.add_routes([web.post("/startTransaction", start_transaction)])

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
        config = config["CSMS"]

    websocket_server = await create_websocket_server(csms, config)
    http_server = await create_http_server(csms)
    websocket_task = asyncio.create_task(websocket_server.wait_closed())
    http_task = asyncio.create_task(http_server.start())
    await asyncio.wait([websocket_task, http_task])


if __name__ == "__main__":
    asyncio.run(main())
