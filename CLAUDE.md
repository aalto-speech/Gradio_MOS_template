# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the app:**
```bash
uv run main.py --config-name CONFIG_NAME
# e.g. uv run main.py --config-name swedish_test
```

`main2.py` is an alternate entry point that exposes `num_attention` as a config field (instead of hardcoding 4).

**Build a test list (local filesystem):**
```bash
uv run test_list_builders/local_fs/generate.py \
    --config_name CONFIG_NAME \
    output="YOUR_OUTPUT_DIR" \
    root_dir="ROOT_DIR_FOR_ALL_SYSTEM_SAMPLES"
```

**Analyze results (MOS-based tests):**
```bash
uv run analysis/analysis.py RESULTS_DIRECTORY
```

**Analyze preference test results:**
```bash
uv run analysis/analysis_pref.py RESULTS_DIRECTORY
```

**Standardize audio to 24kHz:**
```bash
bash scripts/standardize_audio_24k.sh INPUT_DIR OUTPUT_DIR
```

## Architecture

The app is a Gradio-based Mean Opinion Score (MOS) listening test platform for speech/audio evaluation. It supports Prolific integration and multiple languages.

### Entry point & config
`main.py` — Hydra-configured entry point. `@hydra.main` loads a YAML config from `config/`. The config specifies the `language`, which selects a page module from `pages/` (e.g. `language: swedish` → `pages.swedish`). It also wires up the sampler, attention checks, instruction pages, and Gradio launch settings.

### Core class: `MOSTest` (`main.py`)
Orchestrates the full test session:
- `TestCasesSampler` (`utils.py`) loads the test list JSON and randomly samples `sample_size_per_test` items per system per test type. CMOS pairs are randomly swapped (A/B counterbalanced) at sample time.
- Each session inserts instruction pages, shuffles test cases per type, then randomly interleaves 4 attention checks at evenly-spaced positions.
- Results are saved to `results/<user_id>_results.json`. Prolific users are redirected via `prolific_return_code`.
- If `PROLIFIC_PID` is detected as a URL query param, the test auto-starts without showing the email input form.

### Page system (`pages/`)
Each language module (e.g. `pages/english.py`, `pages/finnish.py`) is self-contained and defines:
- A `TestPage` abstract base class hierarchy: `TestPage → NoReferencePage`, with concrete subclasses for each test type.
- Supported types: `SMOS` (speaker similarity), `CMOS` (comparative MOS, −3 to +3), `NMOS` (naturalness), `QMOS` (quality, 1-5), `EMOS` (editing MOS, dual-score), `empha_pref` (emphasis preference, −1/0/+1), and corresponding `*InstructionPage` and `*AttentionPage` variants.
- A `PageFactory` with `PAGE_CLASSES` dict mapping type strings (e.g. `"CMOS"`, `"cmos"`) to classes. Register new types via `PageFactory.register_page_type()`.
- Each page implements `get_instructions()`, `get_slider_config()` (returns min, max, default), and `get_level_label()`.

**To add a new language:** copy an existing page module, translate the instruction strings, adjust slider ranges if needed, and set `language: your_language` in the config. The page module is imported dynamically by `main.py`.

**To add a new test type:** subclass `TestPage` (or `NoReferencePage` for no-reference tests), implement the required methods, and register the class in `PageFactory.PAGE_CLASSES`.

### Test list JSON format
```json
{
  "CMOS": [          // test type key
    [                // one system's test cases
      { "type": "CMOS", "reference": "path/a.wav", "target": "path/b.wav",
        "ref_system": "System_A", "target_system": "System_B" }
    ]
  ],
  "empha_pref": [
    [
      { "type": "empha_pref", "reference": "path/a.wav", "target": "path/b.wav",
        "ref_system": "System_A", "target_system": "System_B",
        "transcript": "She bought a *red* car." }
    ]
  ]
}
```
`empha_pref` test cases require a `transcript` field with the emphasized word wrapped in `*asterisks*`.

Use `test_list_builders/` scripts to generate these from local files, Google Drive, or a web server.

### Analysis (`analysis/`)
- `analysis.py`: Filters participants by attention check correctness, then computes per-system CMOS/SMOS means with 95% CI. SMOS scores are reported with a +3 offset. Outputs CSV and per-utterance JSON.
- `analysis_pref.py`: Filters by attention checks, then computes per-pair preference ratios for `empha_pref` tests. Normalizes scores by flipping sign when `swap=True`. Saves CSV and stacked bar plots.
- `dnsmos_analysis.py`, `qmos_analysis.py`: Variant analyses for DNSMOS/QMOS test types.

**Attention check audio naming convention:** The expected score is parsed from the audio filename — the last underscore-separated segment before the extension is used as the expected integer score (e.g., `attention_score_3.wav` → expected score 3). This drives automatic pass/fail filtering across all analysis scripts.

### Config structure (`config/`)
`config/default.yaml` is always loaded by Hydra; named configs override it. Key fields:
- `sampler.test_list_path`: path to the test list JSON
- `sampler.sample_size_per_test`: how many items to sample per system per test type
- `attention_checks`: list of test case dicts for attention checks
- `instructions`: list of instruction page test case dicts
- `language`: selects the `pages/<language>.py` module
- `prolific_return_code`: Prolific completion code for redirect
- `gradio.*`: server name, port, root_path, share, allowed_paths

**Participant cap:** `main.py` hard-codes a 30-participant limit (`num_results >= 30` check in `start_test`). Adjust this directly in `main.py` or use `main2.py` which may expose it differently.
