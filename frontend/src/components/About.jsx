export default function About() {
  return (
    <section className="panel about">
      <h2>Cómo está hecha la recomendación</h2>
      <p>
        AgroNASA lee el clima de <strong>NASA POWER</strong> (comunidad agroclimatológica) para la
        celda de 0.5° × 0.625° donde cae el punto. Con esa climatología mensual puntúa cada cultivo
        con la curva trapezoidal de EcoCrop: 0 fuera de los límites absolutos, 1 dentro del óptimo.
        El puntaje es una media geométrica. Si la temperatura, la lluvia o la helada de un cultivo
        sensible valen 0, el puntaje queda en 0.
      </p>
      <p>
        Los rangos de maíz, papa, quinua, haba, frijol, soya, arroz, tomate, cebolla y yuca están
        copiados de FAO EcoCrop (copia OpenCLIM). La lluvia de la ficha se compara con la suma de la
        ventana de ciclo. <code>tolerancia_sequia</code> no está en esa ficha y no se inventó: el
        ajuste por sequía solo corre si ese dato existe.
      </p>
      <h3>Qué no promete</h3>
      <ul>
        <li>No es un pronóstico. POWER es reanálisis, con unos días de retraso.</li>
        <li>La alerta dice si el periodo reciente fue más seco o más frío que su propio histórico.</li>
        <li>La resolución no ve el microclima de un valle o una ladera.</li>
        <li>
          El segundo dataset (NDVI de MODIS, SMAP o GPM) quedó fuera: MODIS pide cuenta Earthdata y
          no hay una serie citada para incrustar sin inventar números.
        </li>
      </ul>
      <p className="aviso">Recomendación orientativa; consulta a un técnico local.</p>
    </section>
  );
}
