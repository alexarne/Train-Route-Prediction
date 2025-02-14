import os
from dotenv import load_dotenv
import requests
import json
import sseclient
import datetime
import pytz

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
SJ_API_KEY = os.getenv("SJ_API_KEY")

def handlePositionData(data):
    print()
    print(f"AdvertisedTrainNumber {data["Train"]["AdvertisedTrainNumber"]}")
    print(f"Received at {data.get("ReceivedTime")}")
    print(f"Measurement {data.get("TimeStamp")}")
    print(f"Speed {data.get("Speed")}")
    print(f"Bearing {data.get("Bearing")}")

def getSSEURL(trainNumber):
    headers = {
        "Content-Type": "application/xml"
    }
    req = f"""
    <REQUEST>
        <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
        <QUERY sseurl="true" objecttype="TrainPosition" namespace="järnväg.trafikinfo" schemaversion="1.1" limit="10000">
        <FILTER>
            <AND>
                <EQ name="Status.Active" value="true" />
                <OR>
                    <EQ name="Train.JourneyPlanNumber" value="{trainNumber}" />
                </OR>
            </AND>
        </FILTER>
        </QUERY>
    </REQUEST>
    """
    resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
    obj = resp.json()
    print(json.dumps(obj, indent=2))
    data = obj["RESPONSE"]["RESULT"][0]
    now = datetime.datetime.now()
    receivedTime = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    print(f"Received at {receivedTime} measurement taken at {data["TrainPosition"][0]["TimeStamp"]}")

    return obj["RESPONSE"]["RESULT"][0]["INFO"]["SSEURL"]

def getPositions(SSEURL):
    while True:
        print("Starting streaming session...")
        session = requests.session()
        stream = session.get(SSEURL, stream=True)
        client = sseclient.SSEClient(stream)
        for event in client.events():
            obj = json.loads(event.data)
            print(json.dumps(obj, indent=2))
            data = obj["RESPONSE"]["RESULT"][0]
            now = datetime.datetime.now()
            receivedTime = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
            for train in data["TrainPosition"]:
                train["ReceivedTime"] = receivedTime
                handlePositionData(train)
    return 1

def main():
    #print("1) Trafikverket API       (Requires TRAFIKVERKET_API_KEY)")
    #print("2) SJ API                 (Requires SJ_API_KEY)")
    #mode = {
    #    "1": "Trafikverket",
    #    "2": "SJ"
    #}[input("Select endpoint: ")]
    trainNumber = input("Train number: ")

    SSEURL = getSSEURL(trainNumber)
    print(f"Obtained SSEURL")
    getPositions(SSEURL)

if __name__ == '__main__':
    main()

filters = """
<GT name='TimeStamp' value='$dateadd(-0.00:00:30)' />
<EQ name="Train.OperationalTrainNumber" value="2139" />
<EQ name="Status.Active" value="true" />
"""