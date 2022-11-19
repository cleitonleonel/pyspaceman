import os
import re
import json
import time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

URL_BASE = 'https://bet7k.com'
URL_API = 'https://api.bs2bet.com'
URL_CLIENT = 'https://client.pragmaticplaylive.net'
URL_PLAY = 'https://gs9.pragmaticplaylive.net'

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504, 104],
    allowed_methods=["HEAD", "POST", "PUT", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)


class Browser(object):

    def __init__(self):
        self.response = None
        self.headers = None
        self.session = requests.Session()

    def set_headers(self, headers=None):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
        }
        if headers:
            for key, value in headers.items():
                self.headers[key] = value

    def get_headers(self):
        return self.headers

    def send_request(self, method, url, **kwargs):
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        return self.session.request(method, url, **kwargs)


class SpaceManAPI(Browser):

    def __init__(self, email=None, password=None):
        super().__init__()
        self.token = None
        self.is_connected = False
        self.email = email
        self.password = password
        self.location = None
        self.j_session_id = None
        self.set_headers()
        self.headers = self.get_headers()
        self.get_response()

    def get_response(self):
        return self.send_request('GET',
                                 f"{URL_BASE}/casino/1301-live-spaceman",
                                 headers=self.headers)

    def auth(self):
        payload = {
            "email": self.email,
            "password": self.password
        }
        self.headers["origin"] = URL_BASE
        self.headers["referer"] = f"{URL_BASE}/casino/1301-live-spaceman?login=true"
        self.response = self.send_request("POST",
                                          f"{URL_API}/v2/auth/login",
                                          json=payload,
                                          headers=self.headers)
        if not self.response.json().get("error"):
            self.token = self.response.json()["access_token"]
            self.is_connected = True
        return self.response.json()

    def reconnect(self):
        print("Reconectando...")
        self.auth()
        self.start_game()
        self.get_session()

    def get_profile(self):
        self.headers["origin"] = URL_BASE
        self.headers["referer"] = f"{URL_BASE}/casino/1301-live-spaceman?login=true"
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("GET",
                                          f"{URL_API}/v2/auth/user-profile",
                                          headers=self.headers)
        return self.response.json()

    def start_game(self):
        self.headers["authorization"] = f"Bearer {self.token}"
        self.response = self.send_request("GET",
                                          f"{URL_API}/v2/start-game?game=1301&platform=WEB",
                                          headers=self.headers)
        if self.response:
            response_data = self.response.json()
            self.location = response_data.get("gameURL")
        return self.response.json()

    def get_session(self):
        self.headers = {}
        self.headers["referer"] = f"{URL_BASE}/casino/1301-live-spaceman"
        self.response = self.send_request("GET",
                                          self.location,
                                          headers=self.headers)
        if self.response:
            location_url = self.response.history[1].headers.get("Location")
            self.j_session_id = re.findall(r"&JSESSIONID=(.*?)&\S", location_url)[0]
            self.save_json()
            return True
        return False

    def game_data(self):
        result_dict = {
            "result": False
        }
        payload = {
            "tableId": "spacemanyxe123nh",
            "numberOfGames": 500,
            "JSESSIONID": self.j_session_id
        }
        self.headers = {}
        self.headers["referer"] = f"{URL_CLIENT}/"
        self.response = self.send_request("GET",
                                          f"{URL_PLAY}/api/ui/statisticHistory",
                                          params=payload,
                                          headers=self.headers)
        if self.response:
            try:
                response_data = self.response.json()
                if not response_data["errorCode"] == "1":
                    result_dict["object"] = response_data
                    result_dict["result"] = True
                else:
                    result_dict["result"] = False
            except:
                result_dict["result"] = False
        return result_dict

    def save_json(self, data=None):
        with open(f"{self.filename}.json", "w") as file:
            if not data:
                file.write(json.dumps({"JSESSIONID": self.j_session_id}))
            else:
                file.write(json.dumps(data, indent=4))

    def check_session(self):
        self.filename = "bt7k_session"
        if not os.path.exists(f"{self.filename}.json"):
            print("Gerando novo j_session_id...")
            login = self.auth()
            if login.get("error"):
                print(f"Erro, usuário {self.email} ou {self.password} inválidos!!!")
                exit()
            self.start_game()
            self.get_session()
        with open(f"{self.filename}.json", "r") as file:
            json_data = file.read()
            if json_data == "":
                print("Token não encontrado!!!")
                print("Reconectando...")
                os.remove(f"{self.filename}.json")
                file.close()
                return self.check_session()
            j_session_id = json.loads(json_data)
            self.j_session_id = j_session_id["JSESSIONID"]
            if self.j_session_id and self.game_data().get("result"):
                self.is_connected = True
                print("JSESSIONID is valid!!!")
            else:
                self.response.json()
                self.is_connected = False
                print("JSESSIONID not is valid!!!")
                os.remove(f"{self.filename}.json")
                file.close()
                return self.check_session()


if __name__ == '__main__':
    sma = SpaceManAPI("email@gmail.com", "senha123")
    sma.check_session()
    # sma.is_connected = False # SE QUISER RECONECTAR PARA MANTER SEMPRE COM A ULTIMA SESSÃO ATIVA
    if not sma.is_connected:
        sma.reconnect()
    while True:
        data = sma.game_data()
        if data["result"]:
            print(json.dumps(data["object"], indent=4))
        time.sleep(5)
