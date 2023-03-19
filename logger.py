import logging
import logstash
import sys


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


instance = LoggerLogstash(
    logstash_port=5959, logstash_host="localhost", logger_name="ocpp"
)
logger = instance.get()

count = 0
from time import sleep

while True:

    count = count + 1

    if count % 2 == 0:
        logger.error("Error Message Code Faield :{} ".format(count))
    else:
        logger.info("python-logstash: test logstash info message:{} ".format(count))

    exit
