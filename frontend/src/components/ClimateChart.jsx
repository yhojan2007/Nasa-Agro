import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const NAMES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function ClimateChart({ months }) {
  const data = months.map((month) => ({
    mes: NAMES[month.mes],
    lluvia: month.precip_mm,
    temperatura: month.t2m,
  }));
  return (
    <div className="chart-wrap">
      <h3>Clima medio del punto</h3>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data}>
          <CartesianGrid stroke="#e6e0d4" />
          <XAxis dataKey="mes" />
          <YAxis yAxisId="rain" unit=" mm" width={64} />
          <YAxis yAxisId="temp" orientation="right" unit=" °C" width={48} />
          <Tooltip />
          <Legend />
          <Bar yAxisId="rain" dataKey="lluvia" name="Lluvia (mm)" fill="#1d6b45" />
          <Line
            yAxisId="temp"
            dataKey="temperatura"
            name="Temperatura (°C)"
            stroke="#b85c38"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
