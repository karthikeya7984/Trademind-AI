"use client";
import { ResponsiveContainer, LineChart, Line, Tooltip } from "recharts";

interface Props {
  data: Array<{ close: number }>;
  color?: string;
}

export default function StockMiniChart({ data, color = "#00ff88" }: Props) {
  const chartData = data?.slice(-30).map((d, i) => ({ i, v: d.close })) || [];
  return (
    <ResponsiveContainer width="100%" height={50}>
      <LineChart data={chartData}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
        <Tooltip contentStyle={{ display: "none" }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
