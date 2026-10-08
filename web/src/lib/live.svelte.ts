import type { LiveMessage, ModelStatus } from "../../../server/live-messages";

const MAX_RETRY_DELAY_MS = 10_000;

export function connectLive() {
  const live = $state({
    drawings: 0,
    model: null as ModelStatus | null,
  });
  let retryDelay = 1000;

  function apply(message: LiveMessage) {
    if (message.type === "snapshot") {
      live.drawings = message.drawings;
      live.model = message.model;
    } else if (message.type === "drawings") {
      live.drawings = message.drawings;
    } else {
      live.model = message.model;
    }
  }

  function connect() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${location.host}/live`);
    socket.onopen = () => {
      retryDelay = 1000;
    };
    socket.onmessage = (event) => apply(JSON.parse(event.data));
    socket.onclose = () => {
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY_MS);
    };
  }

  connect();
  return live;
}
