import json
import sys
import re

from urllib3 import Timeout, PoolManager
from time import sleep
from datetime import datetime

# Petterns of Sensitive data made in the requests
PATTERNS = [
    r'[A-Za-z0-9+\/=]{80,}', #Long base64 strings
    r'[A-Za-z0-9+\/]{27}=', #Secret key pattern
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}' #UUID Pattern   
]

class RequestError(Exception):
    pass


# Function to be used to replace sensitive information delivered through logs
def replace_sensitive_data(text, placeholder="****"):
    """Replace Senitive date to be output"""

    for pattern in PATTERNS:
        results = re.findall(pattern, text)
        if results:
            for result in results:
                new_string = f"{result[:4]}{placeholder}"
                text = text.replace(result, new_string)

    return text


class PrismaAPI(object):
    def __init__(self, 
        prisma_api_endpoint: str,
        compute_api_endpoint: str,
        username: str,
        password: str,
        limit=50,
        time_sleep=5,
        connect_timeout=2,
        read_timeout=7,
        debug=False
    ):
        self.prisma_api_endpoint = prisma_api_endpoint
        self.compute_api_endpoint = compute_api_endpoint
        self.username = username
        self.password = password
        self.limit = limit
        self.time_sleep = time_sleep
        self.debug = debug
        timeout = Timeout(connect=connect_timeout, read=read_timeout)
        self.http = PoolManager(timeout=timeout)

        self.headers = {"Content-Type": "application/json"}

        token_body = {
            "username": self.username,
            "password": self.password
        }

        if not self.prisma_api_endpoint:
            if not self.compute_api_endpoint:   
                print("If PRISMA_API_ENDPOINT is not set, then COMPUTE_API_ENDPOINT is required.")
                sys.exit(1)
            else:
                # Check for console connectivity
                self.has_connectivity()

                # Retrieve Compute Console token
                compute_token = json.loads(self.http_request(self.compute_api_endpoint, "/api/v1/authenticate", token_body))["token"]
                self.headers["Authorization"] = f"Bearer {compute_token}"

        else:
            # Retrieve Prisma Cloud token
            prisma_token = json.loads(self.http_request(self.prisma_api_endpoint, "/login", token_body))["token"]
            self.headers["X-Redlock-Auth"] = prisma_token

            if not self.compute_api_endpoint:
                # Get Compute API endpoint
                self.compute_api_endpoint = json.loads(self.http_request(self.prisma_api_endpoint, "/meta_info", method="GET"))["twistlockUrl"]


    def has_connectivity(self):
        response = self.http.request("GET",f"{self.compute_api_endpoint}/api/v1/_ping")
        if response.status == 200:
            print(f"{datetime.now()} Connection to the endpoint {self.compute_api_endpoint} succedded.")
        else:
            print(f"{datetime.now()} Connection to the endpoint {self.compute_api_endpoint} failed.")
            sys.exit(1)


    def http_request(self, api_endpoint, path, body={}, method="POST", skip_error=False):
        if self.debug: print(f"{datetime.now()} Making the following request:\n    URL: {api_endpoint}\n    Path: {path}\n    Method: {method}\n")
        response = self.http.request(method, f"{api_endpoint}{path}", headers=self.headers, body=json.dumps(body))

        if response.status == 200:
            return response.data
        
        if response.status == 401 and path not in ("/login", "/api/v1/authenticate"):
            token_body = {
                "username": self.username,
                "password": self.password
            }

            if "X-Redlock-Auth" in self.headers:
                token = json.loads(self.http_request(self.prisma_api_endpoint, "/login", token_body))["token"]
                self.headers["X-Redlock-Auth"] = token

            elif "Authorization" in self.headers:
                token = json.loads(self.http_request(self.compute_api_endpoint, "/api/v1/authenticate", token_body))["token"]
                self.headers["Authorization"] = f"Bearer {token}"
                
            return self.http_request(api_endpoint, path, body, method, skip_error)
        
        if response.status == 429:
            sleep(self.time_sleep)
            return self.http_request(api_endpoint, path, body, method, skip_error)

        # Error Message
        msg = f"{datetime.now()} Error making request to {api_endpoint}{path}. Method: {method}. Body: {body}. Error message: {response.data}. Status code: {response.status}"
        
        if not skip_error:
            raise RequestError(replace_sensitive_data(msg))
        
        if self.debug: print(replace_sensitive_data(msg))
        return "{}"


    def compute_request(self, path, body={}, method="POST", skip_error=False):
        return self.http_request(self.compute_api_endpoint, path, body, method, skip_error)


    def prisma_request(self, path, body={}, method="POST", skip_error=False):
        return self.http_request(self.prisma_api_endpoint, path, body, method, skip_error)


    def get_all_compute_resources(self, path, parameters = ""):
        offset = 0
        response = "first_response"
        data = []
        base_path = f"{path}?limit={self.limit}"
        if parameters: base_path = f"{base_path}&{parameters}"

        while response:
            full_path = f"{base_path}&offset={offset}" 
            response = json.loads(self.http_request(self.compute_api_endpoint, full_path, method="GET"))
            if response:
                data += response
                offset += self.limit

        if self.debug: print(f"{datetime.now()} Total data retrieved from Compute Console: {len(data)}. Path: {path}\n")
        return data

