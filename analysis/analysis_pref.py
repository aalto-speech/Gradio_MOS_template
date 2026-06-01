import json
import sys
import numpy as np
import pandas as pd
from collections import defaultdict
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
    # pair_key -> {'a_pref': int, 'no_pref': int, 'b_pref': int}
    pair_counts = defaultdict(lambda: {'a_pref': 0, 'no_pref': 0, 'b_pref': 0,
                                       'ref_system': None, 'target_system': None})

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

        if score < 0:
            pair_counts[pair_key]['a_pref'] += 1
        elif score == 0:
            pair_counts[pair_key]['no_pref'] += 1
        else:
            pair_counts[pair_key]['b_pref'] += 1

    pref_results = {}
    for pair_key, counts in pair_counts.items():
        total = counts['a_pref'] + counts['no_pref'] + counts['b_pref']
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
        }

    return pref_results


def print_preference_results(pref_results):
    """Print formatted preference results"""
    print("\nPREFERENCE RESULTS")
    print("-" * 90)
    header = f"{'System A (ref)':<22} {'System B (target)':<22} {'A pref':>8} {'No pref':>8} {'B pref':>8} {'N':>5}"
    print(header)
    print("-" * 90)

    for pair_key in sorted(pref_results.keys()):
        data = pref_results[pair_key]
        a_str = f"{data['a_pref_ratio']:.1%}" if data['a_pref_ratio'] is not None else "N/A"
        n_str = f"{data['no_pref_ratio']:.1%}" if data['no_pref_ratio'] is not None else "N/A"
        b_str = f"{data['b_pref_ratio']:.1%}" if data['b_pref_ratio'] is not None else "N/A"

        print(f"{data['ref_system']:<22} {data['target_system']:<22} {a_str:>8} {n_str:>8} {b_str:>8} {data['n_samples']:>5}")


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
        })

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")


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

    return pref_results


if __name__ == "__main__":
    directory_path = sys.argv[1]

    try:
        pref_results = main(directory_path)
    except Exception as e:
        print(f"Error: {e}")
