import { useState } from "react";
import { explore, getClimate, recommend, rotate, searchPlace } from "./api";
import About from "./components/About";
import ClimateChart from "./components/ClimateChart";
import Explorer from "./components/Explorer";
import MapView from "./components/MapView";
import Results from "./components/Results";
import SoilForm, { EMPTY_SOIL } from "./components/SoilForm";

const ZONES = [
  { nombre: "Cochabamba", lat: -17.39, lon: -66.16 },
  { nombre: "El Alto", lat: -16.5, lon: -68.15 },
  { nombre: "Santa Cruz", lat: -17.8, lon: -63.18 },
];

const MONTHS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

function soilPayload(form) {
  const payload = {};
  if (form.ph !== "") payload.ph = Number(form.ph);
  if (form.textura) payload.textura = form.textura;
  if (form.drenaje) payload.drenaje = form.drenaje;
  if (form.materia_organica !== "") payload.materia_organica = Number(form.materia_organica);
  if (form.n) payload.n = form.n;
  if (form.p) payload.p = form.p;
  if (form.k) payload.k = form.k;
  if (Object.values(payload).some((value) => typeof value === "number" && Number.isNaN(value))) {
    throw new Error("Revisa los números del suelo.");
  }
  return Object.keys(payload).length ? payload : null;
}

export default function App() {
  const [section, setSection] = useState("mapa");
  const [point, setPoint] = useState(null);
  const [mes, setMes] = useState("");
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [climate, setClimate] = useState(null);
  const [result, setResult] = useState(null);
  const [soil, setSoil] = useState(EMPTY_SOIL);
  const [rotation, setRotation] = useState(null);
  const [soilError, setSoilError] = useState("");
  const [soilLoading, setSoilLoading] = useState(false);
  const [category, setCategory] = useState("cereales");
  const [explored, setExplored] = useState(null);
  const [exploreError, setExploreError] = useState("");
  const [exploreLoading, setExploreLoading] = useState(false);

  async function run(nextPoint, nextMes = mes, nextSoil = soil) {
    setPoint(nextPoint);
    setLoading(true);
    setError("");
    setRotation(null);
    const payload = { lat: nextPoint.lat, lon: nextPoint.lon };
    if (nextMes) payload.mes_siembra = Number(nextMes);
    try {
      const soilBody = soilPayload(nextSoil);
      if (soilBody) payload.suelo = soilBody;
      const [weather, ranking] = await Promise.all([
        getClimate(nextPoint.lat, nextPoint.lon),
        recommend(payload),
      ]);
      setClimate(weather);
      setResult(ranking);
    } catch (err) {
      setClimate(null);
      setResult(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onSearch(event) {
    event.preventDefault();
    setError("");
    try {
      setPlaces(await searchPlace(query));
    } catch (err) {
      setPlaces([]);
      setError(err.message);
    }
  }

  function locate() {
    if (!navigator.geolocation) {
      setError("Este navegador no comparte la ubicación.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        run({ lat: position.coords.latitude, lon: position.coords.longitude });
      },
      () => setError("No se pudo leer tu ubicación."),
    );
  }

  async function onExplore() {
    if (!point) {
      setExploreError("Primero elige un punto en el mapa.");
      return;
    }
    setExploreLoading(true);
    setExploreError("");
    const payload = { lat: point.lat, lon: point.lon, categoria: category };
    if (mes) payload.mes_siembra = Number(mes);
    try {
      const soilBody = soilPayload(soil);
      if (soilBody) payload.suelo = soilBody;
      setExplored(await explore(payload));
    } catch (err) {
      setExplored(null);
      setExploreError(err.message);
    } finally {
      setExploreLoading(false);
    }
  }

  async function onSoil() {
    if (!point) {
      setSoilError("Primero elige un punto en el mapa.");
      return;
    }
    setSoilLoading(true);
    setSoilError("");
    try {
      const soilBody = soilPayload(soil);
      if (!soilBody) {
        throw new Error("Indica al menos un dato de suelo.");
      }
      const payload = { lat: point.lat, lon: point.lon, suelo: soilBody };
      if (mes) payload.mes_siembra = Number(mes);
      const [ranking, cycle] = await Promise.all([recommend(payload), rotate(payload)]);
      setResult(ranking);
      setRotation(cycle);
    } catch (err) {
      setSoilError(err.message);
    } finally {
      setSoilLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <p className="eyebrow">NASA POWER · EcoCrop</p>
        <h1>AgroNASA</h1>
        <p>Elige un punto y mira qué cultivos encajan con el clima de esa zona.</p>
      </header>
      <nav>
        {[
          ["mapa", "Mapa"],
          ["explorar", "Explorar"],
          ["suelo", "Suelo"],
          ["acerca", "Acerca de"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={section === id ? "active" : ""}
            onClick={() => setSection(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {section === "mapa" ? (
        <>
          <form className="search" onSubmit={onSearch}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar un lugar"
              aria-label="Buscar un lugar"
            />
            <button type="submit">Buscar</button>
            <button type="button" onClick={locate}>
              Usar mi ubicación
            </button>
          </form>
          {places.length ? (
            <ul className="places">
              {places.map((place) => (
                <li key={place.place_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPlaces([]);
                      run({ lat: Number(place.lat), lon: Number(place.lon) });
                    }}
                  >
                    {place.display_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <div className="zones">
            {ZONES.map((zone) => (
              <button key={zone.nombre} type="button" onClick={() => run(zone)}>
                {zone.nombre}
              </button>
            ))}
          </div>
          <MapView point={point} onPick={(next) => run(next)} />
          <label className="month">
            Mes de siembra
            <select
              value={mes}
              onChange={(event) => {
                const next = event.target.value;
                setMes(next);
                if (point) run(point, next);
              }}
            >
              <option value="">El mejor mes para cada cultivo</option>
              {MONTHS.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          {loading ? (
            <p className="banner">
              Consultando NASA POWER. La primera vez puede tardar un minuto porque compara el
              histórico del punto.
            </p>
          ) : null}
          {error ? <p className="banner">{error}</p> : null}
          {climate ? <ClimateChart months={climate.meses} /> : null}
          <Results climate={climate} result={result} />
        </>
      ) : null}

      {section === "explorar" ? (
        <Explorer
          category={category}
          onCategory={setCategory}
          onRun={onExplore}
          loading={exploreLoading}
          result={explored}
          error={exploreError}
        />
      ) : null}

      {section === "suelo" ? (
        <SoilForm
          value={soil}
          onChange={setSoil}
          onSubmit={onSoil}
          loading={soilLoading}
          rotation={rotation}
          error={soilError}
        />
      ) : null}

      {section === "acerca" ? <About /> : null}
    </div>
  );
}
