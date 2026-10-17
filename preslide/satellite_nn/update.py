"""Gold/pseudo separation and admission rules for retraining."""
from __future__ import annotations

NOT_TRAINABLE = ('UNKNOWN', 'DISAGREEMENT', 'UNASSESSABLE', 'NO_VISIBLE_DETECTION')


def admit(sample: dict, cfg: dict) -> dict:
    """Training record or ValueError. Pseudo labels: train regions only, fixed low weight, off by default."""
    state, split = sample['state'], sample['split']
    if state in NOT_TRAINABLE:
        raise ValueError(f'{state} cannot be used for training')
    if split != 'train':
        raise ValueError(f'sample from split {split!r} must never enter training')
    if state == 'MODEL_AGREEMENT':
        if not cfg['auto_train_pseudolabels']:
            raise ValueError('pseudo-label training disabled')
        return {**sample, 'weight': cfg['pseudo_weight'], 'kind': 'pseudo'}
    return {**sample, 'weight': 1.0, 'kind': 'verified'}


def pseudo_share(records: list[dict]) -> float:
    tot = sum(r['weight'] for r in records)
    return sum(r['weight'] for r in records if r['kind'] == 'pseudo') / tot if tot else 0.0


def check_cycle(records: list[dict], cfg: dict) -> None:
    if not any(r['kind'] == 'verified' for r in records):
        raise ValueError('a cycle needs verified examples')
    if pseudo_share(records) > cfg['pseudo_loss_share_max'] + 1e-9:
        raise ValueError('pseudo-label loss share exceeds the registered maximum')
