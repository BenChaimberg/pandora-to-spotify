#!/usr/bin/env python3
import configparser

from pandora import PandoraClient
from spotify import SpotifyClient

config = configparser.ConfigParser()
config.read("conf.ini")

pandora = PandoraClient(config["pandora"]["username"], config["pandora"]["password"])
spotify = SpotifyClient()

stations = pandora.get_stations()
# select only a single station that I know contains liked songs, for testing purposes
stations = filter(lambda station: station["stationId"] == "344712744001219816", stations)
for station in stations:
    liked_songs = pandora.get_liked_songs(station["stationId"])
    station.update({"songs": liked_songs})
    spotify.import_song_group(station)
