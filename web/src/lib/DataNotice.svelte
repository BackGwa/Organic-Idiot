<script lang="ts">
  let {
    open = $bindable(),
    acknowledged,
    onacknowledge,
  }: { open: boolean; acknowledged: boolean; onacknowledge: () => void } = $props();

  let dialog: HTMLDialogElement;

  $effect(() => {
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });

  function confirm() {
    if (!acknowledged) onacknowledge();
    open = false;
  }

  function cancel(event: Event) {
    // 처음 한 번은 확인해야 참여 가능
    if (!acknowledged) event.preventDefault();
    else open = false;
  }
</script>

<dialog bind:this={dialog} oncancel={cancel} aria-labelledby="notice-title">
  <h2 id="notice-title">데이터 고지</h2>
  <ul>
    <li>그린 그림은 모두 유기농 멍청이의 <strong>학습에 사용</strong>됩니다.</li>
    <li>학습 데이터는 프로젝트가 끝나면 <strong>모두 폐기</strong>됩니다.</li>
    <li>학습된 모델은 추후 <strong>Hugging Face에 공개</strong>됩니다. 단, 데이터셋은 공개하지 않습니다.</li>
    <li>
      <strong>개인정보 등 민감한 내용은 그리지 마세요.</strong> 그린 내용이 공개된 모델에 남을 수 있습니다.
    </li>
  </ul>
  <button class="button primary" onclick={confirm}>{acknowledged ? "닫기" : "확인했어요"}</button>
</dialog>

<style>
  dialog {
    width: min(460px, calc(100% - 32px));
    padding: 24px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--text);
  }

  dialog::backdrop {
    background: rgb(0 0 0 / 0.45);
  }

  h2 {
    margin: 0;
    font-size: 1.2rem;
  }

  ul {
    margin: 16px 0 24px;
    padding-left: 20px;
    display: grid;
    gap: 10px;
  }

  button {
    width: 100%;
  }
</style>
