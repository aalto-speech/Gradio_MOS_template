#!/usr/bin/env python3
"""
TTS Audio Test Generator
Generates CMOS and SMOS test pairs from Google Drive audio samples
"""

import json
import pickle
import random
import yaml
from pathlib import Path
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import hydra
from omegaconf import DictConfig

# Scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class TTSTestGenerator:
    def __init__(self, credentials_path: str):
        """Initialize with Google Drive API credentials"""
        self.service = self._authenticate(credentials_path)
        self.audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
    
    def _authenticate(self, credentials_path: str):
        """Authenticate with Google Drive API"""
        creds = None
        token_path = 'test_list_builders/google_drive/credentials/token.pickle'
        
        # Check if we have saved credentials
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        
        return build('drive', 'v3', credentials=creds)
    
    def _find_folder_by_name(self, folder_name: str, parent_id: str = None) -> str:
        """Find folder ID by name, optionally within a parent folder"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        if not items:
            raise FileNotFoundError(f"Folder '{folder_name}' not found")
        
        return items[0]['id']
    
    def _get_audio_files(self, folder_id: str, system_name: str, root_path: str) -> List[Dict[str, str]]:
        """Get all audio files from a folder and include system and path information"""
        # Build query for audio files
        mime_types = [
            "audio/wav", "audio/mpeg", "audio/mp4", "audio/flac", 
            "audio/ogg", "audio/aac", "audio/x-wav"
        ]
        
        query = f"'{folder_id}' in parents and ("
        query += " or ".join([f"mimeType='{mt}'" for mt in mime_types])
        query += ")"
        
        # Get all files with pagination
        all_files = []
        page_token = None
        
        while True:
            # Request with pagination
            request_params = {
                'q': query,
                'fields': "nextPageToken, files(id, name, webViewLink, webContentLink)",
                'pageSize': 1000  # Maximum allowed page size
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            results = self.service.files().list(**request_params).execute()
            
            files = results.get('files', [])
            all_files.extend(files)
            
            # Check if there are more pages
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            
            print(f"Retrieved {len(all_files)} files so far for {system_name}...")
        
        # Filter by extension as backup (some files might not have correct MIME type)
        audio_files = []
        for file in all_files:
            file_path = Path(file['name'])
            if file_path.suffix.lower() in self.audio_extensions:

                download_link = f"https://drive.google.com/uc?id={file['id']}&export=download"
                
                # Create complete path from root_dir
                complete_path = f"{root_path}/{system_name}/{file['name']}"
                
                audio_files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'download_link': download_link,
                    'system': system_name,
                    'complete_path': complete_path  # Full path from root
                })
        
        print(f"Total audio files found in {system_name}: {len(audio_files)}")
        return audio_files
    
    def _make_file_shareable(self, file_id: str):
        """Make file shareable with link"""
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
        except Exception as e:
            print(f"Warning: Could not make file {file_id} shareable: {e}")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
        
    def _generate_cmos_pairs(
            self, config: Dict[str, Any], system_files: Dict[str, List[Dict]], num_pairs: int
        ) -> List[List[Dict]]:
        """Generate CMOS test pairs - random pairing with replacement until one folder is exhausted"""
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
            
            if not ref_files or not target_files:
                print(f"Warning: Empty audio files for CMOS pair {ref_system} vs {target_system}")
                continue
            
            # Generate pairs for this specific comparison
            pairs_for_this_comparison = []
            max_possible_pairs = min(len(ref_files), len(target_files), num_pairs)
            pairs_generated = 0
            
            while pairs_generated < max_possible_pairs:
                ref_file = ref_files[pairs_generated]
                target_file = list(filter(lambda f: f['name'] == ref_file['name'], target_files))[0] if target_files else None

                if not target_file:
                    print(f"Warning: No matching target file found for {ref_file['name']} in {target_system}")
                    continue
                
                pairs_for_this_comparison.append({
                    "reference": ref_file['download_link'],
                    "target": target_file['download_link'],
                    "type": "CMOS",
                    "ref_system": ref_system,
                    "target_system": target_system,
                    "ref_filename": ref_file['complete_path'],
                    "target_filename": target_file['complete_path']
                })
                pairs_generated += 1
            
            # Add this comparison's pairs as a separate list
            all_pairs.append(pairs_for_this_comparison)
            print(f"Generated {pairs_generated} CMOS pairs for {ref_system} vs {target_system}")
        
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
                        "reference": ref_file['download_link'],
                        "target": target_file['download_link'],
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
                    "target": target_file['download_link'],
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
        """Load audio files for all systems"""
        # Find root directory
        root_folder_id = self._find_folder_by_name(config['root_dir'])
        print(f"Found root folder: {config['root_dir']} (ID: {root_folder_id})")
        
        # Get audio files for each system
        system_files = {}
        for system in config['systems']:
            try:
                system_folder_id = self._find_folder_by_name(system, root_folder_id)
                files = self._get_audio_files(system_folder_id, system, config['root_dir'])  # Pass root_dir name
                system_files[system] = files
                print(f"Found {len(files)} audio files in {system}")
            except FileNotFoundError:
                print(f"Warning: System folder '{system}' not found")
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
        with open(output_path, 'w') as f:
            json.dump(test_results, f, indent=4)
        
        print(f"\nGenerated {total_test_cases} total test cases")
        print(f"Output saved to: {output_path}")
        
        # Print summary by test type
        for test_type, pairs_list in test_results.items():
            total_pairs = sum(len(comparison_list) for comparison_list in pairs_list)
            print(f"{test_type}: {total_pairs} pairs across {len(pairs_list)} comparisons")
        
        return test_results

@hydra.main(version_base=None, config_path="config", config_name=None)
def main(cfg: DictConfig) -> None:
    """Main function using Hydra for configuration management"""
    print("TTS Audio Test Generator")
    print("=" * 50)
    
    # Set random seed if provided
    if cfg.get('seed'):
        random.seed(cfg.seed)
        print(f"Using random seed: {cfg.seed}")
    
    # Create output directory if it doesn't exist
    output_path = Path(cfg.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize generator
    generator = TTSTestGenerator(cfg.credentials)
    
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