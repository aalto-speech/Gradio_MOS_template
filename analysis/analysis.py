import json
import sys
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
import os
import glob

def load_all_json_files(directory_path):
    """Load all JSON files from a directory and aggregate results"""
    json_files = glob.glob(os.path.join(directory_path, "*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in directory: {directory_path}")
    
    all_results = []
    participant_count = 0
    
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            results = data.get('results', [])
            all_results.extend(results)
            participant_count += 1
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    
    print(f"Loaded {len(all_results)} results from {participant_count} participants")
    return all_results

def calculate_confidence_interval(data, confidence=0.95):
    """Calculate mean and 95% confidence interval"""
    if len(data) == 0:
        return None, None, None
    
    mean = np.mean(data)
    sem = stats.sem(data)
    ci = stats.t.interval(confidence, len(data)-1, loc=mean, scale=sem)
    return mean, ci[0], ci[1]

def analyze_cmos(results):
    """Analyze CMOS results per target system"""
    cmos_data = defaultdict(list)
    
    for result in results:
        if result['test_type'] != 'CMOS':
            continue
            
        score = result['score']
        
        if result['swap']:
            target_system = result['ref_system']
            score = -score
        else:
            target_system = result['target_system']
            
        if target_system:
            cmos_data[target_system].append(score)
    
    # Calculate statistics
    cmos_results = {}
    for system, scores in cmos_data.items():
        mean, ci_lower, ci_upper = calculate_confidence_interval(scores)
        cmos_results[system] = {
            'mean': mean,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'n_samples': len(scores)
        }
    
    return cmos_results

def analyze_smos(results):
    """Analyze SMOS results per target system and add 3 to means"""
    smos_data = defaultdict(list)
    
    for result in results:
        if result['test_type'] != 'SMOS':
            continue
            
        score = result['score']
        
        if result['swap']:
            target_system = result['ref_system']
            score = -score
        else:
            target_system = result['target_system']
            
        if target_system:
            smos_data[target_system].append(score)
    
    # Calculate statistics and add 3
    smos_results = {}
    for system, scores in smos_data.items():
        mean, ci_lower, ci_upper = calculate_confidence_interval(scores)
        
        # Add 3 to all values
        adjusted_mean = mean + 3 if mean is not None else None
        adjusted_ci_lower = ci_lower + 3 if ci_lower is not None else None
        adjusted_ci_upper = ci_upper + 3 if ci_upper is not None else None
        
        smos_results[system] = {
            'mean': adjusted_mean,
            'ci_lower': adjusted_ci_lower,
            'ci_upper': adjusted_ci_upper,
            'n_samples': len(scores)
        }
    
    return smos_results

def print_results(cmos_results, smos_results):
    """Print formatted results"""
    print("\nCMOS RESULTS")
    print("-" * 60)
    print(f"{'System':<20} {'Mean':<8} {'95% CI':<20} {'N':<5}")
    print("-" * 60)
    
    for system, data in sorted(cmos_results.items()):
        mean = data['mean']
        ci_lower = data['ci_lower']
        ci_upper = data['ci_upper']
        n = data['n_samples']
        
        ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]" if ci_lower is not None else "N/A"
        mean_str = f"{mean:.3f}" if mean is not None else "N/A"
        
        print(f"{system:<20} {mean_str:<8} {ci_str:<20} {n:<5}")
    
    print("\nSMOS RESULTS (adjusted +3)")
    print("-" * 60)
    print(f"{'System':<20} {'Mean':<8} {'95% CI':<20} {'N':<5}")
    print("-" * 60)
    
    for system, data in sorted(smos_results.items()):
        mean = data['mean']
        ci_lower = data['ci_lower']
        ci_upper = data['ci_upper']
        n = data['n_samples']
        
        ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]" if ci_lower is not None else "N/A"
        mean_str = f"{mean:.3f}" if mean is not None else "N/A"
        
        print(f"{system:<20} {mean_str:<8} {ci_str:<20} {n:<5}")

def save_results_to_csv(cmos_results, smos_results, output_file='results/tts_results.csv'):
    """Save results to CSV"""
    all_results = []
    
    for system, data in cmos_results.items():
        all_results.append({
            'test_type': 'CMOS',
            'system': system,
            'mean': data['mean'],
            'ci_lower': data['ci_lower'],
            'ci_upper': data['ci_upper'],
            'n_samples': data['n_samples']
        })
    
    for system, data in smos_results.items():
        all_results.append({
            'test_type': 'SMOS',
            'system': system,
            'mean': data['mean'],
            'ci_lower': data['ci_lower'],
            'ci_upper': data['ci_upper'],
            'n_samples': data['n_samples']
        })
    
    df = pd.DataFrame(all_results)
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

def main(directory_path):
    """Main analysis function for directory of JSON files"""
    # Load all results
    all_results = load_all_json_files(directory_path)
    
    # Count test types
    test_counts = defaultdict(int)
    for result in all_results:
        test_counts[result['test_type']] += 1
    
    print("Test type breakdown:")
    for test_type, count in test_counts.items():
        print(f"  {test_type}: {count}")
    
    # Analyze
    cmos_results = analyze_cmos(all_results)
    smos_results = analyze_smos(all_results)
    
    # Print and save results
    print_results(cmos_results, smos_results)
    save_results_to_csv(cmos_results, smos_results, output_file=f"{directory_path}/tts_results.csv")
    
    return cmos_results, smos_results

if __name__ == "__main__":
    directory_path = sys.argv[1]
    
    try:
        cmos_results, smos_results = main(directory_path)
    except Exception as e:
        print(f"Error: {e}")