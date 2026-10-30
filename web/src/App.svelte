<script lang="ts">
  import { Check, Eraser, Send, Shuffle, Undo2 } from "@lucide/svelte";
  import { inkLength, MIN_INK_LENGTH, PEN_WIDTH, type Stroke } from "../../server/drawing";
  import DataNotice from "./lib/DataNotice.svelte";
  import DrawingCanvas from "./lib/DrawingCanvas.svelte";
  import { formatTime } from "./lib/format";
  import { keywords, pickKeyword } from "./lib/keywords";
  import { connectLive } from "./lib/live.svelte";
  import { acknowledgeNotice, isNoticeAcknowledged } from "./lib/storage";
  import { submitDrawing } from "./lib/submit";

  type Feedback =
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "success" }
    | { kind: "error"; message: string };

  const SUCCESS_DISPLAY_MS = 1200;

  // 굵기 미리보기를 데스크톱 그림판 크기 기준으로 표시
  const PREVIEW_SCALE = 400;

  const live = connectLive();

  const firstVisit = !isNoticeAcknowledged();
  let acknowledged = $state(!firstVisit);
  let noticeOpen = $state(firstVisit);
  let keyword = $state(pickKeyword());
  let strokes = $state<Stroke[]>([]);
  let penWidth = $state<number>(PEN_WIDTH.initial);
  let feedback = $state<Feedback>({ kind: "idle" });

  const submitting = $derived(feedback.kind === "submitting");
  const submitted = $derived(feedback.kind === "success");
  const progress = $derived(Math.min(inkLength(strokes) / MIN_INK_LENGTH, 1));
  const ready = $derived(progress >= 1);
  const idiotKeyword = $derived(keywords.find((candidate) => candidate.id === live.model?.keywordId));

  $effect(() => {
    if (!submitted) return;
    const timer = setTimeout(() => (feedback = { kind: "idle" }), SUCCESS_DISPLAY_MS);
    return () => clearTimeout(timer);
  });

  function confirmNotice() {
    acknowledgeNotice();
    acknowledged = true;
  }

  function clearDrawing() {
    strokes = [];
    feedback = { kind: "idle" };
  }

  function undo() {
    if (!submitting) strokes.pop();
  }

  function undoOnShortcut(event: KeyboardEvent) {
    const isUndo = (event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === "z";
    if (!isUndo || !acknowledged) return;
    event.preventDefault();
    undo();
  }

  function nextKeyword() {
    keyword = pickKeyword(keyword);
    clearDrawing();
  }

  async function submit() {
    feedback = { kind: "submitting" };
    const result = await submitDrawing(keyword.id, $state.snapshot(strokes));
    if (!result.ok) {
      feedback = { kind: "error", message: result.message };
      return;
    }
    keyword = pickKeyword(keyword);
    strokes = [];
    feedback = { kind: "success" };
  }
</script>

<svelte:window onkeydown={undoOnShortcut} />

<DataNotice bind:open={noticeOpen} {acknowledged} onacknowledge={confirmNotice} />

<main inert={!acknowledged}>
  <h1 class="sr-only">유기농 멍청이</h1>

  <div class="layout">
    <section class="drawing" aria-label="그리기">
      <div class="bar">
        <h2 class="keyword"><span class="sr-only">제시어: </span>{keyword.label}</h2>
        <button class="button" onclick={nextKeyword} disabled={submitting}>
          <Shuffle size={18} aria-hidden="true" /> 다른 단어
        </button>
      </div>

      <DrawingCanvas bind:strokes {penWidth} label="{keyword.label} 그림판" />

      <label class="pen">
        <span>굵기</span>
        <input type="range" min={PEN_WIDTH.min} max={PEN_WIDTH.max} step={PEN_WIDTH.step} bind:value={penWidth} />
        <span class="pen-preview" aria-hidden="true">
          <span style:width="{penWidth * PREVIEW_SCALE}px" style:height="{penWidth * PREVIEW_SCALE}px"></span>
        </span>
      </label>

      <div class="actions">
        <button class="button" onclick={undo} title="되돌리기 (Ctrl+Z)" disabled={strokes.length === 0 || submitting}>
          <Undo2 size={18} aria-hidden="true" /> 되돌리기
        </button>
        <button class="button" onclick={clearDrawing} disabled={strokes.length === 0 || submitting}>
          <Eraser size={18} aria-hidden="true" /> 지우기
        </button>
        <button
          class="button submit"
          class:ready
          class:done={submitted}
          style:--progress={progress}
          onclick={submit}
          disabled={!ready || submitting}
        >
          {#if submitted}
            <Check size={18} aria-hidden="true" /> 완료
          {:else}
            <Send size={18} aria-hidden="true" /> {submitting ? "제출 중…" : "제출"}
            {#if !ready}<span class="sr-only">(조금 더 그려 주세요)</span>{/if}
          {/if}
        </button>
      </div>

      <p class="feedback" role="status">
        {#if submitted}
          <span class="sr-only">제출했어요.</span>
        {:else if feedback.kind === "error"}
          {feedback.message}
        {/if}
      </p>
    </section>

    <section class="idiot" aria-label="멍청이">
      <div class="bar">
        <h2 class="keyword">
          {#if idiotKeyword}<span class="prefix">멍청이가 그린</span> {idiotKeyword.label}{:else}<span class="prefix">멍청이</span>{/if}
        </h2>
      </div>

      {#if live.model}
        <img class="paper" src="/idiot.png?drawn={live.model.drawnAt}" alt="멍청이가 그린 {idiotKeyword?.label}" />
      {:else}
        <p class="paper empty">아직 아무것도 몰라요.<br />그림이 모이면 배우기 시작해요.</p>
      {/if}

      <div class="status">
        <dl class="counts">
          <div><dt>제출된 그림</dt><dd>{live.drawings.toLocaleString()}장</dd></div>
          <div><dt>학습</dt><dd>{(live.model?.round ?? 0).toLocaleString()}회</dd></div>
        </dl>
        {#if live.model}
          <span>{live.model.trainedDrawings.toLocaleString()}장으로 배움 · {formatTime(live.model.trainedAt)}</span>
        {/if}
      </div>
    </section>
  </div>

  <footer>
    <button class="link" onclick={() => (noticeOpen = true)}>데이터 고지</button>
  </footer>
</main>

<style>
  main {
    --board: clamp(260px, calc(100svh - 260px), 480px);
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 100svh;
    padding: 24px 16px;
  }

  .layout {
    display: grid;
    grid-template-columns: var(--board) var(--board);
    justify-content: center;
  }

  .drawing {
    padding-right: 40px;
  }

  .idiot {
    padding-left: 40px;
    border-left: 1px solid var(--border);
  }

  @media (max-width: 760px) {
    main {
      --board: 100%;
      justify-content: flex-start;
    }

    .layout {
      grid-template-columns: minmax(0, 1fr);
    }

    .drawing {
      padding: 0 0 24px;
    }

    .idiot {
      padding: 24px 0 0;
      border-left: 0;
      border-top: 1px solid var(--border);
    }
  }

  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 48px;
    margin: 0 0 12px;
  }

  .keyword {
    margin: 0;
    font-size: 1.75rem;
  }

  .prefix {
    font-size: 1rem;
    font-weight: 500;
    color: var(--text-muted);
  }

  .status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 4px 16px;
    margin-top: 12px;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .counts {
    display: flex;
    gap: 20px;
    margin: 0;
  }

  .counts div {
    display: flex;
    gap: 6px;
  }

  dd {
    margin: 0;
    color: var(--text);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .empty {
    display: grid;
    place-content: center;
    text-align: center;
    color: var(--text-muted);
  }

  .pen {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
    font-size: 0.9rem;
  }

  .pen input {
    flex: 1;
    accent-color: var(--accent);
  }

  .pen-preview {
    display: grid;
    place-items: center;
    width: 20px;
    height: 20px;
  }

  .pen-preview span {
    border-radius: 50%;
    background: var(--ink);
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }

  .feedback {
    min-height: 1.5em;
    margin: 8px 0 0;
    font-size: 0.9rem;
    color: var(--danger);
  }

  .submit {
    flex: 1;
    position: relative;
    isolation: isolate;
    overflow: hidden;
    border-color: var(--accent-track);
    background: var(--accent-track);
    color: var(--accent-strong);
  }

  .submit::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    z-index: -1;
    width: calc(var(--progress) * 100%);
    background: var(--accent-fill);
    transition: width 0.15s ease-out;
  }

  .submit:disabled {
    opacity: 1;
  }

  .submit.ready,
  .submit.done {
    border-color: var(--accent);
    background: var(--accent);
    color: var(--accent-text);
  }

  .submit.ready::before,
  .submit.done::before {
    display: none;
  }

  .submit.done {
    animation: pop 0.4s ease-out;
  }

  @keyframes pop {
    40% {
      transform: scale(1.06);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .submit.done {
      animation: none;
    }
  }

  footer {
    margin-top: 16px;
    text-align: center;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .link {
    padding: 0;
    border: 0;
    background: none;
    text-decoration: underline;
    cursor: pointer;
  }
</style>
