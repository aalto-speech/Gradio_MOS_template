import json
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
from scipy import stats
import os
import glob


def check_file_attention_checks(results):
    """Check if all attention checks in a single file are correct"""
    attention_tests = [r for r in results if r['test_type'] == 'attention']

    for test in attention_tests:
        audio_path = test['reference_audio']
        expected_score = int(os.path.splitext(os.path.basename(audio_path))[0].split("_")[-1])
        actual_score = test['score']

        if expected_score != actual_score:
            return False

    return True


def load_and_filter_json_files(directory_path):
    """Load JSON files, filter out those that fail attention checks"""
    json_files = glob.glob(os.path.join(directory_path, "*.json"))

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in directory: {directory_path}")

    valid_results = []
    total_files = 0
    failed_files = 0

    print(f"Processing {len(json_files)} JSON files...")

    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            results = data.get('results', [])
            total_files += 1

            if check_file_attention_checks(results):
                participant_id = data.get('user_id', os.path.basename(file_path))
                for result in results:
                    if result['test_type'] == 'empha_pref':
                        result['participant_id'] = participant_id
                        result['file_path'] = file_path
                        valid_results.append(result)
            else:
                failed_files += 1
                print(f"Excluded: {os.path.basename(file_path)} (failed attention checks)")

        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            failed_files += 1
            continue

    valid_files = total_files - failed_files
    print(f"\nFiltering summary:")
    print(f"Total files: {total_files}")
    print(f"Valid files: {valid_files}")
    print(f"Excluded files: {failed_files}")
    print(f"Success rate: {valid_files/total_files:.1%}")
    print(f"Valid empha_pref results: {len(valid_results)}")

    return valid_results


def analyze_preference(results):
    """Analyze preference results per system pair.

    score semantics (after swap normalization):
      -1 = ref_system (A) preferred
       0 = no preference
       1 = target_system (B) preferred
    """
    pair_counts = defaultdict(lambda: {'a_pref': 0, 'no_pref': 0, 'b_pref': 0,
                                       'ref_system': None, 'target_system': None,
                                       'scores': []})

    for result in results:
        ref_system = result['ref_system']
        target_system = result['target_system']

        if not ref_system or not target_system:
            continue

        pair_key = (ref_system, target_system)
        pair_counts[pair_key]['ref_system'] = ref_system
        pair_counts[pair_key]['target_system'] = target_system

        # Normalize score: when swapped, the participant saw target on the left and ref on
        # the right, so a positive raw score means ref was preferred — flip to canonical form.
        score = result['score'] if not result['swap'] else -result['score']
        pair_counts[pair_key]['scores'].append(score)

        if score < 0:
            pair_counts[pair_key]['a_pref'] += 1
        elif score == 0:
            pair_counts[pair_key]['no_pref'] += 1
        else:
            pair_counts[pair_key]['b_pref'] += 1

    rng = np.random.default_rng(42)

    pref_results = {}
    for pair_key, counts in pair_counts.items():
        total = counts['a_pref'] + counts['no_pref'] + counts['b_pref']
        a_votes, tie_votes, b_votes = counts['a_pref'], counts['no_pref'], counts['b_pref']
        scores_arr = np.array(counts['scores'])

        # Split-ties exact binomial: each tie counts as half a vote for each side.
        # Doubling everything keeps the counts integer: tie -> 1 vote each side.
        b_votes_doubled = 2 * b_votes + tie_votes
        total_doubled = 2 * total
        if total_doubled > 0:
            # H0: P(B) <= 0.5 -- is B significantly preferred over A?
            p_split_ties = stats.binomtest(b_votes_doubled, total_doubled, p=0.5, alternative='greater').pvalue
            # H0: P(A) <= 0.5 -- is A significantly preferred over B?
            a_votes_doubled = 2 * a_votes + tie_votes
            p_split_ties_a_gt_b = stats.binomtest(a_votes_doubled, total_doubled, p=0.5, alternative='greater').pvalue
        else:
            p_split_ties = 1.0
            p_split_ties_a_gt_b = 1.0

        # Bootstrap 95% CI on the win-rate (ties excluded).
        # Each resample recomputes win-rate = b_pref / (a_pref + b_pref).
        decisive_scores = scores_arr[scores_arr != 0]
        if len(decisive_scores) > 0:
            boot = rng.choice(decisive_scores, size=(5000, len(decisive_scores)), replace=True)
            boot_winrate = (boot > 0).mean(axis=1)
            ci_low, ci_high = np.percentile(boot_winrate, [2.5, 97.5])
        else:
            ci_low, ci_high = None, None

        pref_results[pair_key] = {
            'ref_system': counts['ref_system'],
            'target_system': counts['target_system'],
            'a_pref_count': counts['a_pref'],
            'no_pref_count': counts['no_pref'],
            'b_pref_count': counts['b_pref'],
            'a_pref_ratio': counts['a_pref'] / total if total > 0 else None,
            'no_pref_ratio': counts['no_pref'] / total if total > 0 else None,
            'b_pref_ratio': counts['b_pref'] / total if total > 0 else None,
            'n_samples': total,
            'p_split_ties': p_split_ties,
            'p_split_ties_a_gt_b': p_split_ties_a_gt_b,
            'ci_low': ci_low,
            'ci_high': ci_high,
        }

    return pref_results


def significance_stars(p):
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return 'ns'


def _p_cell(p):
    return f"{p:.4f}{significance_stars(p)}"


def print_preference_results(pref_results):
    """Print formatted preference results"""
    print("\nPREFERENCE RESULTS")
    print("-" * 130)
    header = (f"{'System A (ref)':<22} {'System B (target)':<22} {'A pref':>8} {'No pref':>8} {'B pref':>8} "
              f"{'±95% CI':>8} {'N':>5} {'B>A (SplitTie)':>16} {'A>B (SplitTie)':>16}")
    print(header)
    print("-" * 130)

    for pair_key in sorted(pref_results.keys()):
        data = pref_results[pair_key]
        a_str  = f"{data['a_pref_ratio']:.1%}" if data['a_pref_ratio'] is not None else "N/A"
        n_str  = f"{data['no_pref_ratio']:.1%}" if data['no_pref_ratio'] is not None else "N/A"
        b_str  = f"{data['b_pref_ratio']:.1%}" if data['b_pref_ratio'] is not None else "N/A"
        ci_str = (f"{(data['ci_high'] - data['ci_low']) / 2:.1%}"
                  if data['ci_low'] is not None else "N/A")
        s_str   = _p_cell(data['p_split_ties'])
        sa_str  = _p_cell(data['p_split_ties_a_gt_b'])

        print(f"{data['ref_system']:<22} {data['target_system']:<22} {a_str:>8} {n_str:>8} {b_str:>8} "
              f"{ci_str:>8} {data['n_samples']:>5} {s_str:>16} {sa_str:>16}")


def plot_preference_results(pref_results, output_file='preference_plot.png'):
    """Save one figure per target system (System B).

    Output files are derived from output_file by inserting the system name before
    the extension, e.g. preference_plot_F5TTS.png.
    """
    groups = defaultdict(list)
    for pair_key, data in pref_results.items():
        groups[data['target_system']].append(data)

    system_b_order = {'F5TTS': 0, 'F5TTS-DP-SFT': 1, 'F5TTS-DP-GRPO': 2}
    sorted_groups = sorted(groups.items(), key=lambda x: system_b_order.get(x[0], 99))

    win_color  = '#4CAF50'
    tie_color  = '#B0BEC5'
    loss_color = '#EF5350'

    system_b_display = {
        'F5TTS':         r'$\mathcal{M}_{\mathrm{TTS-SFT}}$',
        'F5TTS-DP-SFT':  r'$\mathcal{M}_{\mathrm{TTS-DP-SFT}}$',
        'F5TTS-DP-GRPO': 'EmphTTS',
    }
    system_b_role = {
        'F5TTS':         'Ablation system',
        'F5TTS-DP-SFT':  'Ablation system',
        'F5TTS-DP-GRPO': 'Proposed system',
    }
    ref_display = {'Qwen3-TTS': 'Qwen3-TTS-VD'}

    def _sig_superscript(p_b_gt_a, p_a_gt_b):
        # Golden metric for significance: split-tie binomial test.
        # '*' marks B significantly preferred over A; '+' marks A significantly preferred over B.
        marks = ''
        if p_b_gt_a < 0.05:
            marks += r'$^{*}$'
        if p_a_gt_b < 0.05:
            marks += r'$^{+}$'
        return marks

    base, ext = os.path.splitext(output_file)

    for system_b, pairs in sorted_groups:
        pairs = sorted(pairs, key=lambda p: (p['ref_system'] == 'GroundTruth', p['ref_system']))
        n = len(pairs)
        labels = [ref_display.get(p['ref_system'], p['ref_system'])
                  + _sig_superscript(p['p_split_ties'], p['p_split_ties_a_gt_b'])
                  for p in pairs]
        wins   = [p['b_pref_ratio'] for p in pairs]
        ties   = [p['no_pref_ratio'] for p in pairs]
        losses = [p['a_pref_ratio'] for p in pairs]
        bottoms_tie = losses
        bottoms_win = [l + t for l, t in zip(losses, ties)]

        fig, ax = plt.subplots(figsize=(7, 0.55 * n + 1.4))

        y = np.arange(n)
        height = 0.72

        ax.barh(y, losses, height, color=loss_color)
        ax.barh(y, ties,   height, left=bottoms_tie, color=tie_color)
        ax.barh(y, wins,   height, left=bottoms_win, color=win_color)

        for j, (l, t, w) in enumerate(zip(losses, ties, wins)):
            if l > 0.07:
                ax.text(l / 2,         j, f'{l:.0%}', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
            if t > 0.07:
                ax.text(l + t / 2,     j, f'{t:.0%}', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
            if w > 0.07:
                ax.text(l + t + w / 2, j, f'{w:.0%}', ha='center', va='center', fontsize=11, color='white', fontweight='bold')

        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=14)
        ax.set_ylim(-0.5, n - 0.5)
        ax.set_ylabel('Baselines', fontsize=10)
        ax.set_xlim(0, 1)
        ax.set_xlabel('Share of listeners', fontsize=10)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
        ax.axvline(x=0.5, color='black', linestyle='--', linewidth=0.8, alpha=0.4)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        role = system_b_role.get(system_b, 'Proposed system')
        proposed_label = 'Prefers ablation' if role == 'Ablation system' else 'Prefers proposed'
        legend_handles = [
            mpatches.Patch(color=loss_color, label='Prefers baseline'),
            mpatches.Patch(color=tie_color,  label='No preference'),
            mpatches.Patch(color=win_color,  label=proposed_label),
        ]
        ax.legend(handles=legend_handles, loc='lower center',
                  bbox_to_anchor=(0.5, -0.28), ncol=3, frameon=False, fontsize=10)

        ax.set_title(f'{role}: {system_b_display.get(system_b, system_b)}',
                     fontweight='bold', fontsize=12, pad=10)

        plt.tight_layout()
        path = f'{base}_{system_b}{ext}'
        plt.savefig(path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"Plot saved to {path}")


def save_preference_to_csv(pref_results, output_file='preference_results.csv'):
    """Save preference results to CSV"""
    rows = []
    for pair_key in sorted(pref_results.keys()):
        data = pref_results[pair_key]
        rows.append({
            'ref_system': data['ref_system'],
            'target_system': data['target_system'],
            'a_pref_count': data['a_pref_count'],
            'no_pref_count': data['no_pref_count'],
            'b_pref_count': data['b_pref_count'],
            'a_pref_ratio': data['a_pref_ratio'],
            'no_pref_ratio': data['no_pref_ratio'],
            'b_pref_ratio': data['b_pref_ratio'],
            'n_samples': data['n_samples'],
            'p_split_ties_b_gt_a': data['p_split_ties'],
            'sig_b_gt_a': significance_stars(data['p_split_ties']),
            'p_split_ties_a_gt_b': data['p_split_ties_a_gt_b'],
            'sig_a_gt_b': significance_stars(data['p_split_ties_a_gt_b']),
            'ci_low': data['ci_low'],
            'ci_high': data['ci_high'],
        })

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")


def winning_utterances(results, ref_system, target_system, output_file=None):
    """Return utterances where target_system wins the majority vote against ref_system.

    Majority = more votes for proposed than for baseline among all valid listeners.
    Saves a CSV if output_file is given.
    """
    pair_results = [
        r for r in results
        if r['ref_system'] == ref_system and r['target_system'] == target_system
    ]

    utterance_votes = defaultdict(lambda: {'baseline': 0, 'tie': 0, 'proposed': 0, 'transcript': ''})

    for r in pair_results:
        score = r['score'] if not r['swap'] else -r['score']
        # Derive utterance ID from whichever audio path is the target (canonical side)
        audio_path = r['target_audio'] if not r['swap'] else r['reference_audio']
        utt_id = os.path.splitext(os.path.basename(audio_path))[0]

        if score < 0:
            utterance_votes[utt_id]['baseline'] += 1
        elif score == 0:
            utterance_votes[utt_id]['tie'] += 1
        else:
            utterance_votes[utt_id]['proposed'] += 1

        if r.get('transcript'):
            utterance_votes[utt_id]['transcript'] = r['transcript']

    rows = []
    for utt_id, counts in sorted(utterance_votes.items()):
        total = counts['baseline'] + counts['tie'] + counts['proposed']
        rows.append({
            'utterance': utt_id,
            'proposed_votes': counts['proposed'],
            'tie_votes': counts['tie'],
            'baseline_votes': counts['baseline'],
            'total_votes': total,
            'winner': 'proposed' if counts['proposed'] > counts['baseline'] else
                      ('baseline' if counts['baseline'] > counts['proposed'] else 'tie'),
            'transcript': counts['transcript'],
        })

    df = pd.DataFrame(rows)
    winners = df[df['winner'] == 'proposed'].sort_values('proposed_votes', ascending=False)

    print(f"\nWinning utterances for {target_system} vs {ref_system}: {len(winners)} / {len(df)}")
    print(winners[['utterance', 'proposed_votes', 'tie_votes', 'baseline_votes', 'transcript']].to_string(index=False))

    if output_file:
        winners.to_csv(output_file, index=False)
        print(f"Saved to {output_file}")

    return winners


def main(directory_path):
    """Main analysis function"""
    valid_results = load_and_filter_json_files(directory_path)

    test_counts = defaultdict(int)
    for result in valid_results:
        test_counts[result['test_type']] += 1

    print(f"\nTest type breakdown (valid files only):")
    for test_type, count in test_counts.items():
        print(f"  {test_type}: {count}")

    pref_results = analyze_preference(valid_results)
    print_preference_results(pref_results)
    save_preference_to_csv(pref_results, output_file=f"{directory_path}/preference_results.csv")
    plot_preference_results(pref_results, output_file=f"{directory_path}/preference_plot.pdf")

    # winning_utterances(
    #     valid_results,
    #     ref_system='GroundTruth',
    #     target_system='F5TTS-DP-GRPO',
    #     output_file=f"{directory_path}/winning_utterances_GRPO_vs_GT.csv",
    # )

    return pref_results


if __name__ == "__main__":
    directory_path = sys.argv[1]

    try:
        pref_results = main(directory_path)
    except Exception as e:
        print(f"Error: {e}")
