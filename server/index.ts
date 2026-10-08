import { mkdirSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { parseDrawing } from "./drawing";
import type { LiveMessage, ModelStatus } from "./live-messages";
import { watchModelStatus } from "./model-status";
import { createRateLimiter } from "./rate-limit";
import { openStore } from "./store";

const HOST = process.env.HOST ?? "127.0.0.1";
const PORT = Number(process.env.PORT ?? 3000);
const DATA_DIR = resolve(process.env.DATA_DIR ?? join(import.meta.dir, "..", "data"));
const WEB_DIR = resolve(import.meta.dir, "..", "web", "dist");
const IDIOT_DRAWING_PATH = join(DATA_DIR, "idiot.png");

const SUBMISSIONS_PER_HOUR = 120;
const HOUR_MS = 60 * 60 * 1000;
const LIVE_TOPIC = "live";

mkdirSync(DATA_DIR, { recursive: true });
const store = openStore(join(DATA_DIR, "organic-idiot.db"));
const limiter = createRateLimiter(SUBMISSIONS_PER_HOUR, HOUR_MS);
setInterval(() => limiter.sweep(), 10 * 60 * 1000);

let model: ModelStatus | null = null;

function publish(message: LiveMessage) {
  server.publish(LIVE_TOPIC, JSON.stringify(message));
}

const notFound = () => new Response("Not Found", { status: 404 });

async function serveFile(path: string, headers?: HeadersInit) {
  const file = Bun.file(path);
  return (await file.exists()) ? new Response(file, { headers }) : notFound();
}

const server = Bun.serve({
  hostname: HOST,
  port: PORT,
  maxRequestBodySize: 256 * 1024,

  routes: {
    "/live": (request, server) =>
      server.upgrade(request) ? undefined : new Response("WebSocket 연결이 필요합니다.", { status: 426 }),

    "/api/drawings": {
      async POST(request, server) {
        // 로컬에서만 열리므로 Cloudflare Tunnel이 넘겨준 방문자 주소를 신뢰
        const address = request.headers.get("cf-connecting-ip") ?? server.requestIP(request)?.address ?? "unknown";
        const limit = limiter.take(address);
        if (!limit.allowed) {
          return Response.json(
            { error: `1시간에 ${SUBMISSIONS_PER_HOUR}장까지 제출할 수 있어요.`, retryAt: limit.retryAt },
            { status: 429 },
          );
        }

        const body = await request.json().catch(() => null);
        const result = parseDrawing(body);
        if (!result.ok) return Response.json({ error: result.error }, { status: 400 });

        store.addDrawing(result.drawing);
        publish({ type: "drawings", drawings: store.countDrawings() });
        return Response.json({ ok: true }, { status: 201 });
      },
    },

    "/idiot.png": () => serveFile(IDIOT_DRAWING_PATH, { "Cache-Control": "no-cache" }),
  },

  fetch(request) {
    const { pathname } = new URL(request.url);
    const filePath = resolve(WEB_DIR, pathname === "/" ? "index.html" : `.${pathname}`);
    if (!filePath.startsWith(WEB_DIR + sep)) return notFound();
    return serveFile(filePath);
  },

  websocket: {
    open(socket) {
      socket.subscribe(LIVE_TOPIC);
      const snapshot: LiveMessage = { type: "snapshot", drawings: store.countDrawings(), model };
      socket.send(JSON.stringify(snapshot));
    },
    message() {},
  },
});

watchModelStatus(join(DATA_DIR, "status.json"), (status) => {
  model = status;
  publish({ type: "model", model });
});

console.log(`유기농 멍청이 서버: http://${HOST}:${PORT} (데이터: ${DATA_DIR})`);
