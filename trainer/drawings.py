import json
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

IMAGE_SIZE = 128
# 브라우저 캔버스처럼 부드러운 선을 얻기 위해 크게 그린 뒤 축소
SUPERSAMPLE = 4


# 잉크 농도 반환 (255가 가장 진함)
def rasterize(strokes: list[dict]) -> np.ndarray:
    size = IMAGE_SIZE * SUPERSAMPLE
    image = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        width = max(1, round(stroke["width"] * size))
        points = [(x * size, y * size) for x, y in stroke["points"]]
        if len(points) > 1:
            draw.line(points, fill=0, width=width, joint="curve")
        radius = width / 2
        for x, y in (points[0], points[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=0)
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.LANCZOS)
    return 255 - np.asarray(image, dtype=np.uint8)


# 새로 추가된 그림만 읽어 그림마다 한 번만 래스터화
class DrawingSource:

    def __init__(self, database: Path, keyword_ids: list[str]):
        self.database = database
        self.keyword_index = {keyword_id: index for index, keyword_id in enumerate(keyword_ids)}
        self.last_id = 0
        self.images: list[np.ndarray] = []
        self.labels: list[int] = []

    def load_new(self):
        if not self.database.exists():
            return
        connection = sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT id, keyword_id, strokes_json FROM drawings WHERE id > ? ORDER BY id",
                (self.last_id,),
            ).fetchall()
        finally:
            connection.close()

        for drawing_id, keyword_id, strokes_json in rows:
            self.last_id = drawing_id
            label = self.keyword_index.get(keyword_id)
            if label is None:
                print(f"알 수 없는 키워드라 건너뜀: drawing {drawing_id} ({keyword_id})")
                continue
            self.images.append(rasterize(json.loads(strokes_json)))
            self.labels.append(label)
