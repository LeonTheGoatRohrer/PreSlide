"""Figures, comparison table and aggregate web bundle from reports/extremwetter_v01/comparisons.json.

summary.md is written by hand from these stored numbers; every number in it appears in comparisons.md.
"""
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..common import read_json, write_json  # noqa: E402
from ..v05.paths import sha  # noqa: E402
from ..v05.pipeline import load  # noqa: E402
from .paths import CONFIG, DATA, REPORT, WEB, config  # noqa: E402

BLUE, ORANGE, AQUA, GREY, INK, MUTED = '#2a78d6', '#eb6834', '#1baf7a', '#c9c8c2', '#0b0b0b', '#52514e'
END_LABEL = {-2: 'bis 07:00 des Vortags (primär, vor t0)', -1: 'bis 07:00 des Ereignistags (kann Regen nach t0 enthalten)',
             0: 'inkl. Ereignistag (enthält Regen nach t0)'}
SETTING_LABEL = {
    'primary': 'Primär: Episoden gleich gewichtet', 'events_weighted': 'Ereignisse gleich gewichtet',
    'without_stanz': 'ohne Stanz-Sturm 25.07.2016', 'hangmure': 'nur reine Hangmure', 'hangmure_gemischt': 'nur Hangmure gemischt',
    'lockergesteinsrutschung': 'nur Lockergesteinsrutschung', 'reference_1961_2025': 'Referenz 1961–2025',
    'reference_2011_2025': 'Referenz 2011–2025', 'end_minus1_may_contain_post_t0': 'Fenster bis 07:00 Ereignistag (Sekundär)',
    'end_0_contains_post_t0': 'Fenster inkl. Ereignistag (Sekundär, nach t0)', 'placebo': 'Placebo: 3 Tage, 60 Tage früher',
}


def style(ax):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GREY)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color='#ecebe7', linewidth=0.8)
    ax.set_axisbelow(True)


def rows_of(data, setting):
    return sorted((r for r in data['rows'] if r['setting'] == setting), key=lambda r: r['window_days'])


def fig_windows(data, path):
    """Mean percentile rank per window length for the three window ends, with episode-bootstrap intervals."""
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=150)
    style(ax)
    prim = rows_of(data, 'primary')
    ks = [r['window_days'] for r in prim]
    x = np.arange(len(ks))
    lo = [r['null_mean_pr_95'][0] for r in prim]
    hi = [r['null_mean_pr_95'][1] for r in prim]
    ax.fill_between(x, lo, hi, color=GREY, alpha=0.5, linewidth=0, label='Zufallsbereich (95 %, Pseudo-Fälle)')
    for setting, end, color, dx in (('primary', -2, BLUE, -0.12), ('end_minus1_may_contain_post_t0', -1, AQUA, 0),
                                    ('end_0_contains_post_t0', 0, ORANGE, 0.12)):
        rs = rows_of(data, setting)
        y = [r['mean_pr'] for r in rs]
        err = np.array([[r['mean_pr'] - r['mean_pr_ci95'][0], r['mean_pr_ci95'][1] - r['mean_pr']] for r in rs]).T
        ax.errorbar(x + dx, y, yerr=err, fmt='o', color=color, ms=6, lw=1.6, capsize=0, label=END_LABEL[end],
                    linestyle='-' if end == -2 else ':')
    ax.axhline(0.5, color=MUTED, lw=1, ls='--')
    ax.set_xticks(x, [f'{k} Tag' if k == 1 else f'{k} Tage' for k in ks])
    ax.set_ylim(0.3, 1.0)
    ax.set_ylabel('mittlerer Perzentilrang am Ort', color=INK, fontsize=10)
    ax.set_title('Niederschlag vor dem Ereignis im Vergleich zu denselben Kalendertagen anderer Jahre\n'
                 f'(explorativ; {prim[0]["n_events"]} Ereignisse, {prim[0]["n_episodes"]} Episoden; Intervalle: Bootstrap über Episoden)',
                 fontsize=10, color=INK, loc='left')
    ax.legend(fontsize=8, frameon=False, loc='lower right')
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_sensitivity(data, path, window_days):
    """Forest plot of all registered settings for one window length."""
    rows = [r for r in data['rows'] if r['window_days'] == window_days and r['setting'] != 'placebo']
    rows += [r for r in data['rows'] if r['setting'] == 'placebo']
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(rows) + 1.2), dpi=150)
    style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color='#ecebe7', linewidth=0.8)
    for i, r in enumerate(rows):
        y = len(rows) - 1 - i
        color = ORANGE if r['setting'] == 'end_0_contains_post_t0' else (GREY if r['setting'] == 'placebo' else BLUE)
        ax.plot(r['null_mean_pr_95'], [y, y], color=GREY, lw=6, alpha=0.6, solid_capstyle='butt')
        ax.plot(r['mean_pr_ci95'], [y, y], color=color, lw=1.8)
        ax.plot(r['mean_pr'], y, 'o', color=color if r['setting'] != 'placebo' else MUTED, ms=6)
        ax.text(1.005, y, f"{r['mean_pr']:.2f}  ({r['n_events']} Ereignisse / {r['n_episodes']} Ep.)",
                va='center', fontsize=8, color=MUTED, transform=ax.get_yaxis_transform())
    ax.axvline(0.5, color=MUTED, lw=1, ls='--')
    ax.set_yticks(range(len(rows))[::-1], [SETTING_LABEL[r['setting']] for r in rows], fontsize=8.5, color=INK)
    ax.set_xlim(0.3, 1.0)
    ax.set_xlabel('mittlerer Perzentilrang (grau: Zufallsbereich 95 %)', fontsize=9, color=INK)
    ax.set_title(f'Alle registrierten Vergleiche, {window_days}-Tage-Fenster (explorativ)', fontsize=10, color=INK, loc='left')
    fig.tight_layout()
    fig.subplots_adjust(right=0.72)
    fig.savefig(path)
    plt.close(fig)


def episode_ranks(scores, window_days):
    """Episode-mean percentile ranks for the primary end and the end including the event day."""
    return scores.groupby('episode').agg(n=(f'pr_{window_days}d_end-2', 'size'), primary=(f'pr_{window_days}d_end-2', 'mean'),
                                         event_day=(f'pr_{window_days}d_end0', 'mean'))


def fig_histogram(scores, path, window_days):
    """Distribution of episode-mean percentile ranks (the independent unit) against the uniform expectation."""
    ep = episode_ranks(scores, window_days)
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), dpi=150, sharey=True)
    bins = np.linspace(0, 1, 11)
    for ax, column, color, title in ((axes[0], 'primary', BLUE, 'Primär: bis 07:00 des Vortags (vor t0)'),
                                     (axes[1], 'event_day', ORANGE, 'Sekundär: inkl. Ereignistag (nach t0)')):
        style(ax)
        ax.hist(ep[column], bins=bins, color=color, edgecolor='white', linewidth=2)
        ax.axhline(len(ep) / 10, color=MUTED, lw=1, ls='--')
        ax.set_title(title, fontsize=9, color=INK, loc='left')
        ax.set_xlabel(f'mittlerer Rang der Episode ({window_days} Tage)', fontsize=9, color=INK)
    axes[0].set_ylabel(f'Episoden (von {len(ep)})', fontsize=9, color=INK)
    axes[0].text(0.02, len(ep) / 10 + 1.4, 'erwartet ohne Zusammenhang', fontsize=7.5, color=MUTED)
    fig.suptitle('Zwei Muster: Vorregen über Tage oder Regen erst am Ereignistag (explorativ)', fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fmt_ci(ci, digits=2):
    if ci is None or any(v is None for v in ci):
        return '[–; unbegrenzt]' if ci and ci[0] is not None else '–'
    return f'[{ci[0]:.{digits}f}; {ci[1]:.{digits}f}]'


def table(data):
    head = ('| Vergleich | Fenster | Ereignisse / Episoden | mittl. Rang [95 %] | Zufall 95 % | p (einseitig) | '
            '> Q95: Anteil [95 %] (erw.) | Ratenverh. Q95 [95 %] | > Q99: Anteil (erw.) |\n|---|---|---|---|---|---|---|---|---|')
    lines = [head]
    for r in data['rows']:
        rr = '–' if r['rate_ratio_q95'] is None else f"{r['rate_ratio_q95']:.1f}"
        lines.append(f"| {SETTING_LABEL[r['setting']]} | {r['window_days']} d (Ende {r['last_label_offset_days']}) | "
                     f"{r['n_events']} / {r['n_episodes']} | {r['mean_pr']:.3f} {fmt_ci(r['mean_pr_ci95'], 3)} | "
                     f"{fmt_ci(r['null_mean_pr_95'], 3)} | {r['p_one_sided']:.4f} | {r['share_q95']:.2f} {fmt_ci(r['share_q95_ci95'])} "
                     f"({r['expected_q95']:.3f}) | {rr} {fmt_ci(r['rate_ratio_q95_ci95'], 1)} | {r['share_q99']:.2f} ({r['expected_q99']:.3f}) |")
    return '\n'.join(lines)


def web_bundle(data):
    """Aggregates only: no event IDs, coordinates or per-event values."""
    keep = ('setting', 'window_days', 'last_label_offset_days', 'years', 'weighting', 'n_events', 'n_episodes', 'mean_pr',
            'mean_pr_ci95', 'null_mean_pr', 'null_mean_pr_95', 'p_one_sided', 'share_q95', 'share_q95_ci95', 'expected_q95',
            'p_share_q95_one_sided', 'rate_ratio_q95', 'rate_ratio_q95_ci95', 'share_q99', 'share_q99_ci95', 'expected_q99',
            'p_share_q99_one_sided', 'rate_ratio_q99', 'rate_ratio_q99_ci95', 'p_holm_primary_windows')
    meta = data['meta']
    return {
        'version': 'extremwetter_v01', 'explorativ': True,
        'frage': 'War der Niederschlag vor dem dokumentierten Ereignistag am Ereignisort extremer als an denselben Kalendertagen anderer Jahre ohne dokumentiertes Ereignis?',
        'design': 'Case-Crossover am selben 1-km-Gitterpunkt (GeoSphere SPARTACUS, Tagesniederschlag), Referenz ±15 Kalendertage in 1991–2025 ohne Ereignisjahr',
        'einheiten': {'ereignisse': meta['n_events'], 'episoden': meta['n_episodes'], 'stanz_ereignisse': meta['stanz_events']},
        'fensterende': {str(k): v for k, v in END_LABEL.items()},
        'vergleiche_bezeichnung': SETTING_LABEL,
        'vergleiche': [{k: r.get(k) for k in keep} for r in data['rows']],
        'hinweise': [
            'Explorativ: alle 423 Ereignisse wurden bereits in V0.4/V0.5 verwendet. Eine Bestätigung braucht neue Ereignisse (Bestätigungsplan).',
            'Zusammenhang, keine Kausalität. Nach großen Unwettern werden Rutschungen vollständiger gemeldet (Meldebias); das kann den Zusammenhang verstärken.',
            'Effektive Stichprobe = Zahl der zeitlichen Episoden, nicht der Ereignisse.',
            'Primärfenster enden um 07:00 des Vortags; Regen in den letzten Stunden vor dem Ereignis fehlt dort.',
        ],
        'config_sha256': sha(CONFIG),
    }


def main():
    cfg = config()
    data = read_json(REPORT / 'comparisons.json')
    if data['meta']['config_sha256'] != sha(CONFIG):
        raise RuntimeError('comparisons.json was computed with another configuration')
    scores = load(DATA / f'run_{sha(CONFIG)[:12]}' / 'event_scores.parquet')
    k = cfg['exposure']['primary_window_days']
    fig_windows(data, REPORT / 'F1_fenster.png')
    fig_sensitivity(data, REPORT / f'F2_sensitivitaet_{k}d.png', k)
    fig_histogram(scores, REPORT / f'F3_verteilung_{k}d.png', k)
    (REPORT / 'comparisons.md').write_text(
        '# extremwetter_v01 – alle registrierten Vergleiche (explorativ)\n\n'
        'Erzeugt aus `comparisons.json` (`python -m preslide.extremwetter report`). Effektive Stichprobe = Episoden. '
        'p = einseitig gegen die Pseudo-Fall-Nullverteilung (5000 Ziehungen). Intervalle: Bootstrap über Episoden (2000). '
        '"erw." = erwarteter Anteil ohne Zusammenhang.\n\n' + table(data) + '\n', encoding='utf-8', newline='\n')
    write_json(WEB, web_bundle(data))
    print('report written')
