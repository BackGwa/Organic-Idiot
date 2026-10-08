<script lang="ts">
  import type { Point, Stroke } from "../../../server/drawing";

  let { strokes = $bindable(), penWidth, label }: { strokes: Stroke[]; penWidth: number; label: string } = $props();

  // 모양에 영향 없는 촘촘한 점은 저장하지 않음
  const MIN_POINT_DISTANCE = 0.004;
  const INK = getComputedStyle(document.documentElement).getPropertyValue("--ink").trim();

  let canvas: HTMLCanvasElement;
  let size = $state(0);
  let drawing = false;

  function clamp(value: number) {
    return Math.round(Math.min(Math.max(value, 0), 1) * 10000) / 10000;
  }

  function toPoint(event: PointerEvent): Point {
    const rect = canvas.getBoundingClientRect();
    return [clamp((event.clientX - rect.left) / rect.width), clamp((event.clientY - rect.top) / rect.height)];
  }

  function start(event: PointerEvent) {
    if (event.button !== 0) return;
    canvas.setPointerCapture(event.pointerId);
    drawing = true;
    strokes.push({ width: penWidth, points: [toPoint(event)] });
  }

  function move(event: PointerEvent) {
    const points = strokes.at(-1)?.points;
    if (!drawing || !points) return;
    const point = toPoint(event);
    const [lastX, lastY] = points.at(-1)!;
    if (Math.hypot(point[0] - lastX, point[1] - lastY) >= MIN_POINT_DISTANCE) points.push(point);
  }

  function end() {
    drawing = false;
  }

  $effect(() => {
    const observer = new ResizeObserver(([entry]) => (size = entry!.contentRect.width));
    observer.observe(canvas);
    return () => observer.disconnect();
  });

  $effect(() => {
    const pixels = Math.round(size * (window.devicePixelRatio || 1));
    // 펜을 움직일 때마다 버퍼를 재할당하지 않도록 크기가 바뀔 때만 설정
    if (canvas.width !== pixels) canvas.width = canvas.height = pixels;
    const context = canvas.getContext("2d")!;
    context.setTransform(pixels, 0, 0, pixels, 0, 0);
    context.clearRect(0, 0, 1, 1);
    context.lineCap = "round";
    context.lineJoin = "round";
    context.strokeStyle = context.fillStyle = INK;

    for (const { width, points } of strokes) {
      const [first, ...rest] = points;
      if (!first) continue;
      context.beginPath();
      if (rest.length === 0) {
        context.arc(first[0], first[1], width / 2, 0, Math.PI * 2);
        context.fill();
        continue;
      }
      context.lineWidth = width;
      context.moveTo(first[0], first[1]);
      for (const [x, y] of rest) context.lineTo(x, y);
      context.stroke();
    }
  });
</script>

<canvas
  bind:this={canvas}
  class="paper"
  aria-label={label}
  onpointerdown={start}
  onpointermove={move}
  onpointerup={end}
  onpointercancel={end}
></canvas>

<style>
  canvas {
    touch-action: none;
    cursor: crosshair;
  }
</style>
