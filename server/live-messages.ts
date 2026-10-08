// 서버가 실시간 연결로 보내는 메시지, 웹 클라이언트와 타입으로 공유

export interface ModelStatus {
  round: number;
  // 이번 라운드에 멍청이가 그린 제시어
  keywordId: string;
  trainedDrawings: number;
  trainedAt: string;
}

export type LiveMessage =
  | { type: "snapshot"; drawings: number; model: ModelStatus | null }
  | { type: "drawings"; drawings: number }
  | { type: "model"; model: ModelStatus };
