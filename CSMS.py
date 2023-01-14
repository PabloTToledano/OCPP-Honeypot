import asyncio
import logging
import random
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This honeypot on the 'websockets' and ocpp package.")
    print("Please install it by running: ")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call_result, call

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    @on("BootNotification")
    def on_boot_notification(self, charging_station, reason, **kwargs):
        print(charging_station)
        print(reason)
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(), interval=600, status="Accepted"
        )

    @on("Authorize")
    def on_authorize(
        self,
        id_token: dict,
        certificate: str | None = None,
        iso15118_certificate_hash_data: list | None = None,
        **kwargs,
    ):
        # Must accept everything so that the attacker believes he/she has access
        return call_result.AuthorizePayload(
            id_token_info={
                "status": "Accepted",
                "personalMessage": "0.69$/kWh",
            },
        )

    @on("Heartbeat")
    def on_heartbeat(self, **kwargs):
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )

    @on("StatusNotification")
    def on_status_notification(
        self,
        timestamp: str,
        connector_status: str,
        evse_id: int,
        connector_id: int,
        **kwargs,
    ):
        #  A connector status changed, the Charging Station sends a StatusNotificationRequest to the CSMS to inform the CSMS about the new status.
        return call_result.StatusNotificationPayload()

    @on("NotifyDisplayMessages")
    def on_notify_display_messages(self, **kwargs):
        return call_result.NotifyDisplayMessagesPayload()

    @on("LogStatusNotification")
    def on_log_status_notification(
        self,
        request_id: int,
        message_info: list | None = None,
        tbc: bool | None = None,
        **kwargs,
    ):
        return call_result.LogStatusNotificationPayload()

    @on("NotifyEvent")
    def on_notify_event(
        self,
        generated_at: str,
        seq_no: int,
        event_data: list,
        tbc: bool | None = None,
        **kwargs,
    ):
        # el atacante puede hacer creer que una charging station tiene muchos errores,etc.
        # un error es G05 - Lock Failure
        return call_result.NotifyEventPayload()

    @on("NotifyCustomerInformation")
    def on_notify_customer_information(
        self,
        data: str,
        seq_no: int,
        generated_at: str,
        request_id: int,
        tbc: bool | None = None,
        **kwargs,
    ):
        return call_result.NotifyCustomerInformationPayload()

    @on("MeterValues")
    def on_meter_values(self, evse_id: int, meter_value: list, **kwargs):
        return call_result.MeterValuesPayload()

    async def send_data_transfer(self):
        request = call.DataTransferPayload(
            vendor_id="",
            message_id="",
        )
        response = await self.call(request)

    async def send_set_variables(self, variable_data: list):
        # variable_data must be a list of dict. The dict must comply with SetVariableDataType
        # attributeValue, component, variable

        request = call.SetVariablesPayload(set_variable_data=variable_data)
        response = await self.call(request)

    async def send_get_variables(self, variable_data: list):
        # variable_data must be a list of dict. The dict must comply with GetVariableDataType
        # component, variable

        request = call.GetVariablesPayload(get_variable_data=variable_data)
        response = await self.call(request)

    async def send_set_network_profile(
        self, configuration_slot: int, connection_data: dict
    ):

        request = call.SetNetworkProfilePayload(
            configuration_slot=configuration_slot, connection_data=connection_data
        )
        response = await self.call(request)

    async def send_request_reset(self, type: str, evse_id: int | None = None):

        request = call.ResetPayload(type=type, evse_id=evse_id)
        response = await self.call(request)

    async def send_sendlocallist(
        self,
        version_number: int,
        update_type: str,
        local_authorization_list: list | None = None,
    ):

        request = call.SendLocalListPayload(
            version_number=version_number,
            update_type=update_type,
            local_authorization_list=local_authorization_list,
        )
        response = await self.call(request)

    async def send_get_localist(
        self,
    ):

        request = call.GetLocalListVersionPayload()
        response = await self.call(request)

    async def send_set_display_messages(self, priority, message):
        request = call.SetDisplayMessagePayload(
            message={
                "id": random.randint(0, 9999),
                "priority": priority,
                "message": message,
            },
        )
        response = await self.call(request)


async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.info("Client hasn't requested any Subprotocol. " "Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    charge_point = ChargePoint(charge_point_id, websocket)

    await charge_point.start()


async def main():
    server = await websockets.serve(
        on_connect, "0.0.0.0", 9000, subprotocols=["ocpp2.0.1"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
