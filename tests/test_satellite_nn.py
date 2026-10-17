import inspect
import numpy as np
import pytest
import torch

from preslide.common import read_json
from preslide.satellite_nn import decisions, models, paths, tiles, update
from preslide.sources import ROOT

CFG = read_json(ROOT / 'config/satellite_nn_v01.json')


def test_tiles_cover_raster_and_edges():
    o = tiles.tile_origins(300, 200)
    cov = np.zeros((300, 200), bool)
    for r, c in o:
        cov[r:r + 128, c:c + 128] = True
    assert cov.all() and max(r for r, _ in o) == 300 - 128


def test_tiles_reject_small_raster():
    with pytest.raises(ValueError):
        tiles.tile_origins(100, 300)


def test_cloud_buffer_and_assessable():
    scl = np.full((128, 128), 4); scl[64, 64] = 9
    inv = tiles.invalid_mask(scl, buffer_m=100, pixel_m=10)
    assert inv[64, 74] and not inv[64, 76]  # 10 px = 100 m buffer, not more
    assert not tiles.assessable(np.ones((128, 128), bool))
    assert tiles.assessable(np.zeros((128, 128), bool))


def test_object_split_across_tiles_counts_once():
    shape = (192, 192)
    truth = np.zeros(shape); truth[90:100, 60:70] = 1.0  # scar on the seam of tiles
    o = tiles.tile_origins(*shape)
    probs = [truth[r:r + 128, c:c + 128] for r, c in o]
    lab, keep = tiles.objects(tiles.mosaic(shape, o, probs), 0.5)
    assert len(keep) == 1
    assert (lab == keep[0]).sum() >= 4


def test_min_object_size_and_invalid_ignored():
    p = np.zeros((20, 20)); p[2:4, 2:4] = 1; p[10, 10] = 1
    assert len(tiles.objects(p, 0.5, min_px=4)[1]) == 1
    inv = np.zeros_like(p, bool); inv[2:4, 2:4] = True
    assert len(tiles.objects(p, 0.5, min_px=4, invalid=inv)[1]) == 0


def test_agreement_requires_mask_overlap():
    a = np.zeros((50, 50), bool); a[:10, :10] = True
    b = np.zeros((50, 50), bool); b[40:, 40:] = True
    assert decisions.decide(True, True, True, decisions.mask_iou(a, b)) == 'DISAGREEMENT'
    assert decisions.decide(True, True, True, decisions.mask_iou(a, a)) == 'MODEL_AGREEMENT'


def test_state_machine_rules():
    assert decisions.decide(False, True, True, 1.0) == 'UNASSESSABLE'
    assert decisions.decide(True, False, False, 0.0) == 'NO_VISIBLE_DETECTION'
    with pytest.raises(ValueError):
        decisions.decide(True, True, True, 1.0, review={'source': 'model_b', 'verdict': 'positive'})
    assert decisions.decide(True, True, True, 1.0, review={'source': 'orthophoto', 'verdict': 'positive'}) == 'VERIFIED_POSITIVE'
    assert decisions.decide(True, True, True, 1.0, review={'source': 'human_review', 'verdict': 'unclear'}) == 'UNKNOWN'


def test_one_to_one_matching():
    r = np.zeros((30, 30), bool); r[5:15, 5:15] = True
    m, up, ur = decisions.match_one_to_one([r, r.copy()], [r])  # duplicate prediction matches once
    assert len(m) == 1 and len(up) == 1 and ur == []


def test_update_admission():
    c = CFG['update']
    s = {'state': 'MODEL_AGREEMENT', 'split': 'train'}
    with pytest.raises(ValueError):
        update.admit(s, c)  # auto_train_pseudolabels=false
    on = {**c, 'auto_train_pseudolabels': True}
    assert update.admit(s, on)['weight'] == 0.2
    for bad in ({'state': 'UNKNOWN', 'split': 'train'}, {'state': 'VERIFIED_POSITIVE', 'split': 'test'},
                {'state': 'MODEL_AGREEMENT', 'split': 'calibration'}):
        with pytest.raises(ValueError):
            update.admit(bad, on)


def test_pseudo_share_cap():
    on = {**CFG['update'], 'auto_train_pseudolabels': True}
    ver = [update.admit({'state': 'VERIFIED_POSITIVE', 'split': 'train'}, on)] * 9
    ps = update.admit({'state': 'MODEL_AGREEMENT', 'split': 'train'}, on)
    update.check_cycle(ver + [ps], on)  # 0.2/9.2 < 10 %
    with pytest.raises(ValueError):
        update.check_cycle(ver[:1] + [ps] * 3, on)
    with pytest.raises(ValueError):
        update.check_cycle([ps], on)


def test_namespace_guard():
    paths.assert_writable(paths.DATA / 'x.parquet')
    for p in ('data/v04/x', 'reports/baseline/BASELINE_MANIFEST.json', 'archive/x'):
        with pytest.raises(PermissionError):
            paths.assert_writable(ROOT / p)


def test_b_has_no_cross_inputs():
    assert list(inspect.signature(models.LRASPP.forward).parameters) == ['self', 'x']
    assert list(inspect.signature(models.UNetResNet18.forward).parameters) == ['self', 'x']
    for n in 'ab':
        net = models.build(n).eval()
        assert net(torch.zeros(1, 3, 128, 128)).shape == (1, 1, 128, 128)


def test_ignore_pixels_do_not_contribute():
    lg = torch.randn(1, 1, 8, 8); t = torch.zeros(1, 1, 8, 8)
    ign = torch.zeros(1, 1, 8, 8, dtype=torch.bool); ign[..., :4] = True
    a = models.masked_loss(lg, t, ign)
    lg2 = lg.clone(); lg2[..., :4] += 100
    assert torch.allclose(a, models.masked_loss(lg2, t, ign))
    t2 = t.clone(); t2[..., :4] = 1
    assert torch.allclose(a, models.masked_loss(lg, t2, ign))


def test_can_overfit_tiny_synthetic_sample_on_cpu():
    torch.manual_seed(0)
    x = torch.rand(2, 3, 64, 64); y = torch.zeros(2, 1, 64, 64); y[:, :, 20:40, 20:40] = 1
    x[:, :, 20:40, 20:40] += 0.8
    net = models.build('a'); opt = torch.optim.AdamW(net.parameters(), 1e-3)
    ign = torch.zeros_like(y, dtype=torch.bool)
    first = None
    for _ in range(60):
        opt.zero_grad(); loss = models.masked_loss(net(x), y, ign); loss.backward(); opt.step()
        first = first if first is not None else loss.item()
    assert loss.item() < 0.5 * first
