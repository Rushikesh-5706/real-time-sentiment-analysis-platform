import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from "recharts";

export default function SentimentChart({ data }) {
  if (!data.length) return <p>No trend data</p>;

  return (
    <div className="card">
      <h3>Sentiment Trend (Last 24 Hours)</h3>
      <LineChart width={600} height={250} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(t) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="positive" stroke="#10b981" />
        <Line type="monotone" dataKey="negative" stroke="#ef4444" />
        <Line type="monotone" dataKey="neutral" stroke="#6b7280" />
      </LineChart>
    </div>
  );
}
