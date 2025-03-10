import os
from dotenv import load_dotenv
import requests

load_dotenv("../.env")
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

def getStations(filter):
    headers = {
        "Content-Type": "application/xml"
    }
    req = f"""
    <REQUEST>
        <LOGIN authenticationkey="{TRAFIKVERKET_API_KEY}"/>
        <QUERY objecttype="TrainStation" namespace="rail.infrastructure" schemaversion="1.5" limit="10000">
        <FILTER>
        </FILTER>
        </QUERY>
    </REQUEST>
    """
    resp = requests.post(TRAFIKVERKET_URL, data = req, headers = headers)
    obj = resp.json()
    arr = obj["RESPONSE"]["RESULT"][0]["TrainStation"]
    # print(json.dumps(arr, indent=2, ensure_ascii=False))
    stations = []
    filter = filter.lower()
    for s in arr:
        signature = s.get("LocationSignature")
        locationName = s.get("OfficialLocationName")
        if filter in signature.lower() or filter in locationName.lower():
            stations.append((signature, locationName))
    return stations

def main():
    filter = input("Search for station: ")
    stations = getStations(filter)
    for signature, locationName in stations:
        print(f"{signature} - {locationName}")

if __name__ == '__main__':
    main()
