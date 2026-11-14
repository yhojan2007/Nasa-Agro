import { useEffect } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

const markerIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function ClickCatcher({ onPick }) {
  useMapEvents({
    click(event) {
      onPick({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
  });
  return null;
}

function FlyTo({ point }) {
  const map = useMap();
  useEffect(() => {
    if (point) {
      map.flyTo([point.lat, point.lon], Math.max(map.getZoom(), 7));
    }
  }, [point, map]);
  return null;
}

export default function MapView({ point, onPick }) {
  return (
    <MapContainer center={[-17.4, -65.5]} zoom={5} className="map" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickCatcher onPick={onPick} />
      <FlyTo point={point} />
      {point ? <Marker position={[point.lat, point.lon]} icon={markerIcon} /> : null}
    </MapContainer>
  );
}
