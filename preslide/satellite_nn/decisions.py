"""Object matching and decision state machine. VERIFIED_* only from independent review, never from model agreement."""
from __future__ import annotations
import numpy as np

STATES = ('UNASSESSABLE', 'NO_VISIBLE_DETECTION', 'DISAGREEMENT', 'MODEL_AGREEMENT',
          'VERIFIED_POSITIVE', 'VERIFIED_NEGATIVE', 'UNKNOWN')
INDEPENDENT_SOURCES = ('human_review', 'orthophoto', 'field_survey')


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.astype(bool), b.astype(bool)
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def decide(assessable: bool, a_detects: bool, b_confirms: bool, iou: float, iou_min: float = 0.30,
           review: dict | None = None) -> str:
    if review is not None:
        if review.get('source') not in INDEPENDENT_SOURCES:
            raise ValueError('verification needs an independent source, not model output')
        return {'positive': 'VERIFIED_POSITIVE', 'negative': 'VERIFIED_NEGATIVE'}.get(review.get('verdict'), 'UNKNOWN')
    if not assessable:
        return 'UNASSESSABLE'
    if not a_detects:
        return 'NO_VISIBLE_DETECTION'  # never a negative label
    if b_confirms and iou >= iou_min:
        return 'MODEL_AGREEMENT'       # pseudo-label candidate only
    return 'DISAGREEMENT'


def match_one_to_one(pred: list[np.ndarray], ref: list[np.ndarray], iou_min: float = 0.30):
    """Greedy 1:1 IoU matching: (matches, unmatched_pred, unmatched_ref). Duplicates never count twice."""
    pairs = sorted(((mask_iou(p, r), i, j) for i, p in enumerate(pred) for j, r in enumerate(ref)), reverse=True)
    used_p, used_r, out = set(), set(), []
    for iou, i, j in pairs:
        if iou < iou_min:
            break
        if i in used_p or j in used_r:
            continue
        used_p.add(i); used_r.add(j); out.append((i, j, iou))
    return out, [i for i in range(len(pred)) if i not in used_p], [j for j in range(len(ref)) if j not in used_r]
