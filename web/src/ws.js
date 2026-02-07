export function connectWs(onMessage) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host.includes(":5173")
    ? "localhost:8000"
    : window.location.host;

  const ws = new WebSocket(`${proto}://${host}/ws`);

  ws.onopen = () => {
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 15000);
  };

  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {
      // ignore
    }
  };

  return ws;
}
