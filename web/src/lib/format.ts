export function formatTime(time: number | string) {
  return new Date(time).toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit" });
}
