"""
Process for obtaining all train identifiers (OperationalTrainNumber)
going between two stations.
"""

import os
from dotenv import load_dotenv
import requests
from pathlib import Path
from typing import List

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SJ_API_KEY = os.getenv("SJ_API_KEY")

def getAllTrains(locationSignature1: str, locationSignature2: str) -> List[int]:
    """
    Return all trains (identified by OperationalTrainNumber) 
    going between both locations in both directions.
    """
    trains1 = getTrains(locationSignature1)
    trains2 = getTrains(locationSignature2)
    trains = [t for t in trains1 if t in trains2]
    return trains

def getTrains(locationSignature: str) -> List[int]:
    """
    Get the trains (identified by OperationalTrainNumber)
    going to or from the location.
    """
    headers = {
        "Content-Type": "application/xml"
    }
    req = f"""
    <REQUEST>
        <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
        <QUERY objecttype="TrainAnnouncement" schemaversion="1.9" limit="100000">
        <FILTER>
            <EQ name="LocationSignature" value="{locationSignature}" />
        </FILTER>
        </QUERY>
    </REQUEST>
    """
    print(f"Fetching departures/arrivals to {locationSignature}...")
    while True:
        try:
            resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
            break
        except:
            print("Retrying...")
    obj = resp.json()
    data = obj["RESPONSE"]["RESULT"][0]["TrainAnnouncement"]
    print(f"Interpreting {len(data)} announcements...")
    trains = set()
    for entry in data:
        otn = entry.get("OperationalTrainNumber")
        ati = entry.get("AdvertisedTrainIdent")
        if otn != None:
            trains.add(int(otn))
        elif ati != None:
            trains.add(int(ati))
    trains = list(trains)
    print(f"Found {len(trains)} trains going to or from {locationSignature}")
    return trains

def saveTrains(location: str, trains: List[int]) -> None:
    """
    Write the given trains to a given file directory.
    """
    file = Path(location)
    if file.exists():
        answer = input(f"File {location} already exists. Overwrite? (y/n) ")
        if answer.startswith("n"):
            return
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(location, "w+") as f:
        for train in trains:
            f.write(f"{train}\n")

def main():
    locationSignature1 = input("First station (code): ")
    locationSignature2 = input("Second station (code): ")
    trains = getAllTrains(locationSignature1, locationSignature2)
    print(f"Found {len(trains)} trains going between {locationSignature1} and {locationSignature2}")
    location = f"./data/{locationSignature1}_{locationSignature2}/trains.txt"
    answer = input(f"Want to write them to the file {location}? (y/n) ")
    if answer.startswith("y"):
        saveTrains(location, trains)

if __name__ == '__main__':
    main()
