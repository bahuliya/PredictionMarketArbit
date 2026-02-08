import React, { useMemo, useState } from "react";

function fmtMoney(n) {
  if (!Number.isFinite(n)) return "-";
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(2)}K`;
  return `$${n.toFixed(2)}`;
}

function fmtContracts(n) {
  if (!Number.isFinite(n)) return "-";
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function fmtPrice(p, isKalshi) {
  if (!Number.isFinite(p)) return "-";

  const isDollarInput = Math.abs(p) <= 1.5; // Polymarket sends dollars (0.xxx), Kalshi sends cents (xx)

  if (isKalshi) {
    // Kalshi feeds are already in cents; avoid interpreting small integers as dollars
    const cents = Math.round(p);
    return `${cents}\u00A2`;
  }

  // Polymarket: display in cents, preserving 0.1¢ (=$0.001) precision without rounding
  if (isDollarInput) {
    const centsTenths = Math.trunc(p * 1000) / 10; // dollars -> tenths of a cent, truncated
    const decimals = centsTenths % 1 === 0 ? 0 : 1;
    return `${centsTenths.toFixed(decimals)}\u00A2`;
  }

  // Fallback: if we ever receive cents here, keep one decimal
  const centsTrunc = Math.trunc(p * 10) / 10;
  const decimals = centsTrunc % 1 === 0 ? 0 : 1;
  return `${centsTrunc.toFixed(decimals)}\u00A2`;
}

function bidsDictToRows(bidsDict) {
  if (!bidsDict) return [];
  const rows = Object.entries(bidsDict)
    .map(([price, size]) => [Number(price), Number(size)])
    .filter(([price, size]) => Number.isFinite(price) && Number.isFinite(size));

  rows.sort((a, b) => b[0] - a[0]);
  return rows;
}

function dedupeRows(rows) {
  // Normalize numeric keys to avoid float string mismatches (e.g., 1 vs 1.0)
  const seen = new Set();
  const out = [];
  for (const [price, size] of rows) {
    const pKey = Number(price.toFixed(4)); // enough precision for cents and tenths of a cent
    const sKey = Number((Number.isFinite(size) ? size : 0).toFixed(4));
    const key = `${pKey}|${sKey}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push([price, size]);
  }
  return out;
}

function totalDollars(price, contracts) {
  if (!Number.isFinite(price) || !Number.isFinite(contracts)) return 0;
  const isDollar = Math.abs(price) <= 1.5;
  const dollars = isDollar ? price : price / 100;
  return dollars * contracts;
}

export default function OrderbookTable({ title, yesBook, noBook }) {
  const [tab, setTab] = useState("yes");
  const book = tab === "yes" ? yesBook : noBook;
  const isKalshi = title === "Kalshi";

  const view = useMemo(() => {
    if (!book) return { askRows: [], bidRows: [], maxBidSize: 1 };

    // Asks: Polymarket provides full ladders; Kalshi gives bestAsk + volume.
    let askRows = [];
    if (book.asks && Object.keys(book.asks).length > 0) {
      askRows = Object.entries(book.asks)
        .map(([price, size]) => [Number(price), Number(size)])
        .filter(([price, size]) => Number.isFinite(price) && Number.isFinite(size))
        .sort((a, b) => a[0] - b[0]); // lowest price first
    } else {
      const bestAsk = book.bestAsk;
      const bestAskVolume = book.bestAskVolume;
      if (bestAsk !== null && bestAsk !== undefined) {
        askRows = [[Number(bestAsk), Number(bestAskVolume || 0)]];
      }
    }

    const bidRows = bidsDictToRows(book.bids);

    let maxBidSize = 1;
    for (const [, size] of bidRows) {
      if (Number.isFinite(size) && size > maxBidSize) maxBidSize = size;
    }

    return { askRows, bidRows, maxBidSize };
  }, [book]);

  // At least 5 rows (pad blanks), otherwise show all (scroll handles height)
  const normalizeRows = (rows) => {
    if (rows.length < 5) {
      const blanks = Array.from({ length: 5 - rows.length }, () => [null, null]);
      return [...rows, ...blanks];
    }
    return rows;
  };

    const askRowsLimited = normalizeRows(dedupeRows(view.askRows));
    const bidRowsLimited = normalizeRows(dedupeRows(view.bidRows));

  return (
    <div className="obPanel">
      <div className="obPanelHead">
        <div className="obPanelTitle">{title}</div>
      </div>

      <div className="obTabBar">
        <button
          type="button"
          className={`obTabBtn ${tab === "yes" ? "active" : ""}`}
          onClick={() => setTab("yes")}
        >
          Trade Yes
        </button>
        <button
          type="button"
          className={`obTabBtn ${tab === "no" ? "active" : ""}`}
          onClick={() => setTab("no")}
        >
          Trade No
        </button>
      </div>

      <div className="obTable">
        <div className="obAsks">
          <div className="obHeaderLine">
            <div className="obSideTitle asks">Asks</div>
            <div className="obColPrice">Price</div>
            <div className="obColContracts">Contracts</div>
          </div>
          <div className="obRows asksScroll">
            {askRowsLimited.length === 0 ? (
              <div className="obEmptyRow">-</div>
            ) : (
              askRowsLimited.map(([p, s], idx) => (
                <div className="obRow askRow" key={`a-${idx}-${p ?? "blank"}`}>
                  <div className="obSpacer" />
                  <div className="obPrice ask">{p == null ? "-" : fmtPrice(p, isKalshi)}</div>
                  <div className="obContracts">{s == null ? "-" : fmtContracts(s)}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="obBids">
          <div className="obHeaderLine">
            <div className="obSideTitle bids">Bids</div>
            <div className="obColPrice">Price</div>
            <div className="obColContracts">Contracts</div>
          </div>
          <div className="obRows bidsScroll">
            {bidRowsLimited.length === 0 ? (
              <div className="obEmptyRow">-</div>
            ) : (
              bidRowsLimited.map(([p, s], idx) => (
                <div className="obRow bidRow" key={`b-${idx}-${p ?? "blank"}`}>
                  <div className="obSpacer" />
                  <div className="obPrice bid">{p == null ? "-" : fmtPrice(p, isKalshi)}</div>
                  <div className="obContracts">{s == null ? "-" : fmtContracts(s)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
