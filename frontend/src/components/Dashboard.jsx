import { useEffect, useState } from "react";
import { fetchDistribution, fetchPosts, connectWebSocket } from "../services/api";
import DistributionChart from "./DistributionChart";
import SentimentChart from "./SentimentChart";
import LiveFeed from "./LiveFeed";
import MetricsCards from "./MetricsCards";

export default function Dashboard() {
  const [distribution, setDistribution] = useState({ positive: 0, negative: 0, neutral: 0 });
  const [posts, setPosts] = useState([]);
  const [trend, setTrend] = useState([]);
  const [status, setStatus] = useState("connecting");
  const [lastUpdate, setLastUpdate] = useState("--");

  useEffect(() => {
    // Initial REST fetch
    fetchDistribution().then(d => setDistribution(d.distribution));
    fetchPosts(20, 0).then(d => {
      setPosts(d.posts);

      // Simple trend aggregation (hour buckets)
      const buckets = {};
      d.posts.forEach(p => {
        const hour = new Date(p.created_at).getHours();
        buckets[hour] = buckets[hour] || { positive: 0, negative: 0, neutral: 0 };
        buckets[hour][p.sentiment.label]++;
      });

      const trendData = Object.keys(buckets).map(h => ({
        timestamp: `Hour ${h}`,
        ...buckets[h]
      }));
      setTrend(trendData);
    });

    // WebSocket (status only)
    const ws = connectWebSocket(
      (msg) => {
        setStatus("connected");
        setLastUpdate(new Date().toLocaleTimeString());
      },
      () => setStatus("disconnected"),
      () => setStatus("disconnected")
    );

    return () => ws.close();
  }, []);

  const total =
    distribution.positive +
    distribution.negative +
    distribution.neutral;

  return (
    <div className="dashboard">
      <header className="header">
        <h1>Real-Time Sentiment Analysis Dashboard</h1>
        <div className="status">
          Status: <span className={status}>{status}</span> | Last Update: {lastUpdate}
        </div>
      </header>

      <div className="grid">
        <DistributionChart data={distribution} />
        <LiveFeed posts={posts} />
      </div>

      <SentimentChart data={trend} />

      <MetricsCards metrics={{
        Total: total,
        Positive: distribution.positive,
        Negative: distribution.negative,
        Neutral: distribution.neutral
      }} />
    </div>
  );
}
