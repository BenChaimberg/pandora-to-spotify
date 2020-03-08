"""All things related to Spotify"""
import json
import re
import webbrowser

import requests


class SongNotFoundError(Exception):
    """Exception raised when search for song returns no results."""


class AuthorizationError(Exception):
    """Exception raised when request fails due to lack of authorization."""


class SpotifyClient:
    """Client to access Spotify API."""

    API_VERSION = "v1"
    API_URL = f"https://api.spotify.com/{API_VERSION}"

    headers = {}
    _user_id = None

    def __init__(self):
        """Initialize the class.

        Gets the necessary authorization to access the API on behalf of a user.
        """

        self._authorize()

    def import_song_group(self, group):
        """Imports a group of songs into a new playlist.

        Args:
            group (dict): A dict representing a group of songs. Should contain a "name" field of
                type str and a "songs" field of type list of dicts. Each dict in the "songs" list
                should have fields "name", "album", and "artist", all of type str.
        """

        playlist_id = self.create_playlist(group["name"])
        for song in group["songs"]:
            self.import_song(song, playlist_id)

    def import_song(self, song, playlist_id):
        """Imports a song into an existing playlist.

        Args:
            song (dict): A dict representing a song. The dict should have fields "name", "album",
                and "artist", all of type str.
            playlist_id (str): A Spotify ID for a playlist.
        """

        song_uri = self.find_song_uri(song)
        self.add_song_to_playlist(song_uri, playlist_id)

    def add_song_to_playlist(self, song_uri, playlist_id):
        """Adds a song to a playlist.

        Uses the /playlists/{playlist_id}/tracks endpoint
        https://developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/
        to add a song to a playlist owned by the user.

        Args:
            song_uri (str): A Spotify URI for a song.
            playlist_id (str): A Spotify ID for a playlist
        """

        endpoint = f"/playlists/{playlist_id}/tracks"
        self._send(endpoint, "POST", params={"uris": song_uri})

    def create_playlist(self, name):
        """Creates a playlist.

        Uses the /users/{user_id}/playlists endpoint
        https://developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/
        to create a new (empty) playlist owned by the user.

        Args:
            name (str): The name for the new playlist.

        Returns:
            A str representing a Spotify ID for the new playlist.
        """

        user_id = self.get_current_user()
        endpoint = f"/users/{user_id}/playlists"
        headers = self.headers
        headers.update()
        response = self._send(
            endpoint,
            "POST",
            extra_headers={"Content-Type": "application/json"},
            data=json.dumps({"name": name, "public": False})
        )
        playlist_id = response.json()["id"]
        return playlist_id

    def find_song_uri(self, song):
        """Finds the Spotify URI for a song

        Searches Spotify for a song given its name, album, and artist, returning the song's URI if
        it can be found.

        Returns:
            A str representing a Spotify URI for the song.

        Raises:
            SongNotFoundError: The song cannot be found on Spotify.
        """

        try:
            tracks = self.search_song(song["name"], artist=song["artist"])
        except SongNotFoundError:
            tracks = self.search_song(song["name"], album=song["album"], artist=song["artist"])

        result = tracks[0]
        uri = result["uri"]
        return uri

    def get_current_user(self):
        """Gets the Spotify ID for the authorized user.

        Uses the /me endpoint
        https://developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/
        to get the Spotify ID for the authorized user.

        Returns:
            A str representing the Spotify ID of the authorized user.
        """

        if self._user_id:
            return self._user_id
        endpoint = "/me"
        response = self._send(endpoint, "GET")
        user_id = response.json()["id"]
        self._user_id = user_id
        return user_id

    def search_song(self, name, album=None, artist=None):
        """Searches for a song.

        Uses the /search endpoint
        (https://developer.spotify.com/documentation/web-api/reference/search/search/)
        to search for a song given its name and possibly its album and artist.

        Args:
            name (str): The song's name.
            album (str, optional): The song's album. Default - None.
            artist (str, optional): The song's artist. Default - None.

        Returns:
            A list of dict representing songs (format is everything under the "tracks"/"items" keys
            in the spec for the API response, above).

        Raises:
            SongNotFoundError: The search returned 0 hits.
        """

        endpoint = "/search"
        query = f"track:{name}"
        if artist:
            query += f" artist:{artist}"
        if album:
            query += f" album:{album}"
        response = self._send(endpoint, "GET", params={"q": query, "type": "track"})
        tracks = response.json()["tracks"]
        if tracks["total"] == 0:
            raise SongNotFoundError(
                f"song name={name} artist={artist} album={album} could not be found"
            )
        return tracks["items"]

    def _send(self, endpoint, method, extra_headers=None, **kwargs):
        """Send a request to an endpoint

        Send an HTTP request to a endpoint using the specified method, adding extra headers and
        including data as required. The request includes default authentication headers (created at
        class initialization).

        Args:
            endpoint (str): The API endpoint to be accessed.
            method (str): The HTTP request method. Supported methods: GET, POST.
            extra_headers (dict, optional): Extra HTTP headers to be added to the request.
                Default - None.
            **kwargs: Arbitrary keyword arguments to be passed to the request (namely "params" or
                "data" dicts).

        Raises:
            ValueError: The HTTP method is not in the supported set.
        """

        headers = self.headers
        if extra_headers:
            headers.update(extra_headers)
        if method == "GET":
            return requests.get(
                f"{self.API_URL}{endpoint}",
                headers=headers,
                **kwargs
            )
        elif method == "POST":
            return requests.post(
                f"{self.API_URL}{endpoint}",
                headers=headers,
                **kwargs
            )
        else:
            raise ValueError(f"supported methods are GET,POST but given {method}")

    # Begin Authentication
    CLIENT_ID = "8d620a84255e4806b1bbed7df287cdd7"
    CLIENT_SECRET = "fec769303a3d4dbba2fbe5ee2e95cee2"
    AUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
    AUTH_CLIENT_HEADER = {
        "Authorization": (
            "Basic "
            "OGQ2MjBhODQyNTVlNDgwNmIxYmJlZDdkZjI4N2NkZDc6"
            "ZmVjNzY5MzAzYTNkNGRiYmEyZmJlNWVlMmU5NWNlZTI="
        )
    }
    AUTH_SCOPE = "playlist-modify-private"
    AUTH_CACHE_FILE = "auth_cache"
    AUTH_REDIRECT_URI = "http://localhost/auth/"

    def _authorize(self):
        try:
            self._refresh_auth()
            return
        except AuthorizationError:
            pass

        user_auth_code = self._authorize_user()

        response = requests.post(
            self.AUTH_TOKEN_URL,
            headers=self.AUTH_CLIENT_HEADER,
            data={
                "grant_type": "authorization_code",
                "code": user_auth_code,
                "redirect_uri": self.AUTH_REDIRECT_URI
            }
        )
        self._handle_auth_response(response)
        refresh_token = response.json()["refresh_token"]
        with open(self.AUTH_CACHE_FILE, "w") as auth_file:
            auth_file.write(refresh_token)

    def _refresh_auth(self):
        try:
            with open(self.AUTH_CACHE_FILE, "r") as auth_file:
                refresh_token = auth_file.read()
        except FileNotFoundError:
            raise AuthorizationError("auth file containing refresh token could not be found")
        else:
            response = requests.post(
                self.AUTH_TOKEN_URL,
                headers=self.AUTH_CLIENT_HEADER,
                data={"grant_type": "refresh_token", "refresh_token": refresh_token}
            )
            self._handle_auth_response(response)

    def _handle_auth_response(self, response):
        if response.status_code != 200:
            raise AuthorizationError(
                f"could not authorize, API returned code: '{response.status_code}' \
                and message: '{response.text}'"
            )
        access_token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def _authorize_user(self):
        request = requests.Request(
            method="GET",
            url="https://accounts.spotify.com/authorize",
            params={
                "client_id": self.CLIENT_ID,
                "response_type": "code",
                "redirect_uri": self.AUTH_REDIRECT_URI,
                "scope": self.AUTH_SCOPE
            }
        ).prepare()
        webbrowser.open(request.url)
        redirect = input("enter the URL you were redirected to: ")

        # TODO: this is a crappy way of parsing URLs but I think turning this into a webapp would
        # be a better use of time than making it nice
        accept_match = re.match(rf"{self.AUTH_REDIRECT_URI}\?code=(.*)", redirect)
        deny_match = re.match(rf"{self.AUTH_REDIRECT_URI}\?error=access_denied", redirect)
        if deny_match:
            raise AuthorizationError(
                "unable to authorize application, make sure you click 'Agree'"
            )
        if not accept_match:
            raise AuthorizationError("could not parse, make sure you copy the URL verbatim")
        auth_code = accept_match.group(1)
        return auth_code
    # End Authentication
