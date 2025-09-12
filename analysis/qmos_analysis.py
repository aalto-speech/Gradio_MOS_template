import json
import sys
import numpy as np
import pandas as pd
from collections import defaultdict
import os
import glob
import argparse

def check_file_attention_checks(results):
    """Check if all attention checks in a single file are correct
    
    Mapping: bad=1, poor=2, fair=3, good=4, excellent=5
    """
    quality_to_score = {
        'bad': 1,
        'poor': 2,
        'fair': 3,
        'good': 4,
        'excellent': 5
    }
    
    attention_tests = [r for r in results if r['test_type'] == 'no_reference_attention']
    
    for test in attention_tests:
        audio_path = test['target_audio']
        # Extract expected quality from filename (e.g., "reference_bad_1.wav" -> "bad")
        basename = os.path.splitext(os.path.basename(audio_path))[0]
        expected_quality = basename.split("_")[-1]
        
        if expected_quality is None:
            print(f"Warning: Could not extract quality from filename: {audio_path}")
            continue
            
        expected_score = quality_to_score[expected_quality]
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
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Handle empty files or files with just whitespace
            if not content:
                print(f"Skipping {os.path.basename(file_path)}: Empty file")
                continue
                
            # Try to parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as json_err:
                print(f"Skipping {os.path.basename(file_path)}: Invalid JSON - {json_err}")
                continue
            
            # Handle case where JSON contains just an empty string
            if isinstance(data, str):
                print(f"Skipping {os.path.basename(file_path)}: File contains empty string, no data to process")
                continue
            
            # Check if data has expected structure (should be a dict)
            if not isinstance(data, dict):
                print(f"Skipping {os.path.basename(file_path)}: Expected JSON object, got {type(data).__name__}")
                continue
                
            results = data.get('results', [])
            if not isinstance(results, list):
                print(f"Skipping {os.path.basename(file_path)}: 'results' field should be a list, got {type(results).__name__}")
                continue
                
            total_files += 1
            
            # Check if this file passes attention checks
            if check_file_attention_checks(results):
                # File passes - include only MOS results
                participant_id = data.get('user_id', os.path.basename(file_path))
                mos_count = 0
                for result in results:
                    if result.get('test_type') == 'QMOS':
                        result['participant_id'] = participant_id
                        result['file_path'] = file_path
                        valid_results.append(result)
                        mos_count += 1
                
                if mos_count == 0:
                    print(f"Warning: {os.path.basename(file_path)} has no MOS results")
            else:
                # File fails attention checks - exclude entirely
                failed_files += 1
                print(f"Excluded: {os.path.basename(file_path)} (failed attention checks)")
                
        except Exception as e:
            print(f"Skipping {os.path.basename(file_path)}: {e}")
            continue
    
    valid_files = total_files - failed_files
    print(f"\nFiltering summary:")
    print(f"Total files: {total_files}")
    print(f"Valid files: {valid_files}")
    print(f"Excluded files: {failed_files}")
    print(f"Success rate: {valid_files/total_files:.1%}")
    print(f"Valid MOS results: {len(valid_results)}")
    
    return valid_results

def calculate_boxplot_metrics(data):
    """Calculate box plot metrics (min, Q1, median, Q3, max)"""
    if len(data) == 0:
        return None
    
    data_array = np.array(data)
    return {
        'min': float(np.min(data_array)),
        'q1': float(np.percentile(data_array, 25)),
        'median': float(np.median(data_array)),
        'q3': float(np.percentile(data_array, 75)),
        'max': float(np.max(data_array)),
        'mean': float(np.mean(data_array)),
        'std': float(np.std(data_array, ddof=1)) if len(data_array) > 1 else 0.0,
        'n_samples': len(data_array)
    }

def analyze_mos_by_utterance(results):
    """Analyze MOS results aggregated by utterance (target_audio)"""
    utterance_scores = defaultdict(list)
    
    # Group scores by target_audio (utterance identifier)
    for result in results:
        if result['test_type'] != 'QMOS':
            continue
            
        target_audio = result['target_audio']
        score = result['score']
        utterance_scores[target_audio].append(score)
    
    # Calculate average score per utterance
    per_utterance_averages = {}
    for utterance, scores in utterance_scores.items():
        per_utterance_averages[utterance] = {
            'average_score': float(np.mean(scores)),
            'n_ratings': len(scores),
            'all_scores': scores
        }
    
    # Calculate overall box plot metrics from per-utterance averages
    all_averages = [data['average_score'] for data in per_utterance_averages.values()]
    boxplot_metrics = calculate_boxplot_metrics(all_averages)
    
    return per_utterance_averages, boxplot_metrics

def save_results_to_json(per_utterance_averages, boxplot_metrics, output_file='mos_results.json'):
    """Save results to JSON file"""
    results = {
        'summary': {
            'total_utterances': len(per_utterance_averages),
            'boxplot_metrics': boxplot_metrics
        },
        'per_utterance_averages': per_utterance_averages
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")

def print_summary(per_utterance_averages, boxplot_metrics):
    """Print summary of results"""
    print("\nMOS ANALYSIS SUMMARY")
    print("-" * 50)
    print(f"Total utterances analyzed: {len(per_utterance_averages)}")
    
    if boxplot_metrics:
        print(f"\nBox Plot Metrics (based on per-utterance averages):")
        print(f"  Mean:     {boxplot_metrics['mean']:.3f}")
        print(f"  Median:   {boxplot_metrics['median']:.3f}")
        print(f"  Std Dev:  {boxplot_metrics['std']:.3f}")
        print(f"  Min:      {boxplot_metrics['min']:.3f}")
        print(f"  Q1:       {boxplot_metrics['q1']:.3f}")
        print(f"  Q3:       {boxplot_metrics['q3']:.3f}")
        print(f"  Max:      {boxplot_metrics['max']:.3f}")

def main(directory_path, output_path=None):
    """Main analysis function"""
    # Load and filter files based on attention checks
    valid_results = load_and_filter_json_files(directory_path)
    
    if not valid_results:
        print("No valid MOS results found after filtering.")
        return None, None
    
    # Count test types
    test_counts = defaultdict(int)
    for result in valid_results:
        test_counts[result['test_type']] += 1
    
    print(f"\nTest type breakdown (valid files only):")
    for test_type, count in test_counts.items():
        print(f"  {test_type}: {count}")
    
    # Analyze MOS by utterance
    per_utterance_averages, boxplot_metrics = analyze_mos_by_utterance(valid_results)
    
    # Print summary and save results
    print_summary(per_utterance_averages, boxplot_metrics)
    
    # Determine output file location
    if output_path:
        if os.path.isdir(output_path):
            output_file = os.path.join(output_path, "mos_results.json")
        else:
            output_file = output_path
    else:
        output_file = os.path.join(directory_path, "mos_results.json")
    
    save_results_to_json(per_utterance_averages, boxplot_metrics, output_file)
    
    return per_utterance_averages, boxplot_metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Analyze QMOS (Quality Mean Opinion Score) test results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qmos_analysis.py /path/to/json/files
  python qmos_analysis.py /path/to/json/files -o /path/to/output/
  python qmos_analysis.py /path/to/json/files --output results.json
        """
    )
    
    parser.add_argument(
        '-d', '--directory_path',
        help='Directory containing JSON files with QMOS test results'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        help='Output file path or directory. If directory, saves as "mos_results.json" inside it. If not specified, saves in the input directory.'
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.directory_path):
        print(f"Error: Directory '{args.directory_path}' does not exist")
        sys.exit(1)
    
    # Validate output path if provided
    if args.output_path:
        output_dir = os.path.dirname(args.output_path) if not os.path.isdir(args.output_path) else args.output_path
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        per_utterance_averages, boxplot_metrics = main(args.directory_path, args.output_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)