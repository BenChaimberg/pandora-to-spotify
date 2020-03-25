#!/usr/bin/env python3
import configparser

from pandora import PandoraClient
from spotify import SpotifyClient

config = configparser.ConfigParser()
config.read("conf.ini")

try:
    app_config = config["app"]
    debug = app_config.getboolean("debug")
except KeyError:
    debug = False

pandora = PandoraClient(config["pandora"]["username"], config["pandora"]["password"])
spotify = SpotifyClient()

stations = pandora.get_stations()

if debug:
    # select only a single station that I know contains liked songs, for testing purposes
    stations = filter(lambda station: station["stationId"] == "894519264273116392", stations)

for station in stations:
    liked_songs = pandora.get_liked_songs(station["stationId"])
    if len(liked_songs) > 0:
        station.update({"songs": liked_songs})
        spotify.import_song_group(station)
