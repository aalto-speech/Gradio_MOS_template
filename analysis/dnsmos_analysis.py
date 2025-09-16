import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import statistics
import numpy as np
import argparse
import matplotlib.pyplot as plt
from scipy.stats import spearmanr


def read_dnsmos_file(json_path: str) -> Optional[float]:
    """
    Read DNSMOS score from a JSON file.
    
    Args:
        json_path: Path to the JSON file
        
    Returns:
        DNSMOS score as float, or None if file doesn't exist or error occurs
    """
    try:
        if not os.path.exists(json_path):
            print(f"Warning: File not found: {json_path}")
            return None
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        dnsmos_score = data.get('dnsmos')
        if dnsmos_score is None:
            print(f"Warning: 'dnsmos' field not found in {json_path}")
            return None
            
        return float(dnsmos_score)
        
    except Exception as e:
        print(f"Error reading {json_path}: {str(e)}")
        return None


def process_single_item(item: dict) -> Tuple[Optional[str], Optional[float]]:
    """
    Process a single item to extract filename and DNSMOS score.
    
    Args:
        item: Dictionary containing target information
        
    Returns:
        Tuple of (filename_without_extension, dnsmos_score)
    """
    target = item.get('target')
    if not target:
        return None, None
        
    # Replace .mp3 with .json
    json_path = target.replace('.mp3', '.json')
    
    # Get filename without extension for the key
    filename = Path(target).stem
    
    # Read DNSMOS score
    dnsmos_score = read_dnsmos_file(json_path)
    
    return filename, dnsmos_score


def read_dnsmos_scores(json_file_path: str, max_workers: int = 4) -> Dict[str, float]:
    """
    Read DNSMOS scores from multiple files using multi-threading.
    
    Args:
        json_file_path: Path to the main JSON file
        max_workers: Maximum number of threads for parallel processing
        
    Returns:
        Dictionary with filename (without extension) as key and DNSMOS score as value
    """
    # Load the main JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading main JSON file: {str(e)}")
        return {}
    
    # Extract all items from QMOS list
    items = []
    qmos_data = data.get('QMOS', [])
    
    for sublist in qmos_data:
        if isinstance(sublist, list):
            items.extend(sublist)
        else:
            items.append(sublist)
    
    print(f"Found {len(items)} items to process")
    
    # Process items using multi-threading
    results = {}
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {
            executor.submit(process_single_item, item): item 
            for item in items
        }
        
        # Collect results
        for future in as_completed(future_to_item):
            filename, score = future.result()
            
            if filename and score is not None:
                results[filename] = score
            else:
                failed_count += 1
    
    print(f"Successfully processed {len(results)} files")
    if failed_count > 0:
        print(f"Failed to process {failed_count} files")
        
    return results


def calculate_boxplot_statistics(scores: Dict[str, float]) -> Dict[str, any]:
    """
    Calculate statistics needed for box plots.
    
    Args:
        scores: Dictionary of filename -> DNSMOS score
        
    Returns:
        Dictionary containing various statistics
    """
    if not scores:
        print("No scores to calculate statistics")
        return {}
    
    values = list(scores.values())
    
    # Basic statistics
    stats = {
        'count': len(values),
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
        'min': min(values),
        'max': max(values),
    }
    
    # Quartiles for box plot
    sorted_values = sorted(values)
    
    stats['q1'] = np.percentile(sorted_values, 25)
    stats['q3'] = np.percentile(sorted_values, 75)
    stats['iqr'] = stats['q3'] - stats['q1']
    
    # Whiskers (1.5 * IQR rule)
    lower_whisker = stats['q1'] - 1.5 * stats['iqr']
    upper_whisker = stats['q3'] + 1.5 * stats['iqr']
    
    # Actual whisker values (min/max within the whisker range)
    stats['lower_whisker'] = max(lower_whisker, stats['min'])
    stats['upper_whisker'] = min(upper_whisker, stats['max'])
    
    # Outliers
    outliers = [v for v in values if v < lower_whisker or v > upper_whisker]
    stats['outliers'] = outliers
    stats['outlier_count'] = len(outliers)
    
    # Additional percentiles
    stats['p5'] = np.percentile(sorted_values, 5)
    stats['p95'] = np.percentile(sorted_values, 95)
    
    return stats


def print_statistics(stats: Dict[str, any]) -> None:
    """
    Print formatted statistics.
    
    Args:
        stats: Statistics dictionary from calculate_boxplot_statistics
    """
    if not stats:
        print("No statistics to display")
        return
        
    print("\n" + "="*50)
    print("DNSMOS SCORE STATISTICS")
    print("="*50)
    print(f"Count: {stats['count']}")
    print(f"Mean: {stats['mean']:.4f}")
    print(f"Median: {stats['median']:.4f}")
    print(f"Standard Deviation: {stats['std_dev']:.4f}")
    print(f"Min: {stats['min']:.4f}")
    print(f"Max: {stats['max']:.4f}")
    print("\nBox Plot Statistics:")
    print(f"Q1 (25th percentile): {stats['q1']:.4f}")
    print(f"Q3 (75th percentile): {stats['q3']:.4f}")
    print(f"IQR: {stats['iqr']:.4f}")
    print(f"Lower Whisker: {stats['lower_whisker']:.4f}")
    print(f"Upper Whisker: {stats['upper_whisker']:.4f}")
    print(f"Outliers: {stats['outlier_count']} ({stats['outlier_count']/stats['count']*100:.1f}%)")
    print("\nAdditional Percentiles:")
    print(f"5th percentile: {stats['p5']:.4f}")
    print(f"95th percentile: {stats['p95']:.4f}")
    
    if stats['outliers']:
        print(f"\nOutlier values: {[f'{x:.4f}' for x in sorted(stats['outliers'])]}")


def get_boxplot_json(stats: Dict[str, any], indent: int = 2) -> str:
    """
    Generate a JSON string representation of box plot statistics.
    
    Args:
        stats: Statistics dictionary from calculate_boxplot_statistics
        indent: JSON indentation level (None for compact format)
        
    Returns:
        JSON string containing box plot data
    """
    if not stats:
        return json.dumps({"error": "No statistics available"}, indent=indent)
    
    boxplot_data = {
        "basic_stats": {
            "count": stats['count'],
            "mean": round(stats['mean'], 4),
            "median": round(stats['median'], 4),
            "std_dev": round(stats['std_dev'], 4),
            "min": round(stats['min'], 4),
            "max": round(stats['max'], 4)
        },
        "boxplot": {
            "q1": round(stats['q1'], 4),
            "median": round(stats['median'], 4),
            "q3": round(stats['q3'], 4),
            "iqr": round(stats['iqr'], 4),
            "lower_whisker": round(stats['lower_whisker'], 4),
            "upper_whisker": round(stats['upper_whisker'], 4)
        },
        "outliers": {
            "count": stats['outlier_count'],
            "percentage": round(stats['outlier_count']/stats['count']*100, 1),
            "values": [round(x, 4) for x in sorted(stats['outliers'])]
        },
        "percentiles": {
            "p5": round(stats['p5'], 4),
            "p25": round(stats['q1'], 4),
            "p50": round(stats['median'], 4),
            "p75": round(stats['q3'], 4),
            "p95": round(stats['p95'], 4)
        }
    }
    
    return json.dumps(boxplot_data, indent=indent)


def print_boxplot_json(stats: Dict[str, any], indent: int = 2) -> None:
    """
    Print box plot statistics as a JSON string.
    
    Args:
        stats: Statistics dictionary from calculate_boxplot_statistics
        indent: JSON indentation level (None for compact format)
    """
    json_string = get_boxplot_json(stats, indent)
    print("\nBox Plot Statistics (JSON):")
    print(json_string)


def read_mos_file(mos_file_path: str) -> Tuple[Dict[str, any], Dict[str, float]]:
    """
    Read MOS file and extract boxplot metrics and per-utterance scores.
    
    Args:
        mos_file_path: Path to the MOS JSON file
        
    Returns:
        Tuple of (boxplot_metrics, per_utterance_scores)
    """
    try:
        with open(mos_file_path, 'r', encoding='utf-8') as f:
            mos_data = json.load(f)
    except Exception as e:
        print(f"Error loading MOS file: {str(e)}")
        return {}, {}
    
    # Extract boxplot metrics
    # boxplot_metrics = mos_data.get('summary', {}).get('boxplot_metrics', {})
    
    # Extract per-utterance scores
    per_utterance_data = mos_data.get('per_utterance_averages', {})
    per_utterance_scores = {}
    
    for file_path, score_data in per_utterance_data.items():
        # Get filename without extension (to match DNSMOS keys)
        if score_data['n_ratings'] <= 1:
            continue  # Skip entries with insufficient ratings
        filename = Path(file_path).stem
        average_score = score_data['average_score']
        per_utterance_scores[filename] = float(average_score)
    
    print(f"Loaded MOS data: {len(per_utterance_scores)} utterances")

    boxplot_metrics = calculate_boxplot_statistics(per_utterance_scores)
    
    return boxplot_metrics, per_utterance_scores


def plot_boxplot_comparison(dns_stats: Dict[str, any], mos_metrics: Dict[str, any], output_path: str = "boxplot_comparison.png") -> None:
    """
    Plot side-by-side boxplots comparing DNSMOS and MOS scores.
    
    Args:
        dns_stats: DNSMOS statistics from calculate_boxplot_statistics
        mos_metrics: MOS boxplot metrics from MOS file
        output_path: Path to save the plot
    """
    if not dns_stats or not mos_metrics:
        print("Cannot create plot: missing statistics data")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    
    # Create box plot data structure for matplotlib
    box_data = [
        {
            'med': dns_stats['median'],
            'q1': dns_stats['q1'],
            'q3': dns_stats['q3'],
            'whislo': dns_stats['lower_whisker'],
            'whishi': dns_stats['upper_whisker'],
            'fliers': dns_stats['outliers']
        },
        {
            'med': mos_metrics['median'],
            'q1': mos_metrics['q1'],
            'q3': mos_metrics['q3'],
            'whislo': mos_metrics['min'],  # MOS file doesn't have whisker info, use min/max
            'whishi': mos_metrics['max'],
            'fliers': []  # No outlier info in MOS file
        }
    ]
    
    # Create the boxplot
    bp = ax.bxp(box_data, positions=[1, 2], patch_artist=True)
    # Set labels manually with larger font
    ax.set_xticks([1, 2])
    ax.set_xticklabels(['DNSMOS', 'MOS'], fontsize=18)
    
    # Customize colors
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Add statistics text with larger font
    ax.text(0.02, 0.98, f'DNSMOS: μ={dns_stats["mean"]:.3f}, σ={dns_stats["std_dev"]:.3f}', 
            transform=ax.transAxes, verticalalignment='top', fontsize=18,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    ax.text(0.02, 0.88, f'MOS: μ={mos_metrics["mean"]:.3f}, σ={mos_metrics["std_dev"]:.3f}', 
            transform=ax.transAxes, verticalalignment='top', fontsize=18,
            bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))
    
    # Set axis labels and title with larger fonts
    ax.set_ylabel('Score', fontsize=18)
    ax.set_title('DNSMOS vs MOS Score Comparison', fontsize=18)
    
    # Increase tick label font sizes
    ax.tick_params(axis='y', labelsize=18)
    
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Boxplot comparison saved to: {output_path}")
    plt.close()


def calculate_spearman_correlation(dns_scores: Dict[str, float], mos_scores: Dict[str, float]) -> Tuple[float, float, int]:
    """
    Calculate Spearman's rank correlation coefficient between DNSMOS and MOS scores.
    
    Args:
        dns_scores: Dictionary of filename -> DNSMOS score
        mos_scores: Dictionary of filename -> MOS score
        
    Returns:
        Tuple of (correlation_coefficient, p_value, n_samples)
    """
    # Find common filenames
    common_files = set(dns_scores.keys()) & set(mos_scores.keys())
    
    if len(common_files) == 0:
        print("No common files found between DNSMOS and MOS data")
        return 0.0, 1.0, 0
    
    print(f"Found {len(common_files)} common files for correlation analysis")
    
    # Extract paired scores
    dns_values = [dns_scores[filename] for filename in common_files]
    mos_values = [mos_scores[filename] for filename in common_files]
    
    # Calculate Spearman correlation
    correlation, p_value = spearmanr(dns_values, mos_values)
    
    return correlation, p_value, len(common_files)

def plot_dns_mos_scatter(dns_scores: Dict[str, float], 
                        mos_scores: Dict[str, float],
                        save_plot: Optional[str] = None,
                        figure_size: Tuple[int, int] = (10, 8)) -> None:
    """
    Create a scatter plot between DNSMOS and MOS scores without calculating correlation.
    
    Args:
        dns_scores: Dictionary of filename -> DNSMOS score
        mos_scores: Dictionary of filename -> MOS score
        save_plot: Optional filename to save the plot
        figure_size: Tuple of (width, height) for the figure size
    """
    # Find common filenames
    common_files = set(dns_scores.keys()) & set(mos_scores.keys())
    
    if len(common_files) == 0:
        print("No common files found between DNSMOS and MOS data")
        return
    
    # Extract paired scores
    dns_values = [dns_scores[filename] for filename in common_files]
    mos_values = [mos_scores[filename] for filename in common_files]
    
    # Create scatter plot
    plt.figure(figsize=figure_size)
    plt.scatter(dns_values, mos_values, alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    
    # Add trend line
    z = np.polyfit(dns_values, mos_values, 1)
    p = np.poly1d(z)
    plt.plot(sorted(dns_values), p(sorted(dns_values)), "r--", alpha=0.8, linewidth=2)
    
    # Customize the plot
    plt.xlabel('DNSMOS Scores', fontsize=12)
    plt.ylabel('MOS Scores', fontsize=12)
    plt.title(f'DNSMOS vs MOS Scores (n = {len(common_files)})', fontsize=14, pad=20)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot if filename provided
    plt.savefig(save_plot, dpi=300, bbox_inches='tight')
    print(f"Plot saved as: {save_plot}")

def plot_bland_altman(dns_scores: Dict[str, float], 
                     mos_scores: Dict[str, float],
                     save_plot: Optional[str] = None,
                     figure_size: Tuple[int, int] = (10, 8)) -> None:
    """
    Create a Bland-Altman plot between DNSMOS and MOS scores.
    
    Args:
        dns_scores: Dictionary of filename -> DNSMOS score
        mos_scores: Dictionary of filename -> MOS score  
        save_plot: Optional filename to save the plot
        figure_size: Tuple of (width, height) for the figure size
    """
    # Find common filenames
    common_files = set(dns_scores.keys()) & set(mos_scores.keys())
    
    if len(common_files) == 0:
        print("No common files found between DNSMOS and MOS data")
        return
    
    # Extract paired scores
    dns_values = np.array([dns_scores[filename] for filename in common_files])
    mos_values = np.array([mos_scores[filename] for filename in common_files])
    
    # Calculate Bland-Altman metrics
    mean_scores = (dns_values + mos_values) / 2
    diff_scores = dns_values - mos_values  # DNSMOS - MOS
    
    mean_diff = np.mean(diff_scores)
    std_diff = np.std(diff_scores, ddof=1)
    
    # 95% limits of agreement
    upper_loa = mean_diff + 1.96 * std_diff
    lower_loa = mean_diff - 1.96 * std_diff
    
    # Create Bland-Altman plot
    plt.figure(figsize=figure_size)
    
    # Scatter plot
    plt.scatter(mean_scores, diff_scores, alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    
    # Mean difference line
    plt.axhline(mean_diff, color='blue', linestyle='--', linewidth=2, 
                label=f'Mean difference: {mean_diff:.3f}')
    
    # Limits of agreement lines
    plt.axhline(upper_loa, color='red', linestyle='--', linewidth=2, 
                label=f'Upper LoA: {upper_loa:.3f}')
    plt.axhline(lower_loa, color='red', linestyle='--', linewidth=2, 
                label=f'Lower LoA: {lower_loa:.3f}')
    
    # Zero reference line
    plt.axhline(0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    
    # Customize the plot
    plt.xlabel('Average of DNSMOS and MOS Scores', fontsize=18)
    plt.ylabel('Difference (DNSMOS - MOS)', fontsize=18)
    plt.title(f'Bland-Altman Plot: DNSMOS vs MOS', fontsize=18, pad=20)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=18)
    
    # Add statistics text box
    stats_text = f'Mean ± SD: {mean_diff:.3f} ± {std_diff:.3f}\n95% LoA: [{lower_loa:.3f}, {upper_loa:.3f}]'
    # plt.text(0.05, 0.05, stats_text, transform=plt.gca().transAxes, 
    #          bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
    #          verticalalignment='bottom', fontsize=18)
    
    plt.tight_layout()
    
    # Save plot if filename provided
    if save_plot:
        plt.savefig(save_plot, dpi=300, bbox_inches='tight')
        print(f"Plot saved as: {save_plot}")
    else:
        plt.show()

def print_correlation_results(correlation: float, p_value: float, n_samples: int) -> None:
    """
    Print formatted correlation results.
    
    Args:
        correlation: Spearman correlation coefficient
        p_value: Statistical significance p-value
        n_samples: Number of samples used in correlation
    """
    print("\n" + "="*50)
    print("SPEARMAN CORRELATION ANALYSIS")
    print("="*50)
    print(f"Number of paired samples: {n_samples}")
    print(f"Spearman's ρ: {correlation:.4f}")
    print(f"P-value: {p_value:.6f}")
    
    # Interpretation
    if p_value < 0.001:
        significance = "highly significant (p < 0.001)"
    elif p_value < 0.01:
        significance = "significant (p < 0.01)"
    elif p_value < 0.05:
        significance = "significant (p < 0.05)"
    else:
        significance = "not significant (p ≥ 0.05)"
    
    if abs(correlation) >= 0.8:
        strength = "very strong"
    elif abs(correlation) >= 0.6:
        strength = "strong"
    elif abs(correlation) >= 0.4:
        strength = "moderate"
    elif abs(correlation) >= 0.2:
        strength = "weak"
    else:
        strength = "very weak"
    
    direction = "positive" if correlation > 0 else "negative"
    
    print(f"Correlation strength: {strength} {direction} correlation")
    print(f"Statistical significance: {significance}")
    
    if n_samples < 10:
        print("Warning: Small sample size may affect reliability of correlation analysis")


def process_dnsmos_data(json_file_path: str, max_workers: int = 4, print_stats: bool = True, print_json: bool = False) -> Tuple[Dict[str, float], Dict[str, any]]:
    """
    Complete pipeline to process DNSMOS data and calculate statistics.
    
    Args:
        json_file_path: Path to the main JSON file
        max_workers: Maximum number of threads for parallel processing
        print_stats: Whether to print statistics to console
        print_json: Whether to print statistics as JSON
        
    Returns:
        Tuple of (scores_dict, statistics_dict)
    """
    print("Reading DNSMOS scores...")
    scores = read_dnsmos_scores(json_file_path, max_workers)
    
    if not scores:
        print("No scores were successfully read. Please check your file paths and data.")
        return {}, {}
    
    print("\nCalculating statistics...")
    stats = calculate_boxplot_statistics(scores)
    
    if print_stats:
        print_statistics(stats)
    
    if print_json:
        print_boxplot_json(stats)
    
    return scores, stats


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Process DNSMOS scores from JSON files and calculate box plot statistics',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-i", '--input_test_list',
        type=str,
        help='Path to the input test list file containing dnsmos data'
    )

    parser.add_argument(
        '-m', '--mos_file',
        type=str,
        help='Path to the mos results file'
    )
    
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=4,
        help='Number of worker threads for parallel processing'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        help='Save JSON output to file instead of printing to console'
    )
    
    parser.add_argument(
        '--plot-output',
        type=str,
        default='boxplot_comparison.png',
        help='Output path for the boxplot comparison (default: boxplot_comparison.png)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.input_test_list:
        print("Error: Input test list file is required.")
        return 1
    
    if not os.path.exists(args.input_test_list):
        print(f"Error: Input file '{args.input_test_list}' does not exist.")
        return 1
    
    # Validate worker count
    if args.workers < 1:
        print("Error: Number of workers must be at least 1.")
        return 1
    
    print(f"Processing DNSMOS data from: {args.input_test_list}")
    print(f"Using {args.workers} worker threads")
    
    # Process the data
    scores = read_dnsmos_scores(args.input_test_list, max_workers=args.workers)
    
    if not scores:
        print("No scores were successfully read. Please check your file paths and data.")
        return 1
    
    stats = calculate_boxplot_statistics(scores)
    
    # Handle MOS file if provided
    mos_metrics = {}
    mos_scores = {}
    if args.mos_file:
        if not os.path.exists(args.mos_file):
            print(f"Warning: MOS file '{args.mos_file}' does not exist.")
        else:
            print(f"Loading MOS data from: {args.mos_file}")
            mos_metrics, mos_scores = read_mos_file(args.mos_file)
            
            if mos_metrics and stats:
                # Create boxplot comparison
                plot_boxplot_comparison(stats, mos_metrics, args.plot_output)
            
            if mos_scores and scores:
                # Calculate Spearman correlation
                correlation, p_value, n_samples = calculate_spearman_correlation(scores, mos_scores)
                print_correlation_results(correlation, p_value, n_samples)

                plot_bland_altman(scores, mos_scores, save_plot="dns_mos_bland_altman.png")
    
    # Handle JSON output
    if args.output_file:
        json_string = get_boxplot_json(stats, indent=2)
        
        try:
            with open(args.output_file, 'w') as f:
                f.write(json_string)
            print(f"\nJSON output saved to: {args.output_file}")
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            return 1
    
    # Always print JSON output
    print_boxplot_json(stats, indent=2)
    
    return 0


if __name__ == "__main__":
    main()