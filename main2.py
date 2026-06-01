import glob
from pathlib import Path
import gradio as gr
import json
import os
import random
import math
from typing import List
from gradio import update
import hydra
from omegaconf import DictConfig

from utils import is_valid_email, TestCasesSampler
from importlib import import_module


class MOSTest:
    def __init__(
            self,
            case_sampler: TestCasesSampler,
            page_module,
            attention_checks: List[dict],
            instruction_pages: List[dict],
            num_attention: int = 3,
            css_file: str = None,
            prolific_return_code: str = None,
        ):
        self.case_sampler = case_sampler
        self.attention_checks = attention_checks
        self.instruction_pages = instruction_pages
        self.num_attention = num_attention

        self.PageFactory = getattr(page_module, "PageFactory")
        self.EmphasisPreferencePage = getattr(page_module, "EmphasisPreferencePage")
        self.CMOSPage = getattr(page_module, "CMOSPage")

        if css_file and os.path.isfile(css_file):
            with open(css_file, 'r') as f:
                self.custom_css = f.read()
        else:
            self.custom_css = None

        if prolific_return_code is None:
            self.redirect_url = "https://app.prolific.com/"
        else:
            self.redirect_url = f"https://app.prolific.com/submissions/complete?cc={prolific_return_code}"

    def sample_test_cases_for_session(self):
        """Sample new test cases for each session"""
        questions = self.case_sampler.sample_test_cases()
        test_cases = []
        if self.instruction_pages is not None:
            for instruction in self.instruction_pages:
                match instruction["type"]:
                    case "smos_instruction":
                        random.shuffle(questions['SMOS'])
                        questions['SMOS'].insert(0, instruction)
                    case "cmos_instruction":
                        random.shuffle(questions['CMOS'])
                        questions['CMOS'].insert(0, instruction)
                    case "qmos_instruction":
                        questions['QMOS'].insert(0, instruction)
                    case "qmos_negative_instruction":
                        questions['QMOS'].insert(0, instruction)
                    case "empha_pref_instruction":
                        random.shuffle(questions['empha_pref'])
                        questions['empha_pref'].insert(0, instruction)
                    case _:
                        print(f"Unsupported instruction type: {instruction['type']}.")
                        continue

        for _, cases in questions.items():
            test_cases.extend(cases)

        num_attention = min(self.num_attention, len(self.attention_checks)) if self.attention_checks else 0

        if self.attention_checks and num_attention > 0:
            for i, attention_check in enumerate(random.sample(self.attention_checks, num_attention)):
                test_cases.insert(
                    random.randint(
                        math.floor(0.2 * (i + 1) * len(test_cases)),
                        math.floor(0.2 * (i + 2) * len(test_cases))
                    ),
                    attention_check
                )
        return test_cases

    def capture_url_params(self, request: gr.Request):
        """Capture URL query parameters from the request"""
        if request and hasattr(request, 'query_params'):
            return dict(request.query_params)
        return {}

    def get_param_value(self, url_params, param_name, default=""):
        """Get a specific parameter value from URL parameters"""
        return url_params.get(param_name, default)

    def get_current_page(self, test_cases, current_page):
        """Get the current test page object"""
        if current_page < len(test_cases):
            test_case = test_cases[current_page]
            return self.PageFactory.create_page(test_case)
        return None

    def create_radio_choices_and_default(self, page_obj):
        """Create radio button choices with labels from page object"""
        min_val, max_val, _ = page_obj.get_slider_config()
        level_labels = page_obj.get_level_label()

        choices = []
        values = []
        current = min_val
        label_index = 0

        while current <= max_val and label_index < len(level_labels):
            choice_text = f"{current}: {level_labels[label_index]}"
            choices.append(choice_text)
            values.append(str(current))
            current += 1
            label_index += 1

        return choices, values, None  # No default value

    def get_initial_test_updates(self, test_cases):
        """Get the initial test page updates when auto-starting"""
        page = self.get_current_page(test_cases, 0)
        if page:
            instructions = page.get_instructions()
            ref_audio = page.get_reference_audio()
            tar_audio = page.get_target_audio()

            choices, values, _ = self.create_radio_choices_and_default(page)
            radio_update = update(choices=choices, value=None, visible=True)

            if isinstance(page, self.EmphasisPreferencePage):
                transcript = page.transcript
                transcript_visible = True
            else:
                transcript = ""
                transcript_visible = False

            return instructions, ref_audio, tar_audio, radio_update, transcript, transcript_visible
        return None, None, None, None, "", False

    def validate_id(self, email, prolific_pid):
        if not email and not prolific_pid:
            return None, "Please provide either Email or Prolific PID"
        return email or prolific_pid, None

    def run_test(self, user_id, naturalness_score, ref_audio_played, target_audio_played,
                 test_cases=None, current_page=0, results=None, url_params=None):
        if test_cases is None:
            test_cases = []
        if results is None:
            results = []
        if url_params is None:
            url_params = {}

        total_pages = len(test_cases)

        # Initialize ALL return variables at the start to prevent UnboundLocalError
        instructions = update()
        progress = update()
        ref_audio = update()
        tar_audio = update()
        radio_update = update()
        submit_score = update(visible=True)
        redirect = update()
        empha_transcript_label = update()
        empha_transcript = update()

        # Early-exit helper — returns the 14-tuple unchanged so Gradio updates nothing visible.
        # Tuple order: instructions, progress, reference, target, score_input, submit_score,
        #              redirect, empha_transcript_label, empha_transcript,
        #              test_cases_state, current_page_state, results_state,
        #              ref_audio_played_state, target_audio_played_state
        if not user_id or current_page >= total_pages:
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect,
                    empha_transcript_label, empha_transcript, test_cases, current_page, results,
                    ref_audio_played, target_audio_played)

        current_page_obj = self.get_current_page(test_cases, current_page)
        needs_reference = current_page_obj.get_reference_audio() is not None

        if not target_audio_played:
            progress = (
                f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"
                f" - Please finish listening to all given audio to completion"
            )
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect,
                    empha_transcript_label, empha_transcript, test_cases, current_page, results,
                    ref_audio_played, target_audio_played)

        if needs_reference and not ref_audio_played:
            progress = (
                f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"
                f" - Please finish listening to all given audio to completion"
            )
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect,
                    empha_transcript_label, empha_transcript, test_cases, current_page, results,
                    ref_audio_played, target_audio_played)

        if naturalness_score is None:
            progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%) - Please select a score"
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect,
                    empha_transcript_label, empha_transcript, test_cases, current_page, results,
                    ref_audio_played, target_audio_played)

        try:
            naturalness_score_int = int(naturalness_score.split(':')[0]) if naturalness_score else None
        except (ValueError, TypeError, AttributeError):
            naturalness_score_int = None

        if current_page_obj and naturalness_score_int is not None and not current_page_obj.validate_score(naturalness_score_int):
            pass

        test_case = test_cases[current_page]
        result_entry = {
            "test_type": test_case["type"],
            "reference_audio": test_case.get("reference", None),
            "target_audio": test_case["target"],
            "ref_system": test_case.get("ref_system", None),
            "target_system": test_case.get("target_system", None),
            "swap": test_case.get("swap", False),
            "score": naturalness_score_int
        }

        if isinstance(current_page_obj, self.EmphasisPreferencePage):
            result_entry["transcript"] = current_page_obj.transcript

        if url_params:
            result_entry["url_params"] = url_params

        results.append(result_entry)

        current_page += 1
        progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"

        if current_page >= total_pages:
            filename = f"results/{user_id}_results.json"
            os.makedirs("results/", exist_ok=True)

            final_results = {
                "user_id": user_id,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "results": results
            }

            with open(filename, "w") as f:
                json.dump(final_results, f, indent=2)

            if "@" in user_id:
                finish_message = """
                # Test Completed!
                ## Thank you for participating! Please close this tab.
                """
                submit_score = update(visible=False)
            else:
                finish_message = """
                # Test Completed!
                ## Thank you for participating! Your results have been saved.
                """
                redirect = update(visible=True)
                submit_score = update(visible=False)

            instructions = update(value=finish_message)
            ref_audio = update(value=None, visible=False)
            tar_audio = update(value=None, visible=False)
            radio_update = update(visible=False)
            empha_transcript_label = update(visible=False)
            empha_transcript = update(value="", visible=False)
            # Return order must match the outputs list in submit_score.click(...)
            return (
                instructions,         # → instructions
                progress,             # → progress_text
                ref_audio,            # → reference (hidden)
                tar_audio,            # → target (hidden)
                radio_update,         # → score_input (hidden)
                submit_score,         # → submit_score button (hidden)
                redirect,             # → redirect button (shown for Prolific users)
                empha_transcript_label,  # → empha_transcript_label (hidden)
                empha_transcript,        # → empha_transcript (hidden)
                test_cases,           # → test_cases_state
                current_page,         # → current_page_state
                results,              # → results_state
                False,                # → ref_audio_played_state (reset)
                False                 # → target_audio_played_state (reset)
            )

        next_page = self.get_current_page(test_cases, current_page)
        if next_page:
            instructions = next_page.get_instructions()
            ref_audio = next_page.get_reference_audio()
            tar_audio = next_page.get_target_audio()

            choices, values, _ = self.create_radio_choices_and_default(next_page)
            radio_update = update(choices=choices, value=None, visible=True)

            if isinstance(next_page, self.EmphasisPreferencePage):
                empha_transcript_label = update(visible=True)
                empha_transcript = update(value=next_page.transcript, visible=True)
            else:
                empha_transcript_label = update(visible=False)
                empha_transcript = update(value="", visible=False)
        else:
            instructions = "Error: Could not load next test"
            ref_audio = None
            tar_audio = None
            radio_update = update()
            empha_transcript_label = update(visible=False)
            empha_transcript = update(value="", visible=False)

        submit_score = update(visible=True)
        redirect = update()

        # Return order must match the outputs list in submit_score.click(...)
        return (
            update(value=instructions),   # → instructions
            progress,                     # → progress_text
            update(value=ref_audio, label='sample A', visible=ref_audio is not None),             # → reference
            update(value=tar_audio, label=('sample B' if ref_audio is not None else 'sample')),   # → target
            radio_update,                 # → score_input
            submit_score,                 # → submit_score button
            redirect,                     # → redirect button
            empha_transcript_label,       # → empha_transcript_label
            empha_transcript,             # → empha_transcript
            test_cases,                   # → test_cases_state
            current_page,                 # → current_page_state
            results,                      # → results_state
            False,                        # → ref_audio_played_state (reset for next page)
            False                         # → target_audio_played_state (reset for next page)
        )

    def create_interface(self):
        """Create the Gradio interface for the MOS test"""
        with gr.Blocks(css=self.custom_css) as interface:
            user_id = gr.State(value=None)
            url_params_state = gr.State(value={})

            test_cases_state = gr.State(value=[])
            current_page_state = gr.State(value=0)
            results_state = gr.State(value=[])

            ref_audio_played_state = gr.State(value=False)
            target_audio_played_state = gr.State(value=False)

            url_params_display = gr.JSON(label="URL Parameters", visible=False)

            with gr.Column() as id_input_section:
                email = gr.Textbox(label="Email", visible=True)
                prolific_pid = gr.Textbox(label="Prolific PID", visible=False)

                id_error = gr.Markdown("", visible=False)
                submit_id = gr.Button("Start Test")

            with gr.Column(visible=False) as test_interface:
                progress_text = gr.HTML("Progress: 0/0")
                instructions = gr.Markdown()

                # EmphasisPreference-specific elements
                empha_transcript_label = gr.Markdown("### Transcript:", visible=False)
                empha_transcript = gr.Textbox(
                    # label="Transcript",
                    interactive=False,
                    lines=3,
                    value="",
                    visible=False,
                    show_label=False,
                )

                with gr.Row():
                    reference = gr.Audio(
                        label="sample A",
                        interactive=False,
                        streaming=True,
                        show_download_button=False,
                        show_share_button=False,
                        editable=False,
                    )
                    target = gr.Audio(
                        label="sample B",
                        interactive=False,
                        streaming=True,
                        show_download_button=False,
                        show_share_button=False,
                        editable=False,
                    )

                score_input = gr.Radio(
                    choices=[],
                    value=None,
                    label="Your Score",
                    interactive=True
                )

                submit_score = gr.Button("Submit Rating")

                redirect = gr.Button("Return to Prolific", visible=False)

            def load_and_populate(request: gr.Request):
                """Load page and capture URL parameters, then conditionally show/hide input fields"""
                params = self.capture_url_params(request)

                new_test_cases = self.sample_test_cases_for_session()
                total_pages = len(new_test_cases)

                prolific_pid_from_url = params.get('PROLIFIC_PID')

                # Return order must match the outputs list in interface.load(...)
                if prolific_pid_from_url:
                    # PROLIFIC_PID in URL → skip login form, auto-start the test
                    instructions_val, ref_audio, tar_audio, radio_update, transcript_val, transcript_visible = self.get_initial_test_updates(new_test_cases)
                    return (
                        params,                    # → url_params_state
                        params,                    # → url_params_display
                        "",                        # → email (clear value)
                        prolific_pid_from_url,     # → prolific_pid (store PID value)
                        update(visible=False),     # → id_input_section (hide login form)
                        update(visible=True),      # → test_interface (show test)
                        prolific_pid_from_url,     # → user_id state
                        instructions_val,          # → instructions
                        update(value=ref_audio, label='sample A', visible=ref_audio is not None),            # → reference audio
                        update(value=tar_audio, label=('sample B' if ref_audio is not None else 'sample')), # → target audio
                        radio_update,              # → score_input
                        update(visible=False),     # → email (hide the textbox)
                        update(visible=False),     # → prolific_pid (hide the textbox)
                        update(visible=transcript_visible),               # → empha_transcript_label
                        update(value=transcript_val, visible=transcript_visible),  # → empha_transcript
                        new_test_cases,            # → test_cases_state
                        0,                         # → current_page_state
                        [],                        # → results_state
                        f"Progress: 0/{total_pages} (0%)",  # → progress_text
                        False,                     # → ref_audio_played_state
                        False                      # → target_audio_played_state
                    )
                else:
                    # No PROLIFIC_PID → show login form, wait for user to click Start
                    return (
                        params,                    # → url_params_state
                        params,                    # → url_params_display
                        "",                        # → email (clear value)
                        "",                        # → prolific_pid (clear value)
                        update(visible=True),      # → id_input_section (show login form)
                        update(visible=False),     # → test_interface (hide test)
                        None,                      # → user_id state (not set yet)
                        "",                        # → instructions (empty)
                        update(value=None, visible=False),  # → reference audio (hidden)
                        update(value=None),        # → target audio (clear)
                        update(value=None),        # → score_input (clear)
                        update(visible=True),      # → email (show textbox)
                        update(visible=False),     # → prolific_pid (hide textbox)
                        update(visible=False),     # → empha_transcript_label (hidden)
                        update(value="", visible=False),    # → empha_transcript (hidden)
                        new_test_cases,            # → test_cases_state (pre-sampled, ready for start)
                        0,                         # → current_page_state
                        [],                        # → results_state
                        f"Progress: 0/{total_pages} (0%)",  # → progress_text
                        False,                     # → ref_audio_played_state
                        False                      # → target_audio_played_state
                    )

            def start_test(email_input, pid_input, test_cases):
                num_results = len(glob.glob("results/*_results.json"))

                # Return order must match the outputs list in submit_id.click(...)
                # Tuple order: user_id, id_error, id_input_section, test_interface,
                #              instructions, reference, target, score_input,
                #              empha_transcript_label, empha_transcript,
                #              current_page_state, results_state
                if num_results >= 30:
                    return (
                        None,                      # → user_id (not set)
                        update(value="The maximum number of participants has been reached. Thank you for your interest!", visible=True),  # → id_error
                        update(visible=True),      # → id_input_section (keep visible)
                        update(visible=False),     # → test_interface (keep hidden)
                        None,                      # → instructions (no change)
                        update(value=None, visible=False),   # → reference (hidden)
                        update(value=None, visible=False),   # → target (hidden)
                        update(),                  # → score_input (no change)
                        update(visible=False),     # → empha_transcript_label (hidden)
                        update(value="", visible=False),     # → empha_transcript (hidden)
                        0,                         # → current_page_state
                        []                         # → results_state
                    )

                if not is_valid_email(email_input) and not pid_input:
                    return (
                        None,                      # → user_id (not set)
                        update(value="Please provide a valid Email address", visible=True),  # → id_error
                        update(visible=True),      # → id_input_section (keep visible for retry)
                        update(visible=False),     # → test_interface (keep hidden)
                        None,                      # → instructions (no change)
                        update(value=None, visible=False),  # → reference (hidden)
                        update(value=None),        # → target (clear)
                        update(),                  # → score_input (no change)
                        update(visible=False),     # → empha_transcript_label (hidden)
                        update(value="", visible=False),    # → empha_transcript (hidden)
                        0,                         # → current_page_state
                        []                         # → results_state
                    )

                valid_id = email_input if email_input else pid_input

                first_page = self.get_current_page(test_cases, 0)
                if first_page:
                    ref_audio = first_page.get_reference_audio()
                    tar_audio = first_page.get_target_audio()
                    instructions = first_page.get_instructions()

                    choices, values, _ = self.create_radio_choices_and_default(first_page)
                    radio_update = update(choices=choices, value=None, visible=True)

                    if isinstance(first_page, self.EmphasisPreferencePage):
                        transcript_val = first_page.transcript
                        transcript_visible = True
                    else:
                        transcript_val = ""
                        transcript_visible = False
                else:
                    ref_audio = None
                    tar_audio = None
                    radio_update = update()
                    instructions = "Error loading test"
                    transcript_val = ""
                    transcript_visible = False

                return (
                    valid_id,                      # → user_id state
                    update(value="", visible=False),   # → id_error (hide)
                    update(visible=False),         # → id_input_section (hide login form)
                    update(visible=True),          # → test_interface (show test)
                    instructions,                  # → instructions
                    update(value=ref_audio, label='sample A', visible=ref_audio is not None),            # → reference audio
                    update(value=tar_audio, label=('sample B' if ref_audio is not None else 'sample')), # → target audio
                    radio_update,                  # → score_input
                    update(visible=transcript_visible),              # → empha_transcript_label
                    update(value=transcript_val, visible=transcript_visible),  # → empha_transcript
                    0,                             # → current_page_state (reset)
                    []                             # → results_state (reset)
                )

            interface.load(
                load_and_populate,
                outputs=[
                    url_params_state,          # [0]  URL query params dict
                    url_params_display,        # [1]  debug JSON display
                    email,                     # [2]  email textbox value
                    prolific_pid,              # [3]  prolific_pid textbox value
                    id_input_section,          # [4]  login form column visibility
                    test_interface,            # [5]  test column visibility
                    user_id,                   # [6]  user identifier state
                    instructions,              # [7]  instruction markdown
                    reference,                 # [8]  reference audio player
                    target,                    # [9]  target audio player
                    score_input,               # [10] score radio buttons
                    email,                     # [11] email textbox visibility (second update to same component)
                    prolific_pid,              # [12] prolific_pid visibility  (second update to same component)
                    empha_transcript_label,    # [13] "Transcript:" label visibility
                    empha_transcript,          # [14] transcript textbox value/visibility
                    test_cases_state,          # [15] sampled test cases for this session
                    current_page_state,        # [16] current page index
                    results_state,             # [17] collected results list
                    progress_text,             # [18] progress bar HTML
                    ref_audio_played_state,    # [19] whether reference audio was fully played
                    target_audio_played_state  # [20] whether target audio was fully played
                ]
            )

            submit_id.click(
                start_test,
                inputs=[email, prolific_pid, test_cases_state],
                outputs=[
                    user_id,                   # [0]  user identifier state
                    id_error,                  # [1]  error message markdown
                    id_input_section,          # [2]  login form column visibility
                    test_interface,            # [3]  test column visibility
                    instructions,              # [4]  instruction markdown
                    reference,                 # [5]  reference audio player
                    target,                    # [6]  target audio player
                    score_input,               # [7]  score radio buttons
                    empha_transcript_label,    # [8]  "Transcript:" label visibility
                    empha_transcript,          # [9]  transcript textbox value/visibility
                    current_page_state,        # [10] current page index (reset to 0)
                    results_state              # [11] collected results list (reset to [])
                ]
            )

            def mark_ref_audio_played():
                return True

            def mark_target_audio_played():
                return True

            reference.stop(mark_ref_audio_played, outputs=[ref_audio_played_state])
            target.stop(mark_target_audio_played, outputs=[target_audio_played_state])

            submit_score.click(
                self.run_test,
                inputs=[
                    user_id, score_input, ref_audio_played_state, target_audio_played_state,
                    test_cases_state, current_page_state, results_state, url_params_state
                ],
                outputs=[
                    instructions,              # [0]  instruction markdown
                    progress_text,             # [1]  progress bar HTML
                    reference,                 # [2]  reference audio player
                    target,                    # [3]  target audio player
                    score_input,               # [4]  score radio buttons (reset for next page)
                    submit_score,              # [5]  submit button visibility
                    redirect,                  # [6]  "Return to Prolific" button visibility
                    empha_transcript_label,    # [7]  "Transcript:" label visibility
                    empha_transcript,          # [8]  transcript textbox value/visibility
                    test_cases_state,          # [9]  test cases (unchanged, passed through)
                    current_page_state,        # [10] current page index (incremented)
                    results_state,             # [11] collected results list (appended)
                    ref_audio_played_state,    # [12] reset to False for next page
                    target_audio_played_state  # [13] reset to False for next page
                ],
            )

            redirect_js = f"() => {{ window.location.href = '{self.redirect_url}' }}"
            redirect.click(
                lambda: None,
                outputs=[],
                js=redirect_js
            )

        return interface


@hydra.main(version_base=None, config_path="config")
def main(cfg: DictConfig) -> None:
    """Functional approach to main"""

    language = cfg.language
    page_module = f"pages.{language}"

    pages = import_module(page_module)

    sampler = TestCasesSampler(
        test_cases_json=cfg.sampler.test_list_path,
        sample_size_per_test=cfg.sampler.sample_size_per_test,
    )

    test = MOSTest(
        case_sampler=sampler,
        page_module=pages,
        attention_checks=cfg.attention_checks,
        instruction_pages=cfg.instructions,
        num_attention=cfg.get("num_attention", 3),
        css_file=cfg.get("css_file", None),
        prolific_return_code=cfg.get("prolific_return_code", None),
    )

    interface = test.create_interface()

    launch_cfg = cfg.gradio
    allowed_paths = []
    for path in launch_cfg.allowed_paths:
        if path == "cwd":
            allowed_paths.append(os.getcwd())
        else:
            allowed_paths.append(str(Path(path).resolve()))

    interface.launch(
        server_name=launch_cfg.server_name,
        server_port=launch_cfg.server_port,
        root_path=launch_cfg.root_path,
        share=launch_cfg.share,
        show_error=launch_cfg.show_error,
        allowed_paths=allowed_paths
    )

if __name__ == "__main__":
    main()
