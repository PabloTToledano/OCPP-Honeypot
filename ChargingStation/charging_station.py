import asyncio
import logging
import random
import vt
import os
import io
import json
import websockets
import ssl
from datetime import datetime

from ocpp.routing import on, after
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result

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
            logstash.LogstashHandler(
                self.log_stash_host, self.log_stash_upd_port, version=1
            )
        )
        return self.logger

class ChargePoint(cp):
    def __init__(self, id, connection, response_timeout, config):
        cp.__init__(self, id, connection, response_timeout)
        self.availability: str = "Operative"
        self.model = config.get("model", "UMA")
        self.vendor = config.get("vendor_name", "Andalucia")
        self.connectors, self.reserved, self.reserved_exp = self.generate_connectors(
            config
        )
        self.occp_variables = config.get("OCPP_variables", {})
        self.vt_client = None
        # Only create virus total client if token is found
        if config.get("VT_API_KEY", "") != "":
            vt_client = vt.Client(config.get("VT_API_KEY"))

    def generate_connectors(self, config):
        n_connectors = config.get("connectors", 1)
        connectors = []
        reserved = []
        reserved_exp = []
        for i in range(n_connectors):
            connectors.append("Operative")
            reserved.append(False)
            reserved_exp.append(datetime.now())
        return connectors, reserved, reserved_exp

    async def send_heartbeat(self, interval):
        request = call.HeartbeatPayload()
        while True:
            await self.call(request)
            await asyncio.sleep(interval)

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charging_station={
                "model": self.model,
                "vendor_name": self.vendor,
            },
            reason="PowerUp",
        )
        try:
            response = await self.call(request)
            if response.status == "Accepted":
                print("Connected to central system.")
                await self.send_heartbeat(response.interval)
        except Exception as e:
            logging.error(e)

    async def send_authorize(
        self,
        id_token: dict,
        certificate: str | None = None,
        iso15118_certificate_hash_data: list | None = None,
    ):
        # id_token must be of type IdTokenType
        # Simple example
        id_token = {
            "idToken": random.randint(100, 99999),
            "type": "Local",
        }
        request = call.AuthorizePayload(id_token=id_token)
        response = await self.call(request)

    async def send_datatransfer(self):
        request = call.DataTransferPayload(
            vendor_id="",
            message_id="",
        )
        response = await self.call(request)

    @on("SetVariables")
    def on_setvariables(self, set_variable_data, **kwargs):
        # set_variable_data list of dict with contents of SetVariableDataType
        # for every variable respond with a dict of  SetVariableResultType

        # attributeStatus: Accepted, Rejected, UnknownVariable, RebootRequired
        variable_result = []
        for variable in set_variable_data:
            # Do something with variable.get("attributeValue")

            if self.occp_variables.get(variable.get("variable"), None):
                self.occp_variables[variable.get("variable")] = variable.get(
                    "attributeValue", ""
                )

            match variable.get("variable"):
                # A05 - Upgrade Charging Station Security Profile
                case "NetworkConfigurationPriority":
                    variable_result.append(
                        {
                            "attributeType": variable.get("attributeType", "Actual"),
                            "attributeStatus": "Accepted",
                            "component": variable.get("component"),
                            "variable": variable.get("variable"),
                        }
                    )
                case default:
                    variable_result.append(
                        {
                            "attributeType": variable.get("attributeType", "Actual"),
                            "attributeStatus": "Accepted",
                            "component": variable.get("component"),
                            "variable": variable.get("variable"),
                        }
                    )
        return call_result.SetVariablesPayload(set_variable_result=variable_result)

    @on("GetVariables")
    def on_getvariables(self, get_variable_data, **kwargs):
        # get_variable_data list of dict with contents of GetVariableDataType
        # for every variable respond with a dict of  SetVariableResultType

        # attributeStatus: Accepted, Rejected, UnknownVariable, RebootRequired
        # if status rejected then attibuteValue empty
        variable_result = []
        for variable in get_variable_data:
            variable_result.append(
                {
                    "attributeType": variable.get("attributeType", "Actual"),
                    "attributeStatus": "Accepted",
                    "component": variable.get("component"),
                    "variable": variable.get("variable"),
                    "attributeValue ": self.occp_variables.get(
                        variable.get("variable"), ""
                    ),
                }
            )
        return call_result.GetVariablesPayload(get_variable_result=variable_result)

    @on("DataTransfer")
    def on_data_transfer(
        self,
        vendor_id: str,
        message_id: str | None = None,
        data: str | None = None,
        **kwargs,
    ):
        # scand data with virustotal
        if self.vt_client:
            try:
                data = io.StringIO(data)
                analysis = self.client.scan_file(data, wait_for_completion=True)
                LOGGER.info(f"VirusTotal analysis: {analysis.stats}")
            except Exception as e:
                # usually due to invalid virustotal api key
                pass

        return call_result.DataTransferPayload(status="", data={})

    @on("SetNetworkProfile")
    def on_set_network_profile(
        self, configuration_slot: int, connection_data: dict, **kwargs
    ):
        # here the usual thing would be to either reject or fail and log everything
        statuses = ["Rejected", "Failed"]
        status = random.choice(statuses)
        return call_result.SetNetworkProfilePayload(status=status)

    @on("Reset")
    def on_reset(self, type: str, evse_id: int | None = None, **kwargs):
        # just send either Scheduled or Rejected
        statuses = ["Rejected", "Scheduled"]
        status = random.choice(statuses)
        return call_result.ResetPayload(status=status)

    @on("SendLocalList")
    def on_send_locallist(
        self,
        version_number: int,
        update_type: str,
        local_authorization_list: list | None = None,
        **kwargs,
    ):
        # TODO check versionNumber againt old versionNumber
        # save new localList
        return call_result.SendLocalListPayload(status="Accepted")

    @on("GetLocalListVersion")
    def on_get_locallist_version(self, **kwargs):
        return call_result.GetLocalListVersionPayload(version_number=2)

    # O.DisplayMessage
    @on("SetDisplayMessages")
    def on_set_display_messages(self, message: dict, **kwargs):
        # TODO save the message
        # this is for set and replace
        return call_result.SetDisplayMessagePayload(status="Accepted")

    @on("GetDisplayMessages")
    def on_get_display_messages(
        self,
        request_id: int,
        id: list | None = None,
        priority: str | None = None,
        state: str | None = None,
        **kwargs,
    ):
        # TODO get messages from DB
        # TODO send NotifyDisplayMessagesRequest
        return call_result.GetDisplayMessagesPayload(status="Accepted")

    @after("GetDisplayMessages")
    async def after_get_display_messages(self, **kwargs):
        # TODO see how to store the request_id and sent display message
        request = call.NotifyDisplayMessagesPayload(
            request_id=1, message_info=[], tbc=False
        )
        response = await self.call(request)

    @on("ClearDisplayMessage")
    def on_clear_display_messages(self, id: int, **kwargs):
        # TODO delete/invalidate the display message
        return call_result.ClearDisplayMessagePayload(status="Accepted")

    @on("GetLog")
    def on_get_log(
        self,
        log: dict,
        log_type: str,
        request_id: int,
        retries: int | None = None,
        retry_interval: int | None = None,
        **kwargs,
    ):
        # suspuestamente tiene que subir el log a la URL en log["remoteLocation"]
        # TODO save request_id for after funtion
        return call_result.GetLogPayload(
            status="Accepted",
            filename=f"{self._unique_id_generator}-{datetime.utcnow().isoformat()}.log",
        )

    @after("GetLog")
    async def after_get_log(self, **kwargs):
        request = call.LogStatusNotificationPayload(status="Uploading", request_id=1)
        response = await self.call(request)
        # upload a fake log file to log["remoteLocation"]
        request = call.LogStatusNotificationPayload(status="Uploaded", request_id=1)
        response = await self.call(request)

    @on("CustomerInformation")
    def on_customer_information(
        self,
        request_id: int,
        report: bool,
        clear: bool,
        customer_certificate: dict | None = None,
        id_token: dict | None = None,
        customer_identifier: str | None = None,
        **kwargs,
    ):
        if clear:
            # N10 - Clear Customer Information
            pass
        elif report:
            # N09 - Get Customer Information
            # TODO create list of fake customer data
            pass
        return call_result.CustomerInformationPayload(status="Accepted")

    @after("CustomerInformation")
    async def after_customer_information(self, **kwargs):
        request = call.NotifyCustomerInformationPayload(
            data="userdata",
            seq_no=0,
            generated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            request_id=0,
            tbc=False,
        )
        response = await self.call(request)

    @on("ChangeAvailability")
    def on_change_availability(
        self, operational_status: str, evse: dict | None = None, **kwargs
    ):
        if operational_status not in ["Inoperative", "Operative"]:
            return call_result.ChangeAvailabilityPayload(status="Rejected")
        if evse:
            # change availability of that connector
            if evse.get("connectorId") and evse.get("connectorId") < len(
                self.connectors
            ):
                self.connectors[evse.get("connectorId")] = operational_status
                return call_result.ChangeAvailabilityPayload(status="Accepted")
            else:
                return call_result.ChangeAvailabilityPayload(status="Rejected")
        else:
            # change availability chargingn station
            self.availability = operational_status
            return call_result.ChangeAvailabilityPayload(status="Accepted")

    @on("ReserveNow")
    def on_reserve_now(
        self,
        id: int,
        expiry_date_time: str,
        id_token: dict,
        connector_type: str | None = None,
        evse_id: int | None = None,
        group_id_token: dict | None = None,
        **kwargs,
    ):
        try:
            if self.reserved and self.reserved_exp > datetime.now():
                return call_result.ReserveNowPayload(status="Occupied")
            else:
                self.reserved = True
                self.reserved_exp = datetime.fromisoformat(expiry_date_time)
                return call_result.ReserveNowPayload(status="Accepted")
        except:
            return call_result.ReserveNowPayload(status="Rejected")

    @on("CancelReservation")
    def on_cancel_reservation(
        self,
        reservation_id: int,
        **kwargs,
    ):
        # free charging station
        self.reserved = False
        return call_result.CancelReservationPayload(status="Accepted")

    @after("CancelReservation")
    async def after_cancel_reservation(self, **kwargs):
        request = call.StatusNotificationPayload(
            timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            connector_status="Available",
            evse_id=0,
            connector_id=0,
        )
        response = await self.call(request)

    @on("CostUpdated")
    def on_cost_updated(
        self,
        total_cost: int,
        transaction_id: str,
        **kwargs,
    ):
        return call_result.CostUpdatedPayload()

    @on("UpdateFirmware")
    def on_update_firmware(
        self,
        request_id: int,
        firmware: dict,
        retries: int | None = None,
        retry_interval: int | None = None,
        **kwargs,
    ):
        # send firmware uri to virustotal for analysis
        if self.vt_client:
            try:
                url_id = vt.url_id(firmware.get("location"))
                url = self.client.get_object("/urls/{}", url_id)
                LOGGER.info(f"VirusTotal analysis: {url.last_analysis_stats}")
            except Exception as e:
                # usually due to invalid virustotal api key
                pass
        return call_result.UpdateFirmwarePayload("Accepted")

    @on("RequestStartTransaction")
    def on_request_start_transaction(
        self,
        id_token: dict,
        remote_start_id: int,
        evse_id: int | None = None,
        group_id_token: dict | None = None,
        charging_profile: dict | None = None,
        **kwargs,
    ):

        return call_result.RequestStartTransactionPayload(status="Accepted")

    @on("SetChargingProfile")
    def on_set_charging_profile(
        self,
        evse_id: int,
        charging_profile: dict,
        **kwargs,
    ):

        return call_result.SetChargingProfilePayload(status="Accepted")


async def main():
    # ws://localhost:8081/OCPP/
    # ws://localhost:9000/CP_2

    # load config json
    with open("/config.json") as file:
        config = json.load(file)

    logging.info("[Charging Point]Using config:")
    logging.info(config)
    ssl_context = None
    security_profile = 1


    if config.get("logstasth").get("ip") is not None:
        instance = LoggerLogstash(
        logstash_port=config.get("logstasth").get("port"), logstash_host=config.get("logstasth").get("ip"), logger_name="ocpp"
        )
        logger = instance.get()


    if config.get("CSMS"):

        if os.path.isfile(config.get("ssl_key")) and os.path.isfile(
            config.get("ssl_pem")
        ):
            # Security profile 3
            security_profile = 3
            if not "wss" in config.get("CSMS"):
                logging.info("Cannot use standard ws with security profile 2/3")
                exit(-1)

            logging.info("Security profile 3")
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_cert_chain(config.get("ssl_pem"), config.get("ssl_key"))
            if os.path.isfile(config.get("local_CA")):
                ssl_context.load_verify_locations(config.get("local_CA"))
                logging.info(f"Using local CA: {config.get('local_CA')}")

        elif "wss" in config.get("CSMS"):
            # Security profile 2
            security_profile = 2
            logging.info("Security profile 2")
            username = config.get("username")
            password = config.get("password")
            if os.path.isfile(config.get("local_CA")):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.load_verify_locations(config.get("local_CA"))
                logging.info(f"Using local CA: {config.get('local_CA')}")
            else:
                # Trusted Certificated
                ssl_context = True
        else:
            # Security profile 1
            logging.info("Security profile 1")
            username = config.get("username")
            password = config.get("password")

        match security_profile:
            case 1:
                # No SSL
                # Security profile 1
                uri = f"{config.get('CSMS')[:5]}{config.get('username')}:{config.get('password')}@{config.get('CSMS')[5:]}{config.get('ID')}"
                logging.info(uri)
                async with websockets.connect(
                    uri,
                    subprotocols=["ocpp2.0.1", "ocpp2.0"],
                ) as ws:

                    charge_point = ChargePoint("OCPP", ws, 30, config)

                    await asyncio.gather(
                        charge_point.start(), charge_point.send_boot_notification()
                    )
            case 2:
                uri = f"{config.get('CSMS')[:5]}{config.get('username')}:{config.get('password')}@{config.get('CSMS')[5:]}{config.get('ID')}"
                logging.info(uri)
                async with websockets.connect(
                    uri,
                    subprotocols=["ocpp2.0.1", "ocpp2.0"],
                    ssl=ssl_context,
                ) as ws:

                    charge_point = ChargePoint("OCPP", ws, 30, config)

                    await asyncio.gather(
                        charge_point.start(), charge_point.send_boot_notification()
                    )
            case 3:
                async with websockets.connect(
                    config.get('CSMS'),
                    subprotocols=["ocpp2.0.1", "ocpp2.0"],
                    ssl=ssl_context,
                ) as ws:

                    charge_point = ChargePoint("OCPP", ws, 30, config)

                    await asyncio.gather(
                        charge_point.start(), charge_point.send_boot_notification()
                    )
    else:
        logging.info("CSMS endpoint not set")


if __name__ == "__main__":
    asyncio.run(main())
