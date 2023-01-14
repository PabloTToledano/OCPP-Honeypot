import asyncio
import logging
import random
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on, after
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    async def send_heartbeat(self, interval):
        request = call.HeartbeatPayload()
        while True:
            await self.call(request)
            await asyncio.sleep(interval)

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charging_station={
                "model": "Electrify America Ultra-Fast",
                "vendor_name": "Signet",
            },
            reason="PowerUp",
        )
        response = await self.call(request)

        if response.status == "Accepted":
            print("Connected to central system.")
            await self.send_heartbeat(response.interval)

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
            # Do something with variable.get("attributeValue")
            variable_result.append(
                {
                    "attributeType": variable.get("attributeType", "Actual"),
                    "attributeStatus": "Accepted",
                    "component": variable.get("component"),
                    "variable": variable.get("variable"),
                    "attributeValue ": "",
                }
            )
        return call_result.GetVariablesPayload(get_variable_result=variable_result)

    @on("DataTransfer")
    def on_data_transfer(self, **kwargs):
        # TODO save the data
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
        # TODO retrieve versionNumber
        return call_result.GetLocalListVersionPayload(version_number=1)

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


async def main():
    async with websockets.connect(
        "ws://localhost:9000/CP_2", subprotocols=["ocpp2.0.1", "ocpp2.0.1j"]
    ) as ws:

        charge_point = ChargePoint("CP_2", ws)
        await asyncio.gather(
            charge_point.start(), charge_point.send_boot_notification()
        )


if __name__ == "__main__":
    asyncio.run(main())
