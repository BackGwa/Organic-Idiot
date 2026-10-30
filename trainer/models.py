import torch
from torch import nn
from torch.nn import functional as F

FEATURE_CHANNELS = 256
# 128 크기를 stride 2 합성곱 4번으로 줄인 크기
FEATURE_SIZE = 8
# 그림이 적을 때 분산이 0으로 붕괴해 무작위 잠재 벡터에서 검은 그림이 나오는 것 방지
LOG_VARIANCE_RANGE = (-6, 6)
# 잠재 공간을 표준 정규분포에 가깝게 붙잡아 무작위로 그려도 형태가 나오게 함
KL_WEIGHT = 4


def down(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(nn.Conv2d(in_channels, out_channels, 4, stride=2, padding=1), nn.LeakyReLU(0.2))


def up(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(nn.ConvTranspose2d(in_channels, out_channels, 4, stride=2, padding=1), nn.LeakyReLU(0.2))


class ConditionalVAE(nn.Module):
    def __init__(self, keyword_count: int, latent_dim: int):
        super().__init__()
        self.keyword_count = keyword_count
        self.latent_dim = latent_dim
        flat = FEATURE_CHANNELS * FEATURE_SIZE * FEATURE_SIZE
        self.encoder = nn.Sequential(down(1, 32), down(32, 64), down(64, 128), down(128, FEATURE_CHANNELS), nn.Flatten())
        self.to_mean = nn.Linear(flat + keyword_count, latent_dim)
        self.to_log_variance = nn.Linear(flat + keyword_count, latent_dim)
        self.from_latent = nn.Linear(latent_dim + keyword_count, flat)
        self.decoder = nn.Sequential(up(FEATURE_CHANNELS, 128), up(128, 64), up(64, 32), nn.ConvTranspose2d(32, 1, 4, stride=2, padding=1))

    # 확률이 아닌 잉크 로짓 반환
    def decode(self, latent: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        condition = F.one_hot(labels, self.keyword_count).float()
        features = self.from_latent(torch.cat([latent, condition], dim=1))
        return self.decoder(F.leaky_relu(features, 0.2).view(-1, FEATURE_CHANNELS, FEATURE_SIZE, FEATURE_SIZE))

    def forward(self, images: torch.Tensor, labels: torch.Tensor):
        condition = F.one_hot(labels, self.keyword_count).float()
        features = torch.cat([self.encoder(images), condition], dim=1)
        mean = self.to_mean(features)
        log_variance = self.to_log_variance(features).clamp(*LOG_VARIANCE_RANGE)
        latent = mean + torch.randn_like(mean) * torch.exp(0.5 * log_variance)
        return self.decode(latent, labels), mean, log_variance

    # 매번 새 랜덤 잠재 벡터를 써서 같은 제시어도 매번 다르게 그림
    @torch.no_grad()
    def draw(self, labels: torch.Tensor) -> torch.Tensor:
        latent = torch.randn(len(labels), self.latent_dim, device=labels.device)
        return torch.sigmoid(self.decode(latent, labels))


def vae_loss(logits, images, mean, log_variance) -> torch.Tensor:
    reconstruction = F.binary_cross_entropy_with_logits(logits, images, reduction="sum")
    divergence = -0.5 * torch.sum(1 + log_variance - mean.pow(2) - log_variance.exp())
    return (reconstruction + KL_WEIGHT * divergence) / len(images)
