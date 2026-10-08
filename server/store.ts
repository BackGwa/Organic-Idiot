import { Database } from "bun:sqlite";
import type { Drawing } from "./drawing";

export function openStore(path: string) {
  const db = new Database(path, { create: true });
  db.run("PRAGMA journal_mode = WAL");
  db.run(`
    CREATE TABLE IF NOT EXISTS drawings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      keyword_id TEXT NOT NULL,
      strokes_json TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )
  `);

  const insert = db.query(
    "INSERT INTO drawings (keyword_id, strokes_json, created_at) VALUES (?, ?, ?)",
  );
  const count = db.query<{ drawings: number }, []>("SELECT COUNT(*) AS drawings FROM drawings");

  return {
    addDrawing(drawing: Drawing) {
      insert.run(drawing.keywordId, JSON.stringify(drawing.strokes), Date.now());
    },
    countDrawings(): number {
      return count.get()!.drawings;
    },
  };
}
