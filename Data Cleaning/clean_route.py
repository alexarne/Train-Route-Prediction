import json
import sys

def load_geojson(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data

def find_starting_lines(features, start_point):
    starting_lines = []
    for feature in features:
        coordinates = feature['geometry']['coordinates']
        if coordinates[0] == start_point or coordinates[-1] == start_point:
            starting_lines.append(feature)
    return starting_lines

def traverse_graph(features, start_point):
    path = [start_point]
    current_point = start_point

    while True:
        possible_lines = find_starting_lines(features, current_point)

        if not possible_lines:
            print("No more lines to traverse from:", current_point)
            answer = input("Pick a new starting point to continue from? (y/n) ")
            if answer.startswith("y"):
                lon = float(input("Enter starting longitude: "))
                lat = float(input("Enter starting latitude: "))
                current_point = [lon, lat]
                path.append(current_point)
                continue
            else:
                break

        choice = 0
        if len(possible_lines) > 1:
            print("Multiple lines found. Choose one:")
            for i, line in enumerate(possible_lines):
                print(f"{i}: {line['id']}")
            answer = input("Enter the number of the chosen line (enter to abort): ")
            if answer == "":
                break
            choice = int(answer)
        
        chosen_line = possible_lines[choice]
        coordinates = chosen_line['geometry']['coordinates']
        if coordinates[-1] == current_point:
            coordinates.reverse()
        path = path + coordinates[1:]
        next_point = coordinates[-1]
        
        # Remove the used feature to avoid cycles
        features.remove(chosen_line)
        
        current_point = next_point

    return path

def writeToFile(path, location):
    with open(location, 'w') as file:
        json.dump(path, file, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <filename.geojson>")
        sys.exit(1)
    
    filename = sys.argv[1]
    geojson_data = load_geojson(filename)
    features = geojson_data['features']
    
    lon = float(input("Enter starting longitude: "))
    lat = float(input("Enter starting latitude: "))
    start_point = [lon, lat]
    
    path = traverse_graph(features, start_point)
    print("Traversal complete.")
    location = input("Save to file (default is ./cleaned-route.json): ")
    writeToFile(path, location if location != "" else "cleaned-route.json")

if __name__ == "__main__":
    main()
