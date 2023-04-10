import asyncio
from functools import partial
from datetime import datetime, timedelta
from ocpp.v201 import datatypes, enums
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

    async def change_variables(self, id: str, variable_data: list):
        for cp in self._chargers:
            if cp.id == id:
                await cp.send_set_variables(variable_data)

    async def get_variables(self, id: str, get_variable_data: list):
        for cp in self._chargers:
            if cp.id == id:
                result = await cp.send_get_variables(get_variable_data)
                return result.get_variable_result

    async def get_connected_chargers(self):
        chargers = {}
        for cp in self._chargers:
            chargers[cp.id] = {
                "ChargerStation": cp.charger_station,
                "connectors": cp.connectors,
                "displayMesagges": cp.display_message,
            }
        return chargers

    async def reserve_now(
        self, id: str, id_token: dict, expiry_date_time: datetime, connector: int = 1
    ):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_reserve_now(
                    id=connector,
                    expiry_date_time=expiry_date_time,
                    id_token=id_token,
                )
                return result.status

        raise ValueError(f"Charger {id} not connected.")

    async def cancel_reserve(self, id: str, connector: int = 1):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_reserve_cancel(reservation_id=connector)
                return result.status

        raise ValueError(f"Charger {id} not connected.")

    async def set_display_message(self, id: str, message):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_set_display_messages(message)
                return result.status
        raise ValueError(f"Charger {id} not connected.")

    async def get_display_message(self, id: str):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_get_display_messages(1)
                return result.status
        raise ValueError(f"Charger {id} not connected.")

    async def clear_display_message(self, id: str, msg_id: int):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_clear_display_messages(msg_id)
                if result.status == "Acepted":
                    cp.display_message.pop(msg_id - 1)
                return result.status
        raise ValueError(f"Charger {id} not connected.")

    async def send_sendlocallist(
        self,
        id: str,
        version_number: int,
        update_type: str,
        local_authorization_list: list,
        local_authorization_list_dict: list,
    ):
        for cp, task in self._chargers.items():
            if cp.id == id:
                result = await cp.send_sendlocallist(
                    version_number,
                    update_type,
                    local_authorization_list,
                    local_authorization_list_dict,
                )
                return result.status
        raise ValueError(f"Charger {id} not connected.")

    async def get_locallist(self, id: str):
        for cp, task in self._chargers.items():
            if cp.id == id:
                return cp.local_list

    async def update_firmware(self, id: str, url: str):
        for cp, task in self._chargers.items():
            if cp.id == id:
                firmware = datatypes.FirmwareType(
                    location=url, retrieve_date_time=datetime.now().isoformat()
                )
                result = await cp.send_update_firmware(request_id=1, firmware=firmware)
                return result.status
        raise ValueError(f"Charger {id} not connected.")
