import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { connectWs } from "../ws.js";

export default function MarketList() {
  const [markets, setMarkets] = useState([]);
  const [arb, setArb] = useState({}); // ticker -> {roi, ts}
  const [pos, setPos] = useState({}); // ticker -> {roi, ts}
  const [sort, setSort] = useState({ key: "hit", dir: "asc" }); // hit|roi|ts

  const formatTsEastern = (ts) => {
    if (!ts) return "-";
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return "-";
    // Convert to America/New_York (handles EST/EDT automatically)
    const ny = new Date(
      d.toLocaleString("en-US", { timeZone: "America/New_York" })
    );
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(ny.getMonth() + 1)}/${pad(ny.getDate())}/${ny.getFullYear()} ${pad(ny.getHours())}:${pad(ny.getMinutes())}:${pad(ny.getSeconds())}`;
  };

  useEffect(() => {
    const ws = connectWs((msg) => {
      if (msg.type === "initial") {
        setMarkets(msg.markets || []);
        const initArb = {};
        const initPos = {};
        for (const m of msg.markets || []) {
          if (m.arb) initArb[m.kalshi_ticker] = m.arb;
          if (m.pos_roi) initPos[m.kalshi_ticker] = m.pos_roi;
        }
        setArb(initArb);
        setPos(initPos);
      }

      if (msg.type === "market_added") {
        setMarkets((prev) => {
          const exists = prev.some((p) => p.kalshi_ticker === msg.kalshi_ticker);
          if (exists) return prev;
          return [...prev, {
            kalshi_ticker: msg.kalshi_ticker,
            poly_yes_asset: msg.poly_yes_asset,
            poly_no_asset: msg.poly_no_asset,
            arb: null,
            pos_roi: null
          }].sort((a,b) => a.kalshi_ticker.localeCompare(b.kalshi_ticker));
        });
      }

      if (msg.type === "roi_positive") {
        setPos((prev) => ({
          ...prev,
          [msg.kalshi_ticker]: { roi: msg.roi, ts: msg.ts }
        }));

        setArb((prev) => {
          const next = { ...prev };
          if (msg.hit_target) {
            next[msg.kalshi_ticker] = { roi: msg.roi, ts: msg.ts };
          } else {
            delete next[msg.kalshi_ticker];
          }
          return next;
        });
      }

      if (msg.type === "arb_hit") {
        setArb((prev) => ({
          ...prev,
          [msg.kalshi_ticker]: { roi: msg.roi, ts: msg.ts }
        }));
      }
    });

    return () => ws.close();
  }, []);

  const rows = useMemo(() => {
    const base = markets.map((m) => {
      const hit = arb[m.kalshi_ticker];
      const p = pos[m.kalshi_ticker];
      return {
        ...m,
        hitTarget: !!hit,
        roi: hit ? hit.roi : (p ? p.roi : null),
        ts: hit ? hit.ts : (p ? p.ts : null)
      };
    });

    const cmp = (a, b, key, dir) => {
      const mul = dir === "asc" ? 1 : -1;
      if (key === "hit") return mul * ((a.hitTarget === b.hitTarget) ? 0 : (a.hitTarget ? -1 : 1));
      if (key === "roi") {
        const ra = a.roi ?? -Infinity;
        const rb = b.roi ?? -Infinity;
        if (ra === rb) return 0;
        return mul * (ra > rb ? 1 : -1);
      }
      if (key === "ts") {
        const ta = a.ts ? new Date(a.ts).getTime() : -Infinity;
        const tb = b.ts ? new Date(b.ts).getTime() : -Infinity;
        if (ta === tb) return 0;
        return mul * (ta > tb ? 1 : -1);
      }
      // default: ticker
      return mul * a.kalshi_ticker.localeCompare(b.kalshi_ticker);
    };

    const sorted = [...base].sort((a, b) => {
      const primary = cmp(a, b, sort.key, sort.dir);
      if (primary !== 0) return primary;
      return cmp(a, b, "ticker", "asc");
    });

    return sorted;
  }, [markets, arb, pos, sort]);

  const toggleSort = (key) => {
    setSort((prev) => {
      if (prev.key === key) {
        return { key, dir: prev.dir === "asc" ? "desc" : "asc" };
      }
      return { key, dir: key === "hit" ? "asc" : "desc" };
    });
  };

  const sortIndicator = (key) => {
    if (sort.key !== key) return "";
    return sort.dir === "asc" ? " ▲" : " ▼";
  };

  return (
    <div className="card">
      <h2 className="h2">Markets</h2>

      <div className="table">
        <div className="tr th">
          <div>Kalshi Ticker</div>
          <button type="button" className="thBtn" onClick={() => toggleSort("hit")}>
            Hit Target{sortIndicator("hit")}
          </button>
          <button type="button" className="thBtn" onClick={() => toggleSort("roi")}>
            ROI %{sortIndicator("roi")}
          </button>
          <button type="button" className="thBtn" onClick={() => toggleSort("ts")}>
            Timestamp (ET){sortIndicator("ts")}
          </button>
        </div>

        {rows.map((r) => (
          <Link
            key={r.kalshi_ticker}
            to={`/market/${encodeURIComponent(r.kalshi_ticker)}`}
            className="tr linkrow"
          >
            <div className="mono">{r.kalshi_ticker}</div>
            <div className={r.hitTarget ? "hitYes" : "hitNo"}>
              {r.hitTarget ? "Yes" : "No"}
            </div>
            <div className={r.roi == null ? "roiEmpty" : "roiPositive"}>
              {r.roi == null ? "-" : r.roi.toFixed(3)}
            </div>
            <div className="mono tsText">{formatTsEastern(r.ts)}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
