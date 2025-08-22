#!/usr/bin/env python3
"""
TTS Audio Test Generator - Local Filesystem Version
Generates CMOS and SMOS test pairs from local filesystem audio samples
"""

import json
import random
import yaml
from pathlib import Path
from typing import List, Dict, Any
import os
import hydra
from omegaconf import DictConfig

class TTSLocalTestGenerator:
    def __init__(self):
        """Initialize the local filesystem test generator"""
        self.audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
    
    def _get_audio_files(self, folder_path: Path, system_name: str, root_path: Path) -> List[Dict[str, str]]:
        """Get all audio files from a local folder and include system and path information"""
        
        print(f"Scanning folder: {folder_path}")
        
        if not folder_path.exists():
            print(f"Warning: Folder {folder_path} does not exist")
            return []
        
        if not folder_path.is_dir():
            print(f"Warning: {folder_path} is not a directory")
            return []
        
        # Find all audio files in the directory
        audio_files = []
        try:
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.audio_extensions:
                    # Create relative path from root directory
                    try:
                        relative_path = file_path.relative_to(root_path)
                        complete_path = str(relative_path).replace('\\', '/')  # Normalize path separators
                    except ValueError:
                        # If file is not under root_path, use system_name/filename
                        complete_path = f"{system_name}/{file_path.name}"
                    
                    audio_files.append({
                        'name': file_path.name,
                        'local_path': str(file_path),
                        'system': system_name,
                        'complete_path': complete_path
                    })
        except PermissionError:
            print(f"Warning: Permission denied accessing {folder_path}")
        except Exception as e:
            print(f"Warning: Error scanning {folder_path}: {e}")
        
        print(f"Total audio files found in {system_name}: {len(audio_files)}")
        return audio_files
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _generate_cmos_pairs(
            self, config: Dict[str, Any], system_files: Dict[str, List[Dict]], num_pairs: int
        ) -> List[List[Dict]]:
        """Generate CMOS test pairs - matching files between systems"""
        all_pairs = []
        
        # Get CMOS test configurations from the new format
        if 'tests' not in config or 'CMOS' not in config['tests']:
            return all_pairs
        
        cmos_configs = config['tests']['CMOS']
        
        print(f"\nGenerating CMOS pairs...")
        for pair_config in cmos_configs:
            ref_system = pair_config['ref']
            target_system = pair_config['target']
            
            if ref_system not in system_files or target_system not in system_files:
                print(f"Warning: Missing system files for CMOS pair {ref_system} vs {target_system}")
                continue
            
            ref_files = system_files[ref_system]
            target_files = system_files[target_system]

            target_files_dict = {file['name']: file for file in target_files}
            
            if not ref_files or not target_files:
                print(f"Warning: Empty audio files for CMOS pair {ref_system} vs {target_system}")
                continue
            
            # Generate pairs for this specific comparison
            pairs_for_this_comparison = []
            max_possible_pairs = min(len(ref_files), len(target_files), num_pairs)
            pairs_generated = 0
            
            while pairs_generated < max_possible_pairs:
                ref_file = ref_files[pairs_generated]
                target_file = target_files_dict.get(ref_file['name'])

                if not target_file:
                    print(f"Warning: No matching target file found for {ref_file['name']} in {target_system}")
                    pairs_generated += 1
                    continue
                
                pairs_for_this_comparison.append({
                    "reference": ref_file['local_path'],
                    "target": target_file['local_path'],
                    "type": "CMOS",
                    "ref_system": ref_system,
                    "target_system": target_system,
                    "ref_filename": ref_file['complete_path'],
                    "target_filename": target_file['complete_path']
                })
                pairs_generated += 1
            
            # Add this comparison's pairs as a separate list
            all_pairs.append(pairs_for_this_comparison)
            print(f"Generated {len(pairs_for_this_comparison)} CMOS pairs for {ref_system} vs {target_system}")
        
        return all_pairs
    
    def _generate_smos_pairs(self, config: Dict[str, Any], system_files: Dict[str, List[Dict]], 
                            num_pairs: int) -> List[List[Dict]]:
        """Generate SMOS test pairs - pair audio files based on metalst file"""
        all_pairs = []
        
        # Get SMOS test configurations from the new format
        if 'tests' not in config or 'SMOS' not in config['tests']:
            return all_pairs
        
        smos_configs = config['tests']['SMOS']
        
        print(f"\nGenerating SMOS pairs...")
        for pair_config in smos_configs:
            ref_system = pair_config['ref']
            target_system = pair_config['target']
            metalst_path = pair_config.get('metalst')
            
            if not metalst_path:
                print(f"Warning: Missing 'metalst' field for SMOS pair {ref_system} vs {target_system}")
                continue
            
            if ref_system not in system_files or target_system not in system_files:
                print(f"Warning: Missing system files for SMOS pair {ref_system} vs {target_system}")
                continue
            
            ref_files = system_files[ref_system]
            target_files = system_files[target_system]
            
            if not ref_files or not target_files:
                print(f"Warning: Empty audio files for SMOS pair {ref_system} vs {target_system}")
                continue
            
            # Create filename lookup dictionaries for faster searching
            ref_files_dict = {file['name']: file for file in ref_files}
            target_files_dict = {file['name']: file for file in target_files}
            
            # Generate pairs for this specific comparison
            pairs_for_this_comparison = []
            
            try:
                # Read the metalst file
                with open(metalst_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                pairs_generated = 0
                for line_num, line in enumerate(lines):
                    if pairs_generated >= num_pairs:
                        break
                    
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    # Split by tab
                    fields = line.split('\t')
                    if len(fields) < 4:
                        print(f"Warning: Line {line_num} in {metalst_path} has fewer than 4 fields, skipping")
                        continue
                    
                    ref_filename = os.path.basename(fields[0])
                    target_filename = os.path.basename(fields[3])
                    
                    # Find the reference file
                    if ref_filename not in ref_files_dict:
                        print(f"Warning: Reference file '{ref_filename}' not found in {ref_system}")
                        continue
                    
                    # Find the target file
                    if target_filename not in target_files_dict:
                        print(f"Warning: Target file '{target_filename}' not found in {target_system}")
                        continue
                    
                    ref_file = ref_files_dict[ref_filename]
                    target_file = target_files_dict[target_filename]
                                        
                    pairs_for_this_comparison.append({
                        "reference": ref_file['local_path'],
                        "target": target_file['local_path'],
                        "type": "SMOS",
                        "ref_system": ref_system,
                        "target_system": target_system,
                        "ref_filename": ref_file['complete_path'],
                        "target_filename": target_file['complete_path'],
                        "metalst_line": line_num
                    })
                    pairs_generated += 1
                
                # Add this comparison's pairs as a separate list
                all_pairs.append(pairs_for_this_comparison)
                print(f"Generated {pairs_generated} SMOS pairs for {ref_system} vs {target_system} from {metalst_path}")
                
            except FileNotFoundError:
                print(f"Error: Meta list file '{metalst_path}' not found")
                continue
            except Exception as e:
                print(f"Error reading meta list file '{metalst_path}': {e}")
                continue
        
        return all_pairs
    
    def _generate_mos_pairs(self, config: Dict[str, Any], system_files: Dict[str, List[Dict]], 
                           num_pairs: int) -> List[List[Dict]]:
        """Generate MOS test cases - single audio evaluation (no reference needed)"""
        all_pairs = []
        
        # Get MOS test configurations from the new format
        if 'tests' not in config or 'MOS' not in config['tests']:
            return all_pairs
        
        mos_configs = config['tests']['MOS']
        
        print(f"\nGenerating MOS pairs...")
        for pair_config in mos_configs:
            # For MOS, we only need the target system (no reference)
            target_system = pair_config['target']
            
            if target_system not in system_files:
                print(f"Warning: Missing system files for MOS evaluation of {target_system}")
                continue
            
            target_files = system_files[target_system]
            
            if not target_files:
                print(f"Warning: Empty audio files for MOS evaluation of {target_system}")
                continue
            
            # Generate pairs for this specific evaluation
            pairs_for_this_evaluation = []
            
            # Sample random files for MOS evaluation
            max_possible_pairs = min(len(target_files), num_pairs)
            selected_files = random.sample(target_files, max_possible_pairs)
            
            for target_file in selected_files:
                pairs_for_this_evaluation.append({
                    "reference": None,  # No reference needed for MOS
                    "target": target_file['local_path'],
                    "system": target_system,
                    "type": "MOS",
                    "target_filename": target_file['complete_path']
                })
            
            # Add this evaluation's pairs as a separate list
            all_pairs.append(pairs_for_this_evaluation)
            print(f"Generated {len(selected_files)} MOS evaluations for {target_system}")
        
        return all_pairs
    
    def _get_supported_test_types(self) -> Dict[str, callable]:
        """Return mapping of supported test types to their generation methods"""
        return {
            'CMOS': self._generate_cmos_pairs,
            'SMOS': self._generate_smos_pairs,
            'MOS': self._generate_mos_pairs,
        }
    
    def _detect_test_types_from_config(self, config: Dict[str, Any]) -> List[str]:
        """Detect which test types are present in the configuration"""
        if 'tests' not in config:
            return []
        
        test_types = list(config['tests'].keys())
        return test_types
    
    def _load_system_files(self, config: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Load audio files for all systems from local filesystem"""
        root_path = Path(config['root_dir']).resolve()
        
        if not root_path.exists():
            print(f"Error: Root directory '{root_path}' does not exist")
            return {}
        
        if not root_path.is_dir():
            print(f"Error: Root path '{root_path}' is not a directory")
            return {}
        
        print(f"Root directory: {root_path}")
        
        # Get audio files for each system
        system_files = {}
        for system in config['systems']:
            try:
                system_path = root_path / system
                files = self._get_audio_files(system_path, system, root_path)
                system_files[system] = files
                print(f"Found {len(files)} audio files in {system}")
            except Exception as e:
                print(f"Warning: Error accessing system folder '{system}': {e}")
                system_files[system] = []
        
        return system_files
    
    def generate_test_pairs(self, config: Dict, output_path: str, num_pairs: int = 50):
        """Generate test pairs for all supported test types found in config"""
        
        # Load system files
        system_files = self._load_system_files(config)
        
        # Detect test types from config
        detected_test_types = self._detect_test_types_from_config(config)
        supported_test_types = self._get_supported_test_types()
        
        print(f"\nDetected test types in config: {detected_test_types}")
        
        # Generate test cases for each supported test type
        test_results = {}
        total_test_cases = 0
        
        for test_type in detected_test_types:
            if test_type in supported_test_types:
                print(f"Processing {test_type} test pairs...")
                generator_method = supported_test_types[test_type]
                pairs_list = generator_method(config, system_files, num_pairs)
                test_results[test_type] = pairs_list
                
                # Count total test cases across all comparison lists
                total_for_this_type = sum(len(comparison_list) for comparison_list in pairs_list)
                total_test_cases += total_for_this_type
                print(f"Generated {total_for_this_type} {test_type} pairs across {len(pairs_list)} comparisons")
            else:
                print(f"WARNING: Test type '{test_type}' is not supported!")
                print(f"Supported test types are: {list(supported_test_types.keys())}")
                print(f"Skipping '{test_type}' pairs...")
        
        if total_test_cases == 0:
            print("No test cases were generated. Please check your configuration.")
            return {}
        
        # Save to JSON file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(test_results, f, indent=4)
        
        print(f"\nGenerated {total_test_cases} total test cases")
        print(f"Output saved to: {output_file.resolve()}")
        
        # Print summary by test type
        for test_type, pairs_list in test_results.items():
            total_pairs = sum(len(comparison_list) for comparison_list in pairs_list)
            print(f"{test_type}: {total_pairs} pairs across {len(pairs_list)} comparisons")
        
        return test_results

@hydra.main(version_base=None, config_path="config", config_name=None)
def main(cfg: DictConfig) -> None:
    """Main function using Hydra for configuration management"""
    print("TTS Audio Test Generator - Local Filesystem Version")
    print("=" * 58)
    
    # Set random seed if provided
    if cfg.get('seed'):
        random.seed(cfg.seed)
        print(f"Using random seed: {cfg.seed}")
    
    # Create output directory if it doesn't exist
    output_path = Path(cfg.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize generator
    generator = TTSLocalTestGenerator()
    
    # Convert Hydra config to regular dict for compatibility
    config_dict = {
        'root_dir': cfg.root_dir,
        'systems': list(cfg.systems),
        'tests': dict(cfg.tests)
    }
    
    # Generate test pairs
    generator.generate_test_pairs(config_dict, cfg.output, cfg.num_pairs)

if __name__ == '__main__':
    main()
