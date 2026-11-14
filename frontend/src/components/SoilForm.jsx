const EMPTY = {
  ph: "",
  textura: "",
  drenaje: "",
  materia_organica: "",
  n: "",
  p: "",
  k: "",
};

export { EMPTY as EMPTY_SOIL };

export default function SoilForm({ value, onChange, onSubmit, loading, rotation, error }) {
  function setField(name, fieldValue) {
    onChange({ ...value, [name]: fieldValue });
  }

  return (
    <section className="panel">
      <h2>Suelo y rotación</h2>
      <p>
        Opcional. Si no tienes un análisis, estima textura y drenaje a simple vista. El resultado es
        menos preciso y no reemplaza a un técnico.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label>
          pH
          <input
            inputMode="decimal"
            value={value.ph}
            onChange={(event) => setField("ph", event.target.value)}
          />
        </label>
        <label>
          Textura
          <select value={value.textura} onChange={(event) => setField("textura", event.target.value)}>
            <option value="">No sé</option>
            <option value="franco">Franco</option>
            <option value="arcilloso">Arcilloso</option>
            <option value="arenoso">Arenoso</option>
            <option value="organico">Orgánico</option>
          </select>
        </label>
        <label>
          Drenaje
          <select value={value.drenaje} onChange={(event) => setField("drenaje", event.target.value)}>
            <option value="">No sé</option>
            <option value="bueno">Bueno</option>
            <option value="pobre">Pobre</option>
            <option value="excesivo">Excesivo</option>
          </select>
        </label>
        <label>
          Materia orgánica (%)
          <input
            inputMode="decimal"
            value={value.materia_organica}
            onChange={(event) => setField("materia_organica", event.target.value)}
          />
        </label>
        {["n", "p", "k"].map((nutrient) => (
          <label key={nutrient}>
            {nutrient.toUpperCase()}
            <select value={value[nutrient]} onChange={(event) => setField(nutrient, event.target.value)}>
              <option value="">No sé</option>
              <option value="bajo">Bajo</option>
              <option value="medio">Medio</option>
              <option value="alto">Alto</option>
            </select>
          </label>
        ))}
        <button type="submit" disabled={loading}>
          {loading ? "Recalculando…" : "Recalcular con este suelo"}
        </button>
      </form>
      {error ? <p className="banner">{error}</p> : null}
      {rotation ? (
        <div>
          <p>{rotation.mensaje}</p>
          <ol>
            {rotation.pasos.map((step) => (
              <li key={step.orden}>
                <strong>{step.cultivo}</strong> en el mes {step.mes_siembra}, puntaje {step.puntaje}.{" "}
                {step.motivo}
              </li>
            ))}
          </ol>
          {rotation.observaciones.map((note) => (
            <p key={note}>{note}</p>
          ))}
          <p className="aviso">{rotation.aviso}</p>
        </div>
      ) : null}
    </section>
  );
}
