const NOTICE_KEY = "organic-idiot:notice-acknowledged";

// 저장소를 쓸 수 없는 환경에서는 방문할 때마다 고지를 다시 표시
export function isNoticeAcknowledged(): boolean {
  try {
    return localStorage.getItem(NOTICE_KEY) === "true";
  } catch {
    return false;
  }
}

export function acknowledgeNotice() {
  try {
    localStorage.setItem(NOTICE_KEY, "true");
  } catch {}
}
