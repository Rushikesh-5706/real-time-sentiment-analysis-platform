export default function LiveFeed({ posts }) {
  return (
    <div className="card">
      <h3>Recent Posts</h3>
      <div style={{ maxHeight: 250, overflowY: "auto" }}>
        {posts.map(p => (
          <div key={p.post_id} style={{ marginBottom: 10 }}>
            <strong>{p.sentiment.label}</strong>: {p.content.slice(0, 80)}
          </div>
        ))}
      </div>
    </div>
  );
}
