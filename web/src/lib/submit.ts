import type { Stroke } from "../../../server/drawing";
import { formatTime } from "./format";

export type SubmitResult = { ok: true } | { ok: false; message: string };

export async function submitDrawing(keywordId: string, strokes: Stroke[]): Promise<SubmitResult> {
  let response: Response;
  try {
    response = await fetch("/api/drawings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywordId, strokes }),
    });
  } catch {
    return { ok: false, message: "서버에 연결하지 못했어요. 그림은 그대로 있으니 다시 제출해 주세요." };
  }
  if (response.ok) return { ok: true };

  const body = (await response.json().catch(() => ({}))) as { error?: string; retryAt?: number };
  if (response.status === 429 && body.retryAt) {
    return { ok: false, message: `${body.error} ${formatTime(body.retryAt)}부터 다시 제출할 수 있어요.` };
  }
  return { ok: false, message: body.error ?? `제출하지 못했어요. (오류 ${response.status})` };
}
