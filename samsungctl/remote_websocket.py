import base64
import json
import logging
import socket
import time
import ssl

from . import exceptions


URL_FORMAT = "ws://{}:{}/api/v2/channels/samsung.remote.control?name={}"


class RemoteWebsocket():
    """Object for remote control connection."""

    def __init__(self, config):
        import websocket

        if not config["port"]:
            config["port"] = 8001

        if config["timeout"] == 0:
            config["timeout"] = None

        # If already paired with token, use SSL directly
        use_ssl = config.get("paired") and config.get("token")
        if use_ssl:
            config["port"] = 8002
            url = "wss://{}:{}/api/v2/channels/samsung.remote.control?name={}".format(config["host"], config["port"],
                                self._serialize_string(config["name"]))
            sslopt = {"cert_reqs": ssl.CERT_NONE}
        else:
            url = URL_FORMAT.format(config["host"], config["port"],
                                    self._serialize_string(config["name"]))
            sslopt = {}

        if config.get("token"):
            url += "&token=" + config["token"]

        self.connection = websocket.create_connection(url, config["timeout"], sslopt=sslopt)

        response = self._read_response()
        if response["event"] == "ms.channel.unauthorized":
            if not use_ssl:
                # Try SSL connection on port 8002
                logging.debug("Trying SSL connection on port 8002")
                self.connection.close()
                config["port"] = 8002
                url = "wss://{}:{}/api/v2/channels/samsung.remote.control?name={}".format(config["host"], config["port"],
                                    self._serialize_string(config["name"]))
                if config.get("token"):
                    url += "&token=" + config["token"]
                sslopt = {"cert_reqs": ssl.CERT_NONE}
                self.connection = websocket.create_connection(url, config["timeout"], sslopt=sslopt)
                response = self._read_response()
                if response["event"] != "ms.channel.connect":
                    self.close()
                    raise exceptions.AccessDenied()
            else:
                self.close()
                raise exceptions.AccessDenied()
        elif response["event"] != "ms.channel.connect":
            self.close()
            raise exceptions.UnhandledResponse(response)

        # Extract token if present
        if "data" in response and "token" in response.get("data", {}):
            config["token"] = response["data"]["token"]
            logging.debug("Token received: %s", config["token"])
        config["paired"] = True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Close the connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logging.debug("Connection closed.")

    def control(self, key):
        """Send a control command."""
        if not self.connection:
            raise exceptions.ConnectionClosed()

        payload = json.dumps({
            "method": "ms.remote.control",
            "params": {
                "Cmd": "Click",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey"
            }
        })

        logging.info("Sending control command: %s", key)
        self.connection.send(payload)
        time.sleep(self._key_interval)

    _key_interval = 0.5

    def _read_response(self):
        response = self.connection.recv()
        response = json.loads(response)
        return response

    @staticmethod
    def _serialize_string(string):
        if isinstance(string, str):
            string = str.encode(string)

        return base64.b64encode(string).decode("utf-8")
