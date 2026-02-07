import requests

# ----------- CONFIG ------------ #
OPENCAGE_API_KEY = "854266e4c8144bf8bab86fac628900e4"
# ------------------------------- #

def geocode(address):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={OPENCAGE_API_KEY}"
    r = requests.get(url)
    results = r.json()['results']
    if results:
        return results[0]['geometry']['lat'], results[0]['geometry']['lng']
    return None, None

def main():
    print("\n--- Enter locations (full address or landmark) ---")
    driver_loc = input("Ambulance (Driver) location: ")
    patient_loc = input("Patient location: ")
    hospital_loc = input("Hospital location: ")

    alat, alng = geocode(driver_loc)
    blat, blng = geocode(patient_loc)
    hlat, hlng = geocode(hospital_loc)

    print("\nCoordinates found:")
    print(f"Driver: {alat}, {alng}")
    print(f"Patient: {blat}, {blng}")
    print(f"Hospital: {hlat}, {hlng}")

    # ---- Generate HTML ----
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Ambulance Route Map</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
  <style>
    #map {{ height: 600px; width: 100%; }}
  </style>
</head>
<body>
  <h2>Ambulance Routing: Driver → Patient → Hospital</h2>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <script>
    var map = L.map('map').setView([{alat}, {alng}], 13);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
    var driver = L.marker([{alat}, {alng}], {{icon: L.icon({{iconUrl:'https://cdn-icons-png.flaticon.com/512/2983/2983810.png', iconSize:[36,36], iconAnchor:[18,36] }})}}).addTo(map).bindPopup('Ambulance Driver');
    var patient = L.marker([{blat}, {blng}], {{icon: L.icon({{iconUrl:'https://cdn-icons-png.flaticon.com/512/6877/6877471.png', iconSize:[36,36], iconAnchor:[18,36] }})}}).addTo(map).bindPopup('Patient');
    var hospital = L.marker([{hlat}, {hlng}], {{icon: L.icon({{iconUrl:'https://cdn-icons-png.flaticon.com/512/3757/3757965.png', iconSize:[36,36], iconAnchor:[18,36] }})}}).addTo(map).bindPopup('Hospital');
    var polyline = L.polyline(
      [
        [{alat}, {alng}],
        [{blat}, {blng}],
        [{hlat}, {hlng}]
      ],
      {{color: 'red', weight: 6}}
    ).addTo(map);
    map.fitBounds(polyline.getBounds());
  </script>
</body>
</html>
    """

    with open("route_map.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("\nMap generated! Open route_map.html in your browser.")

if __name__ == "__main__":
    main()
