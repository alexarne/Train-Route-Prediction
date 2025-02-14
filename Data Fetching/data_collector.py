import os
from dotenv import load_dotenv
import requests
import json
import sseclient
from datetime import datetime, timezone
from utils import log
from typing import List
from pathlib import Path
from get_trains import getTrains
import shutil

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SJ_API_KEY = os.getenv("SJ_API_KEY")

# class DataCollector:
#     def __init__(self, STATION1, STATION2):
#         self.STATION1 = STATION1
#         self.STATION2 = STATION2

#     def collect(self):
#         print(f"Starting data collection between {self.STATION1} and {self.STATION2}")
#         tg1 = TrainGetter(self.STATION1)
#         tg2 = TrainGetter(self.STATION2)
#         try:
#             while True:
#                 print("routine")
#                 print(tg1.getTrains())
#                 time.sleep(5)
#         finally:
#             tg1.stop()

#     def request(self, trains):


# def handlePositionData(data):
#     print()
#     print(f"AdvertisedTrainNumber {data["Train"]["AdvertisedTrainNumber"]}")
#     print(f"Received at {data.get("ReceivedTime")}")
#     print(f"Measurement {data.get("TimeStamp")}")
#     print(f"Speed {data.get("Speed")}")
#     print(f"Bearing {data.get("Bearing")}")

# def getSSEURL(trainNumber):
#     headers = {
#         "Content-Type": "application/xml"
#     }
#     req = f"""
#     <REQUEST>
#         <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
#         <QUERY changeid="0" objecttype="TrainPosition" namespace="järnväg.trafikinfo" schemaversion="1.1" limit="10000">
#         <FILTER>
#             <AND>
#                 <EQ name="Status.Active" value="true" />
#                 <OR>
#                     <EQ name="Train.JourneyPlanNumber" value="{trainNumber}" />
#                 </OR>
#             </AND>
#         </FILTER>
#         </QUERY>
#     </REQUEST>
#     """
#     resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
#     obj = resp.json()
#     print(json.dumps(obj, indent=2))
#     data = obj["RESPONSE"]["RESULT"][0]
#     now = datetime.now(timezone.utc).astimezone()
#     formatted_now = now.isoformat(timespec='milliseconds')
#     print(f"Received at {receivedTime} measurement taken at {data["TrainPosition"][0]["TimeStamp"]}")

#     return obj["RESPONSE"]["RESULT"][0]["INFO"]["SSEURL"]

# def getPositions(SSEURL):
#     while True:
#         print("Starting streaming session...")
#         session = requests.session()
#         stream = session.get(SSEURL, stream=True)
#         client = sseclient.SSEClient(stream)
#         for event in client.events():
#             obj = json.loads(event.data)
#             print(json.dumps(obj, indent=2))
#             data = obj["RESPONSE"]["RESULT"][0]
#             now = datetime.datetime.now()
#             receivedTime = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
#             for train in data["TrainPosition"]:
#                 train["ReceivedTime"] = receivedTime
#                 handlePositionData(train)
#     return 1




def fetchPositions(stations: List[List[str]]) -> None:
    """
    Takes a list of station-couples, sets up the data directory
    and starts endlessly polling for the positional data of all
    trains moving between the station-couples.
    """
    log(f"Starting data collection between stations:")
    for s1, s2 in stations:
        log(f" - {s1} and {s2}")
    createDataFolder()
    trains = getAllTrains(stations)

def createDataFolder():
    """
    Create the data directory and make sure it didn't exist before.
    """
    dataLocation = "./data"
    while True:
        file = Path(dataLocation)
        if file.exists():
            answer = input("Directory ./data/ already exists. Do you want to remove it? (y/n) ")
            if answer.startswith("y"):
                shutil.rmtree(dataLocation)
            else: 
                continue
        file.mkdir(parents=True, exist_ok=True)
        break

def getAllTrains(stations: List[List[str]]) -> List[List[int]]:
    """
    Get the trains (identified by OperationalTrainNumber) for all
    station couples
    """
    trains = []
    for locationSignature1, locationSignature2 in stations:
        trains.append(getTrains(locationSignature1, locationSignature2))
    return trains

def main():
    number = int(input("How many routes do you want to track? "))
    stations = []
    for i in range(number):
        print(f"------ Route {i+1} ------")
        station1 = input(f"First station (code): ")
        station2 = input(f"Second station (code): ")
        stations.append([station1, station2])
    fetchPositions(stations)

if __name__ == '__main__':
    main()

filters = """
<GT name='TimeStamp' value='$dateadd(-0.00:00:30)' />
<EQ name="Train.OperationalTrainNumber" value="2139" />
<EQ name="Status.Active" value="true" />
"""