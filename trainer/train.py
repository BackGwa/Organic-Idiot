# 모인 그림으로 계속 학습하고 라운드마다 무작위 제시어 하나를 그려 웹 서버에 전달

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import torch
from PIL import Image
from safetensors.torch import load_file, save_file
from torch import nn

from drawings import IMAGE_SIZE, DrawingSource
from models import ConditionalVAE, vae_loss

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()
DATABASE_PATH = DATA_DIR / "organic-idiot.db"
MODEL_DIR = DATA_DIR / "model"
IDIOT_DRAWING_PATH = DATA_DIR / "idiot.png"
STATUS_PATH = DATA_DIR / "status.json"

KEYWORDS = json.loads((ROOT / "keywords.json").read_text(encoding="utf-8"))
LATENT_DIM = 64
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
STEPS_PER_ROUND = 200
# GPU에서 라운드가 빨리 끝나도 그림을 볼 시간 확보
MIN_ROUND_SECONDS = 10
POLL_SECONDS = 5


# Windows에서는 웹 서버가 파일을 보내는 동안 잠시 교체가 막힐 수 있음
def replace_file(source: Path, target: Path):
    for attempt in range(10):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.1)


# 웹 서버가 쓰다 만 파일을 읽지 않도록 임시 파일에 쓴 뒤 교체
def write_atomically(path: Path, write: Callable[[Path], None]):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    write(temporary)
    replace_file(temporary, path)


def load_weights(model: nn.Module, path: Path):
    if path.exists():
        model.load_state_dict(load_file(path))
        print(f"이전 학습을 이어서 진행: {path}")


def sample_batch(images: torch.Tensor, labels: torch.Tensor, device: torch.device):
    index = torch.randint(len(images), (min(BATCH_SIZE, len(images)),))
    return images[index].to(device).float() / 255, labels[index].to(device)


def train_vae(vae: ConditionalVAE, optimizer, images, labels, device) -> float:
    vae.train()
    for _ in range(STEPS_PER_ROUND):
        batch, batch_labels = sample_batch(images, labels, device)
        logits, mean, log_variance = vae(batch, batch_labels)
        loss = vae_loss(logits, batch, mean, log_variance)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return loss.item()


def publish_drawing(vae: ConditionalVAE, label: int, device):
    vae.eval()
    ink = vae.draw(torch.tensor([label], device=device))[0, 0].cpu().numpy()
    image = Image.fromarray((255 - ink * 255).round().astype(np.uint8))
    write_atomically(IDIOT_DRAWING_PATH, lambda path: image.save(path, format="PNG"))


# Hugging Face 공개용 모델과 설정
def save_model(vae: ConditionalVAE):
    write_atomically(MODEL_DIR / "model.safetensors", lambda path: save_file(vae.state_dict(), path))
    config = {
        "architecture": "ConditionalVAE",
        "image_size": IMAGE_SIZE,
        "latent_dim": LATENT_DIM,
        "keywords": KEYWORDS,
    }
    write_atomically(
        MODEL_DIR / "config.json",
        lambda path: path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"),
    )


def write_status(round_number: int, keyword_id: str, trained_drawings: int):
    status = {
        "round": round_number,
        "keywordId": keyword_id,
        "trainedDrawings": trained_drawings,
        "trainedAt": datetime.now(timezone.utc).isoformat(),
    }
    write_atomically(STATUS_PATH, lambda path: path.write_text(json.dumps(status), encoding="utf-8"))


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"학습 장치: {device} · 데이터: {DATA_DIR}")

    source = DrawingSource(DATABASE_PATH, [keyword["id"] for keyword in KEYWORDS])
    vae = ConditionalVAE(len(KEYWORDS), LATENT_DIM).to(device)
    load_weights(vae, MODEL_DIR / "model.safetensors")
    optimizer = torch.optim.Adam(vae.parameters(), lr=LEARNING_RATE)
    round_number = json.loads(STATUS_PATH.read_text(encoding="utf-8"))["round"] if STATUS_PATH.exists() else 0

    while True:
        source.load_new()
        if not source.images:
            time.sleep(POLL_SECONDS)
            continue

        started = time.monotonic()
        images = torch.from_numpy(np.stack(source.images)).unsqueeze(1)
        labels = torch.tensor(source.labels)
        loss = train_vae(vae, optimizer, images, labels, device)

        round_number += 1
        label = random.randrange(len(KEYWORDS))
        publish_drawing(vae, label, device)
        save_model(vae)
        write_status(round_number, KEYWORDS[label]["id"], len(images))
        elapsed = time.monotonic() - started
        print(f"{round_number}회 학습 · 그림 {len(images)}장 · 손실 {loss:.1f} · {elapsed:.1f}초")
        time.sleep(max(0, MIN_ROUND_SECONDS - elapsed))


if __name__ == "__main__":
    main()
