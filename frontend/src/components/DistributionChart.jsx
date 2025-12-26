import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

const COLORS = {
  positive: "#10b981",
  negative: "#ef4444",
  neutral: "#6b7280",
};

export default function DistributionChart({ data }) {
  const total = data.positive + data.negative + data.neutral;

  if (total === 0) {
    return <p>No sentiment data available</p>;
  }

  const chartData = Object.keys(data)
    .filter(k => data[k] > 0)
    .map(k => ({
      name: k,
      value: data[k],
      percentage: ((data[k] / total) * 100).toFixed(2),
    }));

  return (
    <div className="card">
      <h3>Sentiment Distribution</h3>
      <PieChart width={300} height={250}>
        <Pie data={chartData} dataKey="value" nameKey="name">
          {chartData.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </div>
  );
}
