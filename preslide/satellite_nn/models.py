"""Model A (U-Net/ResNet-18) and independent model B (LR-ASPP/MobileNetV3). RGB in, one logit map out, no cross inputs."""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision


class _Up(nn.Module):
    def __init__(self, cin: int, skip: int, cout: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(cin + skip, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(True))

    def forward(self, x, skip):
        x = F.interpolate(x, size=skip.shape[-2:], mode='bilinear', align_corners=False)
        return self.conv(torch.cat([x, skip], 1))


class UNetResNet18(nn.Module):
    def __init__(self, pretrained: bool = False):
        super().__init__()
        r = torchvision.models.resnet18(weights='IMAGENET1K_V1' if pretrained else None)
        self.stem = nn.Sequential(r.conv1, r.bn1, r.relu)
        self.pool = r.maxpool
        self.l1, self.l2, self.l3, self.l4 = r.layer1, r.layer2, r.layer3, r.layer4
        self.u4, self.u3, self.u2, self.u1 = _Up(512, 256, 128), _Up(128, 128, 64), _Up(64, 64, 64), _Up(64, 64, 32)
        self.head = nn.Conv2d(32, 1, 1)

    def forward(self, x):
        s0 = self.stem(x); s1 = self.l1(self.pool(s0)); s2 = self.l2(s1); s3 = self.l3(s2); s4 = self.l4(s3)
        d = self.u1(self.u2(self.u3(self.u4(s4, s3), s2), s1), s0)
        return F.interpolate(self.head(d), size=x.shape[-2:], mode='bilinear', align_corners=False)


class LRASPP(nn.Module):
    def __init__(self, pretrained: bool = False):
        super().__init__()
        self.net = torchvision.models.segmentation.lraspp_mobilenet_v3_large(
            weights=None, weights_backbone='IMAGENET1K_V1' if pretrained else None, num_classes=1)

    def forward(self, x):
        return self.net(x)['out']


def build(name: str, pretrained: bool = False) -> nn.Module:
    return {'a': UNetResNet18, 'b': LRASPP}[name](pretrained)


def masked_loss(logits: torch.Tensor, target: torch.Tensor, ignore: torch.Tensor,
                weight: torch.Tensor | None = None) -> torch.Tensor:
    """Equal-weighted BCE + Dice; ignore pixels (True) contribute to neither term."""
    keep = (~ignore).float()
    w = keep if weight is None else keep * weight
    bce = (F.binary_cross_entropy_with_logits(logits, target, reduction='none') * w).sum() / w.sum().clamp(min=1)
    p = torch.sigmoid(logits) * keep
    t = target * keep
    dice = 1 - (2 * (p * t).sum() + 1) / (p.sum() + t.sum() + 1)
    return 0.5 * bce + 0.5 * dice
