import sqlite3
import os
import sys
import datetime
import webbrowser

def unix_to_human_time(unix_timestamp):
    return datetime.datetime.fromtimestamp(unix_timestamp, datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')

def generate_map(database_path):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Fetch unique train numbers
    cursor.execute("SELECT DISTINCT operationalTrainNumber FROM timestamps ORDER BY operationalTrainNumber")
    train_numbers = [row[0] for row in cursor.fetchall()]

    if not train_numbers:
        print("No train data found in the database.")
        return

    # Get train data
    cursor.execute("SELECT operationalTrainNumber, journeyNumber, receivedTime, measuredTime, WGS84_1, WGS84_2 FROM timestamps ORDER BY operationalTrainNumber, journeyNumber, receivedTime")
    train_data = cursor.fetchall()
    conn.close()

    # Structure data
    train_routes = {}
    for train, journey, received_time, measured_time, lon, lat in train_data:
        if train not in train_routes:
            train_routes[train] = {}
        if journey not in train_routes[train]:
            train_routes[train][journey] = []
        train_routes[train][journey].append({
            'lat': lat,
            'lon': lon,
            'human_received_time': unix_to_human_time(received_time),
            'measured_time': unix_to_human_time(measured_time),
            'journey': journey
        })

    # Generate HTML
    html_path = "train_map.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Train Route Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <style>
                body, html {{ height: 100%; margin: 0; }}
                #map {{ height: 100%; width: 100%; }}
                #infoBox {{ position: absolute; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 5px; z-index: 1000; }}
                #controls {{ position: absolute; top: 10px; right: 10px; background: white; padding: 10px; border-radius: 5px; z-index: 1000; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <div id="infoBox">Press → to start animation</div>
            <div id="controls">
                <label for="trainSelect">Train:</label>
                <select id="trainSelect" onchange="updateTrain()">
                    {''.join(f'<option value="{train}">{train}</option>' for train in train_routes)}
                </select>
                <label for="journeySelect">Journey:</label>
                <select id="journeySelect" onchange="updateJourney()"></select>
            </div>
            <script>
                var map = L.map('map').setView([59.8, 17.7], 12);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }}).addTo(map);
                var markers = [];
                var trainRoutes = {train_routes};
                var selectedTrain = Object.keys(trainRoutes)[0];
                var selectedJourney = null;
                var markerIndex = 0;
                var markerRange = [];

                function updateTrain() {{
                    selectedTrain = document.getElementById("trainSelect").value;
                    updateJourneyList();
                }}

                function updateJourneyList() {{
                    var journeySelect = document.getElementById("journeySelect");
                    journeySelect.innerHTML = "";
                    Object.keys(trainRoutes[selectedTrain]).forEach(journey => {{
                        journeySelect.innerHTML += `<option value="${{journey}}">${{journey}}</option>`;
                    }});
                    selectedJourney = Object.keys(trainRoutes[selectedTrain])[0];
                    resetAnimation();
                }}

                function updateJourney() {{
                    selectedJourney = document.getElementById("journeySelect").value;
                    resetAnimation();
                }}

                function resetAnimation() {{
                    markerRange = [];
                    markerIndex = 0;
                    clearMarkers();
                    nextMarker();
                }}

                function clearMarkers() {{
                    markers.forEach(marker => map.removeLayer(marker));
                    markers = [];
                }}

                function nextMarker() {{
                    if (selectedTrain && selectedJourney) {{
                        let route = trainRoutes[selectedTrain][selectedJourney];
                        if (markerIndex < route.length) {{
                            markerRange.push(route[markerIndex]);
                            markerIndex++;
                            updateMarkers();
                        }} else {{
                            // Move to next journey number
                            let availableJourneys = Object.keys(trainRoutes[selectedTrain]).length;
                            if (parseInt(selectedJourney) < availableJourneys) {{
                                selectedJourney = "" + (parseInt(selectedJourney)+1)
                                markerIndex = 0;
                                document.getElementById("journeySelect").value = selectedJourney;
                                nextMarker();
                            }}
                        }}
                    }}
                }}

                function previousMarker() {{
                    if (markerRange.length > 1) {{
                        markerRange.pop();
                        markerIndex--;
                        if (markerIndex < 1 && parseInt(selectedJourney) > 1) {{
                            selectedJourney = "" + (parseInt(selectedJourney)-1)
                            markerIndex = trainRoutes[selectedTrain][selectedJourney].length
                            document.getElementById("journeySelect").value = selectedJourney;
                        }}
                        updateMarkers();
                    }}
                }}

                function updateMarkers() {{
                    clearMarkers();
                    for (let i = 0; i < markerRange.length; i++) {{
                        let point = markerRange[i];
                        let isLastMarker = (i === markerRange.length - 1);
                        let marker = L.circleMarker([point.lat, point.lon], {{
                            radius: isLastMarker ? 10 : 7,
                            fillColor: isLastMarker ? "#FFA500" : "#FF0000",
                            fillOpacity: isLastMarker ? 1.0 : 0.5,
                            color: isLastMarker ? "#CC8400" : "transparent",
                            weight: isLastMarker ? 2 : 0
                        }}).addTo(map);
                        markers.push(marker);
                    }}
                    if (markerRange.length > 0) {{
                        let lastPoint = markerRange[markerRange.length - 1];
                        document.getElementById('infoBox').innerHTML = `
                            <b>Time:</b> ${{lastPoint.human_received_time}} <br>
                            <b>Latitude:</b> ${{lastPoint.lat.toFixed(6)}} <br>
                            <b>Longitude:</b> ${{lastPoint.lon.toFixed(6)}} <br>
                            <b>Measured Time:</b> ${{lastPoint.measured_time}} <br>
                            <b>Journey:</b> ${{lastPoint.journey}}
                        `;
                        map.setView([lastPoint.lat, lastPoint.lon], 14);
                    }}
                }}
                
                document.addEventListener('keydown', (event) => {{
                    if (event.key === 'ArrowRight') nextMarker();
                    if (event.key === 'ArrowLeft') previousMarker();
                }});
                
                updateJourneyList();
            </script>
        </body>
        </html>
        """)
    print(f"Map generated: {html_path}")
    if input("Open the map? (y/n): ").strip().lower() == 'y':
        webbrowser.open(f'file://{os.path.abspath(html_path)}')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <database_path>")
    else:
        generate_map(sys.argv[1])