import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { connectWs } from "../ws.js";
import OrderbookTable from "../ui/OrderbookTable.jsx";

export default function MarketDetail() {
  const { ticker } = useParams();

  const [markets, setMarkets] = useState([]);
  const [kalshiBooks, setKalshiBooks] = useState({});
  const [polyBooks, setPolyBooks] = useState({});
  const [arb, setArb] = useState({}); // ticker -> {roi, ts}
  const [pos, setPos] = useState({}); // ticker -> {roi, ts}

  const formatTsEastern = (ts) => {
    if (!ts) return "-";
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return "-";
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
        const ob = msg.orderbooks || {};
        setKalshiBooks(ob.kalshi || {});
        setPolyBooks(ob.poly || {});

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
          return [
            ...prev,
            {
              kalshi_ticker: msg.kalshi_ticker,
              poly_yes_asset: msg.poly_yes_asset,
              poly_no_asset: msg.poly_no_asset,
              arb: null,
              pos_roi: null,
            },
          ];
        });
      }

      if (msg.type === "orderbook_kalshi") {
        setKalshiBooks((prev) => ({
          ...prev,
          [msg.kalshi_ticker]: msg.book,
        }));
      }

      if (msg.type === "orderbook_poly") {
        setPolyBooks((prev) => ({
          ...prev,
          [msg.asset_id]: msg.book,
        }));
      }

      if (msg.type === "roi_positive") {
        setPos((prev) => ({
          ...prev,
          [msg.kalshi_ticker]: { roi: msg.roi, ts: msg.ts },
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
          [msg.kalshi_ticker]: { roi: msg.roi, ts: msg.ts },
        }));
      }
    });

    return () => ws.close();
  }, []);

  const match = useMemo(
    () => markets.find((m) => m.kalshi_ticker === ticker),
    [markets, ticker]
  );

  const polyYes = match?.poly_yes_asset || null;
  const polyNo = match?.poly_no_asset || null;

  const kalshiRaw = kalshiBooks[ticker] || null;
  const hit = arb[ticker];
  const p = pos[ticker];
  const roi = hit ? hit.roi : p ? p.roi : null;
  const ts = hit ? hit.ts : p ? p.ts : null;

  return (
    <div className="stack">
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <div className="label">Kalshi</div>
            <div className="mono big">{ticker}</div>
          </div>

          <div>
            <div className="label">Polymarket Assets</div>
            <div className="mono">{polyNo || "-" } (YES)</div>
            <div className="mono">{polyYes || "-" } (NO)</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div
          className="row"
          style={{ gap: "32px", flexWrap: "wrap", alignItems: "center" }}
        >
          <div className="mono">
            <strong>Hit Target:</strong> {hit ? "Yes" : "No"}
          </div>
          <div className="mono">
            <strong>ROI %:</strong> {roi == null ? "-" : roi.toFixed(3)}
          </div>
          <div className="mono">
            <strong>Timestamp (ET):</strong> {formatTsEastern(ts)}
          </div>
        </div>
      </div>

      <div className="grid2">
        <OrderbookTable
          title="Kalshi"
          yesBook={kalshiRaw?.yes || null}
          noBook={kalshiRaw?.no || null}
        />

        <OrderbookTable
          title="Polymarket"
          // Source feed appears inverted; treat polyNo as YES and polyYes as NO for UI consistency
          yesBook={polyNo ? polyBooks[polyNo] : null}
          noBook={polyYes ? polyBooks[polyYes] : null}
        />
      </div>
    </div>
  );
}
