import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timezone
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

def fetchPositions(stations: List[List[str]]) -> None:
    """
    Takes a list of station-couples, sets up the data directory
    and starts endlessly polling for the positional data of all
    trains moving between the station-couples.
    """
    log(f"Starting data collection between stations:")
    for s1, s2 in stations:
        log(f" - {s1} and {s2}")
    trains = getAllTrains(stations)
    pollPositions(stations, trains)

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

def getAllTrains(stations: List[List[str]]) -> List[List[int]]:
    """
    Get the trains (identified by OperationalTrainNumber) for all
    station couples and save them in the corresponding data folders.
    """
    result = []
    for locationSignature1, locationSignature2 in stations:
        trains = getTrains(locationSignature1, locationSignature2)
        result.append(trains)
        saveTrains(f"{DATA_FOLDER_DIR}/trains_{locationSignature1}_{locationSignature2}.txt", trains)
    return result

def pollPositions(stations: List[List[str]], trains: List[List[int]]) -> None:
    """
    
    """
    # Setup SQLite database
    conn = sqlite3.connect(f"{DATA_FOLDER_DIR}/db.sqlite3")
    cur = conn.cursor()
    cur.execute("CREATE TABLE route_map (routeNumber INTEGER PRIMARY KEY, name TEXT)")
    for id, (locationSignature1, locationSignature2) in enumerate(stations):
        cur.execute("INSERT INTO route_map VALUES (?, ?)", (id, f"{locationSignature1}_{locationSignature2}"))
    cur.execute("""CREATE TABLE timestamps (
                routeNumber INTEGER,
                operationalTrainNumber INTEGER,
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
    lastChangeID = 0
    try:
        while True:
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
            for entry in data["TrainPosition"]:
                for routeNumber in trainMap.get(entry["Train"]["OperationalTrainNumber"]):
                    processResponse(conn.cursor(), routeNumber, entry)
            if len(data["TrainPosition"]) != 0:
                log("Processed once...")

            conn.commit()
            lastChangeID = int(data["INFO"]["LASTCHANGEID"])
            time.sleep(1)
    except Exception as e:
        conn.close()
        log("Closing pollPositions...")
        log(f"---- Reason:\n{e}")
        log(f"---- Traceback:\n{traceback.format_exc()}")

def processResponse(db, routeNumber, data):
    """
    
    """
    # routeNumber, operationalTrainNumber,
    # receivedTime, modifiedTime, measuredTime, 
    # SWEREF99TM_1, SWEREF99TM_2, WGS84_1, WGS84_2, 
    # bearing, speed
    try:
        operationalTrainNumber = int(data["Train"]["OperationalTrainNumber"])
        receivedTime = time.time()
        modifiedTime = time.time()
        meaasuredTime = time.time()
        sweref = wkt.loads(data["Position"]["SWEREF99TM"])
        SWEREF99TM_1 = sweref["coordinates"][0]
        SWEREF99TM_2 = sweref["coordinates"][1]
        wgs = wkt.loads(data["Position"]["WGS84"])
        WGS84_1 = wgs["coordinates"][0]
        WGS84_2 = wgs["coordinates"][1]
        bearing = int(data.get("Bearing") or -1)
        speed = data.get("Speed")
        db.execute("INSERT INTO timestamps VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                    (routeNumber, operationalTrainNumber,
                     receivedTime, modifiedTime, meaasuredTime,
                     SWEREF99TM_1, SWEREF99TM_2, WGS84_1, WGS84_2,
                     bearing, speed))
    except Exception as e: 
        log(f"FATAL - Couldn't process data response entry:\n{json.dumps(data, indent=2)}")
        log(f"---- Reason:\n{e}")
        log(f"---- Traceback:\n{traceback.format_exc()}")

def main():
    # createDataFolder()
    # pollPositions([
    #     ["test1", "test2"],
    #     ["test13", "test24"],
    #     ["2", "qwdq"],
    #     ["32few", "d12"]
    # ], [
    #     [1293],
    #     [1293],
    #     [1293],
    #     [1293]
    # ])
    # return
    createDataFolder()
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
