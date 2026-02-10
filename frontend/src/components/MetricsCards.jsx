export default function MetricsCards({ metrics }) {
  return (
    <div className="metrics">
      {Object.entries(metrics).map(([k, v]) => (
        <div key={k} className="card">
          <h3>{k}</h3>
          <p>{v}</p>
        </div>
      ))}
    </div>
  );
}
