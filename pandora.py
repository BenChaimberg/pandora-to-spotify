"""All things related to Pandora"""
import math
import requests

class AuthorizationError(Exception):
    """Exception raised when request fails due to lack of authorization."""


class PandoraClient:
    """Client to access Pandora API"""

    BASE_URL = "https://www.pandora.com"
    API_VERSION = "v1"
    API_URL = f"{BASE_URL}/api/{API_VERSION}"

    headers = {}
    cookies = {}

    def __init__(self, username, password):
        """Initialize the class.

        Args:
            username (str): A Pandora account's username.
            password (str): A Pandora account's password.
        """

        self._get_csrf()
        self._login(username, password)

    def get_liked_songs(self, station_id):
        """Get the liked songs from a station

        Args:
            station_id (str): The identifier for a station.

        Returns:
            A list of dicts representing songs. Each dict contains three fields: name, album, and
            artist. For example:

            {"name": "Amsterdam", "album": "The Weatherman", "artist": "Gregory Alan Isokov"}

            It is acceptable for the values of album or artist to be None.
        """

        feedbacks = self.get_station_feedbacks(station_id)
        songs = []
        for feedback in feedbacks:
            songs.append({
                "name": feedback["songTitle"],
                "album": feedback["albumTitle"],
                "artist": feedback["artistName"]
            })
        return songs

    def get_stations(self, limit=250):
        """Get the stations for the account.

        Uses the /station/getStations endpoint
        https://6xq.net/pandora-apidoc/rest/stations/#get-stations to return the stations for the
        configured account.

        Args:
            limit (int): The maximum number of stations to return. Default - 250.

        Returns:
            A list of dicts representing stations (format is everything under the "stations" key
            in the spec for the API response, above).
        """

        endpoint = "/station/getStations"
        response = self._send(endpoint, "POST", {"pageSize": limit})
        stations = response.json()["stations"]
        return stations

    def get_station_feedbacks(self, station_id, positive=True):
        """Get the feedback for a station

        Uses /station/getStationFeedback endpoint
        https://6xq.net/pandora-apidoc/rest/stations/#get-station-feedback to return the positive
        or negative feedback for the given station.

        Args:
            station_id (str): The identifier for a station.
            positive (bool): Whether to return positive (True) or negative (False) feedback.
                Default - True.

        Returns:
            A list of dicts representing feedbacks (format is everything under the "feedback" key
            in the spec for the API response, above.
        """
        page_size = 10
        endpoint = "/station/getStationFeedback"
        base_request = {
            "stationId": station_id,
            "positive": positive,
            "pageSize": page_size
        }

        size_request = base_request.copy()
        size_request["pageSize"] = 1
        total_feedbacks = self._send(endpoint, "POST", size_request).json()["total"]

        feedback = []
        for i in range(math.ceil(total_feedbacks / page_size)):
            feedback_request = base_request.copy()
            feedback_request["startIndex"] = i * page_size
            feedback_response = self._send(endpoint, "POST", feedback_request).json()
            feedback.extend(feedback_response["feedback"])
        return feedback

    def _send(self, endpoint, method, data):
        """Send a request to an endpoint

        Send an HTTP request to a endpoint using the specified method and passing the specified
        data as a JSON object. The content type of the request is application/json. The request
        includes authentication headers and cookies (created at class initialization).

        Args:
            endpoint (str): The API endpoint to be accessed.
            method (str): The HTTP request method. Supported methods: POST.
            data (dict): The data to be sent in the request body.

        Raises:
            ValueError: The HTTP method is not in the supported set.
        """

        if method == "POST":
            return requests.post(
                f"{self.API_URL}{endpoint}",
                headers=self.headers,
                cookies=self.cookies,
                json=data
            )
        else:
            raise ValueError(f"supported methods are POST but given {method}")

    # Begin Authentication
    def _get_csrf(self):
        """
        Gets the CSRF token from Pandora's home website. Saves into a cookie and default HTTP
        headers.
        """

        csrf_token_header_name = "X-CsrfToken"
        if csrf_token_header_name not in self.headers:
            home_head_response = requests.head(self.BASE_URL)
            self.cookies.update(home_head_response.cookies)
            csrf_token = self.cookies["csrftoken"]
            csrf_header = {csrf_token_header_name: csrf_token}
            self.headers.update(csrf_header)

    def _login(self, username, password):
        """
        Gets an auth token for the app to act on behalf of the user. Saves into the default HTTP
        headers.
        """

        auth_token_header_name = "X-AuthToken"
        if auth_token_header_name not in self.headers:
            login_response = self._send("/auth/login", "POST", {
                "username": username,
                "password": password
            })
            try:
                auth_token = login_response.json()["authToken"]
            except KeyError:
                raise AuthorizationError()
            auth_header = {auth_token_header_name: auth_token}
            self.headers.update(auth_header)
    # End Authentication
