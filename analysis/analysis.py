import json
import sys
import numpy as np
import pandas as pd
from scipy import stats
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
            
            # Check if this file passes attention checks
            if check_file_attention_checks(results):
                # File passes - include only CMOS and SMOS results
                participant_id = data.get('user_id', os.path.basename(file_path))
                for result in results:
                    if result['test_type'] in ['CMOS', 'SMOS']:
                        result['participant_id'] = participant_id
                        result['file_path'] = file_path
                        valid_results.append(result)
            else:
                # File fails attention checks - exclude entirely
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
    print(f"Valid CMOS/SMOS results: {len(valid_results)}")
    
    return valid_results

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

def save_results_to_csv(cmos_results, smos_results, output_file='tts_results.csv'):
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


def analyze_per_utterance(results):
    """Analyze CMOS and SMOS results per utterance and target system"""
    # Structure: utterance -> target_system -> {'cmos_scores': [], 'smos_scores': []}
    utterance_data = defaultdict(lambda: defaultdict(lambda: {'cmos_scores': [], 'smos_scores': []}))
    
    for result in results:
        if result['test_type'] not in ['CMOS', 'SMOS']:
            continue
            
        # Extract utterance identifier from the audio path
        # Assuming the utterance ID is in the filename
        # Determine target system (use ref_system if swap is True)
        if result['swap']:
            target_system = result['ref_system']
            audio_path = result['reference_audio']
            score = -score
        else:
            target_system = result['target_system']
            audio_path = result['target_audio']
        # Extract utterance ID from filename (adjust this logic based on your filename format)
        utterance = os.path.splitext(os.path.basename(audio_path))[0]
        
        score = result['score']
            
        if not target_system:
            continue
            
        # Store scores by test type and target system
        if result['test_type'] == 'CMOS':
            utterance_data[utterance][target_system]['cmos_scores'].append(score)
        elif result['test_type'] == 'SMOS':
            utterance_data[utterance][target_system]['smos_scores'].append(score)
    
    # Filter to keep only utterances that have both CMOS and SMOS for both systems
    # First, identify all target systems
    all_systems = set()
    for utterance, systems_data in utterance_data.items():
        all_systems.update(systems_data.keys())
    
    if len(all_systems) < 2:
        print(f"Warning: Found only {len(all_systems)} target systems. Need at least 2 systems.")
        return {}
    
    # Calculate averages and filter
    utterance_results = {}
    for utterance, systems_data in utterance_data.items():
        # Check if this utterance has data for all systems
        if len(systems_data) != len(all_systems):
            continue
            
        # Check if each system has both CMOS and SMOS scores
        valid_utterance = True
        system_results = {}
        
        for system, data in systems_data.items():
            cmos_scores = data['cmos_scores']
            smos_scores = data['smos_scores']
            
            # Must have both CMOS and SMOS scores for this system
            if not cmos_scores or not smos_scores:
                valid_utterance = False
                break
                
            # Calculate averages
            cmos_avg = np.mean(cmos_scores)
            smos_avg = np.mean(smos_scores) + 3  # Apply +3 adjustment
            
            system_results[system] = {
                'averaged_CMOS': cmos_avg,
                'number_of_CMOS_scores': len(cmos_scores),
                'averaged_SMOS': smos_avg,
                'number_of_SMOS_scores': len(smos_scores)
            }
        
        # Only include utterance if it has complete data for all systems
        if valid_utterance:
            utterance_results[utterance] = {
                'utterance': utterance,
                'systems': system_results
            }
    
    return utterance_results

def save_utterance_results_to_json(utterance_results, output_file='utterance_results.json'):
    """Save per-utterance results to JSON file"""
    # Convert to the requested format
    results_list = []
    
    for utterance, data in utterance_results.items():
        utterance_entry = {'utterance': utterance}
        
        # Add system-specific results
        for system, system_data in data['systems'].items():
            system_key = system.replace(' ', '_')  # Replace spaces with underscores for cleaner keys
            utterance_entry[f'{system_key}_averaged_CMOS'] = system_data['averaged_CMOS']
            utterance_entry[f'{system_key}_number_of_CMOS_scores'] = system_data['number_of_CMOS_scores']
            utterance_entry[f'{system_key}_averaged_SMOS'] = system_data['averaged_SMOS']
            utterance_entry[f'{system_key}_number_of_SMOS_scores'] = system_data['number_of_SMOS_scores']
        
        results_list.append(utterance_entry)
    
    with open(output_file, 'w') as f:
        json.dump(results_list, f, indent=2)
    
    print(f"Per-utterance results saved to {output_file}")
    print(f"Total utterances with complete data: {len(results_list)}")
    
    return results_list

def main(directory_path):
    """Main analysis function"""
    # Load and filter files based on attention checks
    valid_results = load_and_filter_json_files(directory_path)
    
    # Count test types
    test_counts = defaultdict(int)
    for result in valid_results:
        test_counts[result['test_type']] += 1
    
    print(f"\nTest type breakdown (valid files only):")
    for test_type, count in test_counts.items():
        print(f"  {test_type}: {count}")
    
    # Analyze CMOS and SMOS
    cmos_results = analyze_cmos(valid_results)
    smos_results = analyze_smos(valid_results)
    
    # Print and save results
    print_results(cmos_results, smos_results)
    save_results_to_csv(cmos_results, smos_results, output_file=f"{directory_path}/tts_results.csv")

    # Analyze per utterance
    utterance_results = analyze_per_utterance(valid_results)
    utterance_json = save_utterance_results_to_json(utterance_results, 
                                                   output_file=f"{directory_path}/utterance_results.json")
    
    return cmos_results, smos_results

if __name__ == "__main__":
    directory_path = sys.argv[1]
    
    try:
        cmos_results, smos_results = main(directory_path)
    except Exception as e:
        print(f"Error: {e}")
