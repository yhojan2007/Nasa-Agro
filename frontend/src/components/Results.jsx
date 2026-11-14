const LABELS = {
  sequia_severa: "Lluvia muy por debajo del histórico",
  deficit_lluvia: "Déficit de lluvia",
  normal: "Lluvia en el rango habitual",
  exceso_lluvia: "Exceso de lluvia",
  exceso_extremo: "Exceso extremo de lluvia",
  helada: "Mínimas bajo 2 °C",
  sin_historico: "Histórico insuficiente",
};

const TONE = {
  sequia_severa: "bad",
  deficit_lluvia: "warn",
  normal: "ok",
  exceso_lluvia: "warn",
  exceso_extremo: "bad",
  helada: "warn",
  sin_historico: "muted",
};

const MONTHS = [
  "",
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

export default function Results({ climate, result }) {
  if (!result) {
    return null;
  }
  return (
    <section className="results">
      <p className="aviso">{result.aviso}</p>
      {result.origen_clima === "fixture_demo" ? (
        <p className="banner">
          NASA no respondió a tiempo. Estos números salen de una consulta guardada para esta zona.
        </p>
      ) : null}
      <p className="meta">
        Fuente: {result.fuente}. Celda {result.punto.celda_nasa[0].toFixed(3)},{" "}
        {result.punto.celda_nasa[1].toFixed(3)}
        {result.punto.elevacion_m != null
          ? ` · altitud de la celda ${Math.round(result.punto.elevacion_m)} m`
          : ""}
        . La malla de POWER mide decenas de kilómetros: es la tendencia de la zona, no de tu parcela.
      </p>
      {result.alertas_mensaje ? <p className="banner">{result.alertas_mensaje}</p> : null}
      <div className="alerts">
        {result.alertas.map((alert) => (
          <article key={`${alert.tipo}-${alert.ventana_dias}`} className={`alert ${TONE[alert.tipo] || "muted"}`}>
            <h3>{LABELS[alert.tipo] || alert.tipo}</h3>
            <p>{alert.mensaje}</p>
          </article>
        ))}
      </div>
      {climate ? (
        <p className="meta">Periodo climatológico: {climate.periodo_climatologico}</p>
      ) : null}
      <div className="ranking">
        {result.recomendaciones.map((item) => (
          <article key={item.id} className="crop">
            <header>
              <h3>{item.cultivo}</h3>
              <strong>{item.puntaje}</strong>
            </header>
            <p className="tag">
              {item.etiqueta} · siembra en {MONTHS[item.mes_siembra]} · limita {item.factor_limitante}
              {item.ajuste_alerta ? " · con ajuste por la anomalía reciente" : ""}
            </p>
            <p>{item.explicacion}</p>
            {item.observaciones?.length ? (
              <ul>
                {item.observaciones.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
            {!item.validado ? <p className="meta">Requisitos marcados como ejemplo.</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
