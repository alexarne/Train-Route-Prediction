import os
from dotenv import load_dotenv
import requests
import json

def main():
    load_dotenv("../.env")
    API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
    print("ll")
    print(API_KEY)

    url = "https://api.trafikinfo.trafikverket.se/v2/data.json"
    headers = {
        "Content-Type": "application/xml"
    }
    req = f"""
    <REQUEST>
        <LOGIN authenticationkey="{API_KEY}"/>
        <QUERY objecttype="TrainPosition" namespace="järnväg.trafikinfo" schemaversion="1.1" limit="10000">
        <FILTER>
            <GT name='TimeStamp' value='$dateadd(-0.00:10:25)' />
        </FILTER>
        </QUERY>
    </REQUEST>
    """
    resp = requests.post(url, data = req, headers=headers)
    obj = resp.json()
    print(json.dumps(obj, indent=2))
    print("--------NEW")
    print(obj["RESPONSE"]["RESULT"])
    print(len(obj["RESPONSE"]["RESULT"][0]["TrainPosition"]))

if __name__ == '__main__':
    main()

filters = """
<GT name='TimeStamp' value='$dateadd(-0.00:00:30)' />
<EQ name="Train.OperationalTrainNumber" value="2139" />
"""