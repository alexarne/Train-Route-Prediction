import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
from utils import log
from typing import List
from pathlib import Path
from get_trains import getTrains, saveTrains
import shutil
import time
import sqlite3
from geomet import wkt
import traceback
import time

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SJ_API_KEY = os.getenv("SJ_API_KEY")
DATA_FOLDER_DIR = os.getenv("DATA_FOLDER_DIR")

def createDataFolder() -> None:
    """
    Create the data directory and make sure it didn't exist before.
    """
    while True:
        file = Path(DATA_FOLDER_DIR)
        if file.exists():
            answer = input(f"Directory {DATA_FOLDER_DIR} already exists. Do you want to remove it? (y/n) ")
            if answer.startswith("y"):
                shutil.rmtree(DATA_FOLDER_DIR)
            else: 
                continue
        file.mkdir(parents=True, exist_ok=True)
        break

def fetchPositions(stations: List[List[str]]) -> None:
    """
    Takes a list of station-lists, sets up the data directory
    and starts endlessly polling for the positional data of all
    trains moving between the station-lists, regardless of order.
    """
    log(f"Starting data collection between stations:")
    for locations in stations:
        log(f" - {" and ".join(locations)}")
    trains = getAllTrains(stations)
    pollPositions(stations, trains)

def getAllTrains(stations: List[List[str]]) -> List[List[int]]:
    """
    Get the trains (identified by OperationalTrainNumber) for all
    station-lists and save them in the corresponding data folders.
    """
    result = []
    for locations in stations:
        trains = getTrains(*locations)
        result.append(trains)
        saveTrains(f"{DATA_FOLDER_DIR}/trains_{"_".join(locations)}.txt", trains)
    return result

def pollPositions(stations: List[List[str]], trains: List[List[int]]) -> None:
    """
    Endlessly poll the positions of the given trains and stores it
    to database. 
    """
    # Setup SQLite databases
    log("Setting up the databases...")
    conns = []
    for locations in stations:
        conns.append(sqlite3.connect(f"{DATA_FOLDER_DIR}/db_{"_".join(locations)}.sqlite3"))
        conn = conns[-1]
        cur = conn.cursor()
        cur.execute("""CREATE TABLE timestamps (
                    operationalTrainNumber INTEGER,
                    journeyNumber INTEGER,
                    receivedTime REAL, 
                    modifiedTime REAL, 
                    measuredTime REAL,
                    SWEREF99TM_1 INTEGER,
                    SWEREF99TM_2 INTEGER,
                    WGS84_1 REAL,
                    WGS84_2 REAL,
                    bearing INTEGER,
                    speed INTEGER
                    )""")
        conn.commit()
    
    # Reverse lookup data structure for train id -> route id
    trainMap = {}
    for id, trainList in enumerate(trains):
        for train in trainList:
            trainMap.setdefault(train, []).append(id)
    
    # Start polling
    headers = {
        "Content-Type": "application/xml"
    }
    processedRequests = 0
    lastChangeID = 0
    log("Starting pollPositions...")
    while True:
        try:
            req = f"""
            <REQUEST>
                <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
                <QUERY changeid="{lastChangeID}" objecttype="TrainPosition" namespace="järnväg.trafikinfo" schemaversion="1.1" limit="10000">
                <FILTER>
                    <AND>
                        <EQ name="Status.Active" value="true" />
                        <OR>
                            {"\n".join([
                                f'<EQ name="Train.OperationalTrainNumber" value="{trainNumber}" />' for trainList in trains for trainNumber in trainList
                            ])}
                        </OR>
                    </AND>
                </FILTER>
                </QUERY>
            </REQUEST>
            """
            resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
            obj = resp.json()
            data = obj["RESPONSE"]["RESULT"][0]
            if lastChangeID == 0:
                # Skip first pass, ignore potential junk data
                lastChangeID = int(data["INFO"]["LASTCHANGEID"])
                continue

            # Store to database
            for entry in data["TrainPosition"]:
                otn = int(entry["Train"]["OperationalTrainNumber"])
                processResponse([conns[routeNumber].cursor() for routeNumber in trainMap.get(otn)], entry)
            if len(data["TrainPosition"]) != 0:
                processedRequests += 1
                if processedRequests % 100 == 0:
                    log(f"Processed {processedRequests} requests...")

            # Commit database transactions and finalize
            for conn in conns:
                conn.commit()
            lastChangeID = int(data["INFO"]["LASTCHANGEID"])
        except Exception as e:
            log("Exception in pollPositions...")
            log(f"---- Reason:\n{e}")
            log(f"---- Traceback:\n{traceback.format_exc()}")
        time.sleep(1)

trainJourneyNumber = {}
trainLastSeen = {}
trainLastPositionSWEREF = {}
trainLastPositionWGS = {}
def processResponse(dbs, data):
    """
    Process the incoming data object for a train position response
    by inserting it into the databases.
    """
    # operationalTrainNumber, journeyNumber,
    # receivedTime, modifiedTime, measuredTime, 
    # SWEREF99TM_1, SWEREF99TM_2, WGS84_1, WGS84_2, 
    # bearing, speed
    global trainJourneyNumber
    global trainLastSeen
    global trainLastPositionSWEREF
    global trainLastPositionWGS
    try:
        operationalTrainNumber = int(data["Train"]["OperationalTrainNumber"])
        receivedTime = datetime.now().timestamp()
        modifiedTime = datetime.fromisoformat(data["ModifiedTime"]).timestamp()
        measuredTime = datetime.fromisoformat(data["TimeStamp"]).timestamp()
        if measuredTime - trainLastSeen.get(operationalTrainNumber, 0) > 3*60*60:
            trainJourneyNumber[operationalTrainNumber] = trainJourneyNumber.get(operationalTrainNumber, -1) + 1
        journeyNumber = trainJourneyNumber.get(operationalTrainNumber, 0)
        trainLastSeen[operationalTrainNumber] = measuredTime

        # Skip entirely if it is the same position as before
        sameSWEREF = data["Position"]["SWEREF99TM"] == trainLastPositionSWEREF.get(operationalTrainNumber)
        sameWGS = data["Position"]["WGS84"] == trainLastPositionWGS.get(operationalTrainNumber)
        if sameSWEREF and sameWGS:
            return
        elif sameSWEREF or sameWGS:
            log(f"Only same {"SWEREF" if sameSWEREF else "WGS"} position for train {operationalTrainNumber}. Proceeding...")

        sweref = wkt.loads(data["Position"]["SWEREF99TM"])
        SWEREF99TM_1 = sweref["coordinates"][0]
        SWEREF99TM_2 = sweref["coordinates"][1]
        wgs = wkt.loads(data["Position"]["WGS84"])
        WGS84_1 = wgs["coordinates"][0]
        WGS84_2 = wgs["coordinates"][1]
        trainLastPositionSWEREF[operationalTrainNumber] = data["Position"]["SWEREF99TM"]
        trainLastPositionWGS[operationalTrainNumber] = data["Position"]["WGS84"]

        bearing = int(data.get("Bearing") or -1)
        speed = data.get("Speed")

        for db in dbs:
            db.execute("INSERT INTO timestamps VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                        (operationalTrainNumber, journeyNumber,
                        receivedTime, modifiedTime, measuredTime,
                        SWEREF99TM_1, SWEREF99TM_2, WGS84_1, WGS84_2,
                        bearing, speed))
    except Exception as e: 
        log(f"FATAL - Couldn't process data response entry:\n{json.dumps(data, indent=2)}")
        log(f"---- Reason:\n{e}")
        log(f"---- Traceback:\n{traceback.format_exc()}")

def main():
    createDataFolder()
    stations = []
    i = 1
    while True:
        print(f"------ Route {i} (press Enter to finish) ------")
        j = 1
        route = []
        while True:
            station = input(f"Station {j} (code): ")
            if station == "":
                break
            j += 1
            route.append(station)
        if len(route) == 0:
            break
        i += 1
        stations.append(route)
    fetchPositions(stations)

if __name__ == '__main__':
    main()
