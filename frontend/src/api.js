const BASE = import.meta.env.VITE_API_URL ?? "";

async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detalle || body.detail || "No se pudo completar la consulta.");
  }
  return body;
}

export function getClimate(lat, lon) {
  return request(`/api/climate?lat=${lat}&lon=${lon}`);
}

export function recommend(payload) {
  return request("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function explore(payload) {
  return request("/api/explore", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function rotate(payload) {
  return request("/api/rotation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function searchPlace(query) {
  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("q", query);
  url.searchParams.set("limit", "5");
  const response = await fetch(url, { headers: { "Accept-Language": "es" } });
  if (!response.ok) {
    throw new Error("No se pudo buscar ese lugar.");
  }
  return response.json();
}
