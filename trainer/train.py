# 새 그림이 들어올 때만 학습하고, 그리기는 주기마다 무작위 제시어로 계속해 웹 서버에 전달

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
STEPS_PER_ROUND = 100
# 학습이 빨리 끝나도 그림을 볼 시간 확보
DRAW_INTERVAL_SECONDS = 10


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


# bf16 연산을 하드웨어로 지원하지 않는 장비에서는 오히려 느려지므로 지원할 때만 사용
def supports_bf16(device: torch.device) -> bool:
    if device.type == "cuda":
        return torch.cuda.is_bf16_supported()
    return torch.cpu._is_avx512_bf16_supported()


def sample_batch(images: torch.Tensor, labels: torch.Tensor, device: torch.device):
    index = torch.randint(len(images), (min(BATCH_SIZE, len(images)),))
    batch = images[index].to(device).float() / 255
    return batch.contiguous(memory_format=torch.channels_last), labels[index].to(device)


def train_vae(vae: ConditionalVAE, optimizer, images, labels, device, use_bf16: bool) -> float:
    vae.train()
    for _ in range(STEPS_PER_ROUND):
        batch, batch_labels = sample_batch(images, labels, device)
        with torch.autocast(device.type, dtype=torch.bfloat16, enabled=use_bf16):
            logits, mean, log_variance = vae(batch, batch_labels)
        # 손실은 정밀도 유지를 위해 32비트로 계산
        loss = vae_loss(logits.float(), batch, mean.float(), log_variance.float())
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
    # channels_last 가중치는 연속 메모리가 아니라 safetensors가 저장하지 못함
    weights = {name: tensor.contiguous() for name, tensor in vae.state_dict().items()}
    write_atomically(MODEL_DIR / "model.safetensors", lambda path: save_file(weights, path))
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


def write_status(round_number: int, keyword_id: str, trained_drawings: int, trained_at: str):
    status = {
        "round": round_number,
        "keywordId": keyword_id,
        "trainedDrawings": trained_drawings,
        "trainedAt": trained_at,
        "drawnAt": datetime.now(timezone.utc).isoformat(),
    }
    write_atomically(STATUS_PATH, lambda path: path.write_text(json.dumps(status), encoding="utf-8"))


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = supports_bf16(device)
    # 입력 크기가 항상 같아 가장 빠른 합성곱 방식을 한 번 골라 재사용
    torch.backends.cudnn.benchmark = True
    print(f"학습 장치: {device} · bf16: {use_bf16} · 데이터: {DATA_DIR}")

    source = DrawingSource(DATABASE_PATH, [keyword["id"] for keyword in KEYWORDS])
    vae = ConditionalVAE(len(KEYWORDS), LATENT_DIM)
    load_weights(vae, MODEL_DIR / "model.safetensors")
    vae = vae.to(device, memory_format=torch.channels_last)
    optimizer = torch.optim.Adam(vae.parameters(), lr=LEARNING_RATE)
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else None
    round_number = status["round"] if status else 0
    trained_at = status["trainedAt"] if status else ""

    while True:
        started = time.monotonic()

        # 적은 그림을 반복 학습하면 모델이 붕괴하므로 새 그림이 있을 때만 학습
        if source.load_new() > 0 and source.images:
            images = torch.from_numpy(np.stack(source.images)).unsqueeze(1)
            labels = torch.tensor(source.labels)
            loss = train_vae(vae, optimizer, images, labels, device, use_bf16)
            round_number += 1
            trained_at = datetime.now(timezone.utc).isoformat()
            save_model(vae)
            print(f"{round_number}회 학습 · 그림 {len(images)}장 · 손실 {loss:.1f} · {time.monotonic() - started:.1f}초")

        if source.images:
            label = random.randrange(len(KEYWORDS))
            publish_drawing(vae, label, device)
            write_status(round_number, KEYWORDS[label]["id"], len(source.images), trained_at)

        time.sleep(max(0, DRAW_INTERVAL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
