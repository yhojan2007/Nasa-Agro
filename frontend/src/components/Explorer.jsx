const CATEGORIES = [
  ["frutas", "Frutas"],
  ["hortalizas", "Hortalizas"],
  ["cereales", "Cereales"],
  ["legumbres", "Legumbres"],
  ["tuberculos_raices", "Tubérculos y raíces"],
  ["oleaginosas", "Oleaginosas"],
  ["otros", "Otros"],
];

export default function Explorer({ category, onCategory, onRun, loading, result, error }) {
  return (
    <section className="panel">
      <h2>Explorar por categoría</h2>
      <p>Usa el mismo puntaje del ranking, solo que filtrado.</p>
      <label>
        Categoría
        <select value={category} onChange={(event) => onCategory(event.target.value)}>
          {CATEGORIES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={onRun} disabled={loading}>
        {loading ? "Calculando…" : "Ver viabilidad"}
      </button>
      {error ? <p className="banner">{error}</p> : null}
      {result ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cultivo</th>
                <th>Puntaje</th>
                <th>Etiqueta</th>
                <th>Limita</th>
              </tr>
            </thead>
            <tbody>
              {result.recomendaciones.length === 0 ? (
                <tr>
                  <td colSpan={4}>No hay cultivos de esa categoría en el catálogo inicial.</td>
                </tr>
              ) : (
                result.recomendaciones.map((item) => (
                  <tr key={item.id}>
                    <td>{item.cultivo}</td>
                    <td>{item.puntaje}</td>
                    <td>{item.etiqueta}</td>
                    <td>{item.factor_limitante}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
