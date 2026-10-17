"""Registry rules for susceptibility_v01. Pure functions on the configuration dict; no IO."""
from datetime import date

SEALED_FLAGS = ('train_allowed', 'tuning_allowed', 'feature_selection_allowed', 'threshold_selection_allowed')


def _arm_datasets(arms):
    for name, value in arms.items():
        if isinstance(value, list):
            yield name, value


def validate(cfg):
    """Raise ValueError listing every violated rule (sealed test isolation, negatives, DEM date, licences)."""
    errors = []
    reg = cfg['registry']
    datasets = reg['datasets']
    for key, d in datasets.items():
        if d['role'] not in reg['allowed_roles']:
            errors.append(f'{key}: role {d["role"]!r} not allowed')
        if not str(d.get('license') or '').strip():
            errors.append(f'{key}: licence missing')
        if d['role'] == 'sealed_blind_test':
            for flag in SEALED_FLAGS:
                if d.get(flag) is not False:
                    errors.append(f'{key}: sealed dataset must set {flag}=false')
            if d['negative_policy'] != 'presence_background':
                errors.append(f'{key}: sealed test must use presence_background')
        else:
            if d['negative_policy'] != 'inside_mapping_extent':
                errors.append(f'{key}: development negatives only inside a mapping extent')
            if not d['mapping_complete'] or not d.get('mapping_extent_layer'):
                errors.append(f'{key}: negatives inside a mapping extent need mapping_complete and an extent layer')
            first = d.get('earliest_event_date')
            if first and date.fromisoformat(cfg['dem']['acquisition_end']) > date.fromisoformat(first):
                errors.append(f'{key}: DEM acquired after the earliest event ({first}); DEM would contain the scar')
    for arm, members in _arm_datasets(cfg['arms']):
        for m in members:
            if m not in datasets:
                errors.append(f'arm {arm}: unknown dataset {m}')
            elif datasets[m]['role'] != 'development':
                errors.append(f'arm {arm}: {m} is not a development dataset')
    blind = cfg['south_tyrol_blind_test']
    if datasets.get(blind['dataset'], {}).get('role') != 'sealed_blind_test':
        errors.append('blind test dataset must have role sealed_blind_test')
    sub = blind['positive_subset']
    if set(sub['include_codes']) & set(sub['exclude_codes']):
        errors.append('blind test include and exclude codes overlap')
    ratio = cfg['sampling']['class_ratio_positive_to_background']
    if len(ratio) != 2 or any(not isinstance(r, int) or r < 1 for r in ratio):
        errors.append('class ratio must be two positive integers')
    if blind['background']['ratio'] != ratio:
        errors.append('blind test ratio differs from the registered sampling ratio')
    if cfg['splits']['gap_between_train_and_test_blocks_m'] >= cfg['splits']['block_size_m']:
        errors.append('block gap must be smaller than the block size')
    if errors:
        raise ValueError('; '.join(errors))
    return True


def apply_amendments(cfg, amendments):
    """Fill registered placeholders. An amendment may only set dotted paths whose registered value is null."""
    for am in sorted(amendments, key=lambda a: a['id']):
        for dotted, value in am['set'].items():
            *parents, leaf = dotted.split('.')
            node = cfg
            for p in parents:
                node = node[p]
            if leaf not in node:
                raise ValueError(f'amendment {am["id"]}: unknown path {dotted}')
            if node[leaf] is not None:
                raise ValueError(f'amendment {am["id"]}: {dotted} is already registered as {node[leaf]!r}')
            node[leaf] = value
    return cfg


def training_datasets(cfg, arm):
    """Datasets an arm may train on; the sealed blind test can never be returned."""
    members = cfg['arms'][arm]
    if not isinstance(members, list):
        raise ValueError(f'arm {arm} is derived, not a dataset list')
    datasets = cfg['registry']['datasets']
    out = [m for m in members if datasets[m]['role'] == 'development']
    if len(out) != len(members):
        raise ValueError(f'arm {arm} references a non-development dataset')
    return out
