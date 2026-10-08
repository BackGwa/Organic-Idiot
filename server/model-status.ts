import type { ModelStatus } from "./live-messages";

const POLL_INTERVAL_MS = 2000;

// 학습기가 라운드마다 통째로 교체하는 상태 파일을 폴링
export function watchModelStatus(path: string, onChange: (status: ModelStatus) => void) {
  let lastModified = 0;

  async function check() {
    const file = Bun.file(path);
    if (!(await file.exists()) || file.lastModified === lastModified) return;
    try {
      onChange((await file.json()) as ModelStatus);
      // 읽기에 실패한 버전은 다음 폴링에서 다시 시도
      lastModified = file.lastModified;
    } catch (error) {
      console.error(`모델 상태 파일을 읽지 못했습니다: ${path}`, error);
    }
  }

  check();
  setInterval(check, POLL_INTERVAL_MS);
}
