export type RateLimitResult = { allowed: true } | { allowed: false; retryAt: number };

// 방문자 주소를 저장하지 않도록 메모리에서만 유지
export function createRateLimiter(limit: number, windowMs: number) {
  const hits = new Map<string, number[]>();

  return {
    take(key: string): RateLimitResult {
      const now = Date.now();
      const recent = (hits.get(key) ?? []).filter((time) => time > now - windowMs);
      hits.set(key, recent);
      if (recent.length >= limit) return { allowed: false, retryAt: recent[0]! + windowMs };
      recent.push(now);
      return { allowed: true };
    },

    sweep() {
      const expiredBefore = Date.now() - windowMs;
      for (const [key, times] of hits) {
        if (times.at(-1)! <= expiredBefore) hits.delete(key);
      }
    },
  };
}
