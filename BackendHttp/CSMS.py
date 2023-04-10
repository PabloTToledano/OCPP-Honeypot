import asyncio
import http
import logging
import random
import argparse
import ssl
import os
import io
import vt
import json
import pathlib
import logstash
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This honeypot uses the 'websockets' and ocpp package.")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call_result, call


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("ocpp")


class LoggerLogstash(object):
    def __init__(
        self,
        logger_name: str = "logstash",
        logstash_host: str = "localhost",
        logstash_port: int = 6969,
    ):
        self.logger_name = logger_name
        self.logstash_host = logstash_host
        self.logstash_port = logstash_port

    def get(self):
        logging.basicConfig(
            filename="logfile",
            filemode="a",
            format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
            level=logging.INFO,
        )

        self.stderrLogger = logging.StreamHandler()
        logging.getLogger().addHandler(self.stderrLogger)
        self.logger = logging.getLogger(self.logger_name)
        self.logger.addHandler(
            logstash.LogstashHandler(self.logstash_host, self.logstash_port, version=1)
        )
        return self.logger


class ChargePoint(cp):
    def __init__(self, id, connection):
        cp.__init__(self, id, connection)
        self.charger_station = None
        self.connectors = {}
        self.display_message = []
        self.local_list = []
        self.update_status = ""
        self.vt_client = None
        # Only create virus total client if token is found
        try:
            with open("/config.json") as file:
                config = json.load(file)
            if config.get("VT_API_KEY", "") != "":
                self.vt_client = vt.Client(config.get("VT_API_KEY"))
        except:
            pass

    @on("BootNotification")
    def on_boot_notification(self, charging_station, reason, **kwargs):
        logging.info(charging_station)
        self.charger_station = charging_station
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=1000,
            status="Accepted",
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
                "personalMessage": {"format": "UTF8", "content": "0.69$/kWh"},
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
        self.connectors[str(connector_id)] = connector_status
        return call_result.StatusNotificationPayload()

    @on("NotifyDisplayMessages")
    def on_notify_display_messages(
        self,
        request_id: int,
        message_info: list | None = None,
        tbc: bool | None = None,
        **kwargs,
    ):
        self.display_message = message_info
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

    @on("NotifyChargingLimit")
    def on_notify_charging_limit(
        self,
        charging_limit: dict,
        charging_schedule: list | None = None,
        evse_id: int | None = None,
        **kwargs,
    ):
        return call_result.NotifyChargingLimitPayload()

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

    @on("NotifyEVChargingSchedule")
    def on_notify_ev_charging_schedule(
        self,
        time_base: str,
        charging_schedule: dict,
        evse_id: int,
        **kwargs,
    ):
        return call_result.NotifyEVChargingSchedulePayload(status="Accepted")

    @on("MeterValues")
    def on_meter_values(self, evse_id: int, meter_value: list, **kwargs):
        return call_result.MeterValuesPayload()

    @on("DataTransfer")
    def on_data_transfer(
        self,
        vendor_id: str,
        message_id: str | None = None,
        data: str | None = None,
        **kwargs,
    ):
        # scand data with virustotal
        call.DataTransferPayload()
        if self.vt_client:
            try:
                data = io.StringIO(data)
                analysis = self.vt_client.scan_file(data, wait_for_completion=True)
                LOGGER.info(f"VirusTotal analysis: {analysis.stats}")
            except Exception as e:
                # usually due to invalid virustotal api key
                pass

        return call_result.DataTransferPayload(status="Accepted", data={})

    @on("FirmwareStatusNotification")
    def on_firmware_status_notification(
        self, status: str, request_id: int | None = None, **kwargs
    ):
        return call_result.FirmwareStatusNotificationPayload()

    @on("PublishFirmwareStatusNotification")
    def on_publish_firmware_notification(
        self,
        location: str,
        checksum: str,
        request_id: int,
        retries: int | None = None,
        retry_interval: int | None = None,
        **kwargs,
    ):
        return call_result.PublishFirmwareStatusNotificationPayload()

    @on("MeterValues")
    def on_meter_values(self, evse_id: int, meter_value: list, **kwargs):
        return call_result.MeterValuesPayload()

    @on("ClearedChargingLimit")
    def on_cleared_charging_limit(
        self, charging_limit_source: str, evse_id: int | None = None, **kwargs
    ):
        return call_result.ClearedChargingLimitPayload()

    @on("TransactionEvent")
    def on_transaction_event(
        self,
        event_type: str,
        timestamp: str,
        trigger_reason: str,
        seq_no: int,
        transaction_info: dict,
        meter_value: list | None = None,
        offline: bool | None = None,
        number_of_phases_used: int | None = None,
        cable_max_current: int | None = None,
        reservation_id: int | None = None,
        evse: dict | None = None,
        id_token: dict | None = None,
        **kwargs,
    ):
        # total_cost: int | None = None, charging_priority: int | None = None,
        # id_token_info: Dict | None = None, updated_personal_message: Dict | None = None

        return call_result.TransactionEventPayload()

    @on("SecurityEventNotification")
    def on_security_event_notification(
        self, type: str, timestamp: str, tech_info: str | None = None, **kwargs
    ):
        return call_result.SecurityEventNotificationPayload()

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
        return await self.call(request)

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

    async def send_reserve_now(
        self,
        id: int,
        expiry_date_time: str,
        id_token: dict,
        connector_type: str | None = None,
        evse_id: int | None = None,
        group_id_token: dict | None = None,
    ):
        request = call.ReserveNowPayload(
            id=id, expiry_date_time=expiry_date_time, id_token=id_token
        )
        return await self.call(request)

    async def send_reserve_cancel(self, reservation_id: int):
        request = call.CancelReservationPayload(reservation_id=reservation_id)
        return await self.call(request)

    async def send_sendlocallist(
        self,
        version_number: int,
        update_type: str,
        local_authorization_list: list | None = None,
        local_authorization_list_dict: list | None = None,
    ):
        request = call.SendLocalListPayload(
            version_number=version_number,
            update_type=update_type,
            local_authorization_list=local_authorization_list,
        )
        self.local_list = local_authorization_list_dict

        return await self.call(request)

    async def send_get_localist(
        self,
    ):
        request = call.GetLocalListVersionPayload()
        return await self.call(request)

    async def send_set_display_messages(self, message):
        request = call.SetDisplayMessagePayload(message=message)
        return await self.call(request)

    async def send_get_display_messages(
        self, request_id, id=None, priority=None, state=None
    ):
        request = call.GetDisplayMessagesPayload(
            request_id, id=id, priority=priority, state=state
        )
        return await self.call(request)

    async def send_clear_display_messages(self, id):
        request = call.ClearDisplayMessagePayload(id)
        return await self.call(request)

    async def send_update_firmware(
        self,
        request_id: int,
        firmware,
        retries: int | None = None,
        retry_interval: int | None = None,
    ):
        request = call.UpdateFirmwarePayload(request_id, firmware=firmware)
        return await self.call(request)


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


class UserInfoProtocol(websockets.BasicAuthWebSocketServerProtocol):
    async def check_credentials(self, username, password):
        # For security profile 1/2
        logging.info(username)
        logging.info(password)
        return True


class TLSCheckCert(websockets.WebSocketServerProtocol):
    async def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """
        Register connection and initialize a task to handle it.
        """
        transport.get_extra_info(...)
        sslsock = transport.get_extra_info("ssl_object")
        cert = sslsock.getpeercert()
        # do whatever with the certificate

        super().super().connection_made(transport)
        # Register the connection with the server before creating the handler
        # task. Registering at the beginning of the handler coroutine would
        # create a race condition between the creation of the task, which
        # schedules its execution, and the moment the handler starts running.
        super().ws_server.register(self)
        super().handler_task = super().loop.create_task(super().handler())


async def main(
    address: str,
    port: int,
    security_profile: int,
    logstash_host: str | None,
    logstash_port: int | None,
):
    logging.info(f"Security profile {security_profile}")

    if logstash_host is not None:
        instance = LoggerLogstash(
            logstash_port=logstash_port, logstash_host=logstash_host, logger_name="ocpp"
        )
        logger = instance.get()

    match security_profile:
        case 1:
            server = await websockets.serve(
                on_connect,
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
            server = await websockets.serve(
                on_connect,
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
            server = await websockets.serve(
                on_connect,
                address,
                port,
                subprotocols=["ocpp2.0.1"],
                ssl=ssl_context,
                create_protocol=TLSCheckCert,
            )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # load config json
    with open("/config.json") as file:
        config = json.load(file)

    logging.info("[CSMS]Using config:")
    logging.info(config)

    asyncio.run(
        main(
            config.get("IP", "0.0.0.0"),
            config.get("port", "9000"),
            config.get("security_profile", 1),
            config.get("logstasth").get("ip"),
            config.get("logstasth").get("port"),
        )
    )
