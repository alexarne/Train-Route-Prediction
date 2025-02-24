"""
Process for obtaining all train identifiers (OperationalTrainNumber)
going between two stations.
"""

import os
from dotenv import load_dotenv
import requests
from pathlib import Path
from typing import List
from utils import log

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SJ_API_KEY = os.getenv("SJ_API_KEY")
DATA_FOLDER_DIR = os.getenv("DATA_FOLDER_DIR")

def getTrains(*locationSignatures) -> List[int]:
    """
    Return all trains (identified by OperationalTrainNumber) 
    going between all locations in both directions.
    """
    if len(locationSignatures) == 0: 
        return []
    elif len(locationSignatures) > 1:
        # Get the intersection of trains which go through all stations
        log(f"Fetching trains between {", ".join(locationSignatures)}...")
        trains = set(getTrains(locationSignatures[0]))
        for i in range(1, len(locationSignatures)):
            # Intersection of common trains
            trains = trains & set(getTrains(locationSignatures[i]))
        trains = list(trains)
        log(f"Found {len(trains)} trains going between {", ".join(locationSignatures)}")
        return trains
    else:
        # Get all trains going to or from a singular train station.
        locationSignature = locationSignatures[0]
        headers = {
            "Content-Type": "application/xml"
        }
        req = f"""
        <REQUEST>
            <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
            <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" limit="100000" orderby="AdvertisedTimeAtLocation">
            <FILTER>
                <EQ name="LocationSignature" value="{locationSignature}" />
            </FILTER>
            </QUERY>
        </REQUEST>
        """
        log(f"Fetching departures/arrivals to {locationSignature}...")
        while True:
            try:
                resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
                break
            except:
                log("Retrying getTrains fetch...")
        obj = resp.json()
        data = obj["RESPONSE"]["RESULT"][0]["TrainAnnouncement"]
        log(f"Interpreting {len(data)} announcements...")
        trains = set()
        for entry in data:
            otn = entry.get("OperationalTrainNumber")
            if otn != None:
                trains.add(int(otn))
        trains = list(trains)
        log(f"Found {len(trains)} trains going to or from {locationSignature}")
        return trains

def saveTrains(location: str, trains: List[int]) -> None:
    """
    Write the given trains to a given file directory.
    """
    file = Path(location)
    file.parent.mkdir(parents=True, exist_ok=True)
    log(f"Writing {len(trains)} trains to {location}...")
    with open(location, "w") as f:
        for train in trains:
            f.write(f"{train}\n")

def main():
    stations = []
    i = 1
    while True:
        station = input(f"Station {i} (code): ")
        if station == "":
            break
        stations.append(station)
        i += 1
    trains = getTrains(*stations)
    dir = f"{DATA_FOLDER_DIR}/trains_{"_".join(stations)}.txt"
    answer = input(f"Want to write them to the file {dir}? (y/n) ")
    if answer.startswith("y"):
        if Path(dir).exists():
            answer = input(f"File {dir} already exists. Overwrite? (y/n) ")
            if not answer.startswith("y"):
                print("Aborting...")
                return
        saveTrains(dir, trains)
    else:
        trains.sort()
        print(trains)

if __name__ == '__main__':
    main()
