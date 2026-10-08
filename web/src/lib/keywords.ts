import keywords from "../../../keywords.json";

export type Keyword = (typeof keywords)[number];

export { keywords };

export function pickKeyword(current?: Keyword): Keyword {
  const candidates = keywords.filter((keyword) => keyword.id !== current?.id);
  return candidates[Math.floor(Math.random() * candidates.length)]!;
}
