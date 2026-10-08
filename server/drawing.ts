import keywords from "../keywords.json";

export type Point = [number, number];

// 좌표와 굵기 모두 캔버스 한 변 대비 비율(0에서 1)
export interface Stroke {
  width: number;
  points: Point[];
}

export interface Drawing {
  keywordId: string;
  strokes: Stroke[];
}

export type ParseResult = { ok: true; drawing: Drawing } | { ok: false; error: string };

export const PEN_WIDTH = { min: 0.004, max: 0.04, step: 0.002, initial: 0.016 } as const;

// 점이나 짧은 낙서 제출 방지용 최소 획 길이(캔버스 너비 단위)
export const MIN_INK_LENGTH = 1;

const MAX_STROKES = 200;
const MAX_POINTS = 4000;
const KEYWORD_IDS = new Set(keywords.map((keyword) => keyword.id));

function isPoint(value: unknown): value is Point {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    value.every((coordinate) => typeof coordinate === "number" && coordinate >= 0 && coordinate <= 1)
  );
}

function isStroke(value: unknown): value is Stroke {
  if (typeof value !== "object" || value === null) return false;
  const { width, points } = value as Record<string, unknown>;
  return (
    typeof width === "number" &&
    width >= PEN_WIDTH.min &&
    width <= PEN_WIDTH.max &&
    Array.isArray(points) &&
    points.length > 0 &&
    points.every(isPoint)
  );
}

export function inkLength(strokes: Stroke[]): number {
  let length = 0;
  for (const { points } of strokes) {
    for (let i = 1; i < points.length; i++) {
      const [fromX, fromY] = points[i - 1]!;
      const [toX, toY] = points[i]!;
      length += Math.hypot(toX - fromX, toY - fromY);
    }
  }
  return length;
}

export function parseDrawing(body: unknown): ParseResult {
  if (typeof body !== "object" || body === null) return { ok: false, error: "잘못된 요청입니다." };
  const { keywordId, strokes } = body as Record<string, unknown>;

  if (typeof keywordId !== "string" || !KEYWORD_IDS.has(keywordId)) {
    return { ok: false, error: "알 수 없는 제시어입니다." };
  }
  if (!Array.isArray(strokes) || strokes.length === 0) {
    return { ok: false, error: "빈 그림은 제출할 수 없습니다." };
  }
  if (strokes.length > MAX_STROKES || !strokes.every(isStroke)) {
    return { ok: false, error: "그림 데이터가 올바르지 않습니다." };
  }
  const pointCount = strokes.reduce((total, stroke) => total + stroke.points.length, 0);
  if (pointCount > MAX_POINTS) {
    return { ok: false, error: "그림이 너무 복잡합니다." };
  }
  if (inkLength(strokes) < MIN_INK_LENGTH) {
    return { ok: false, error: "조금 더 그려 주세요." };
  }

  // 검증한 필드만 저장
  const cleanStrokes = strokes.map(({ width, points }) => ({ width, points }));
  return { ok: true, drawing: { keywordId, strokes: cleanStrokes } };
}
