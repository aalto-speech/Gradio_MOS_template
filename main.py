import gradio as gr
import json
import os
import random
from typing import List
from gradio import update

from utils import is_valid_email, TestCasesSampler
from pages import PageFactory, EMOSPage, CMOSPage

class MOSTest:
    def __init__(self, case_sampler: TestCasesSampler):
        # Keep the structure of test_cases as a list
        self.case_sampler = case_sampler

        # Add attention check cases
        self.attention_checks = [
            {
                "type": 'attention',
                'reference': 'audios/attention_high.wav',
                'target': 'audios/attention_high.wav'
            },
            {
                "type": 'attention',
                'reference': 'audios/attention_high.wav',
                'target': 'audios/attention_high.wav'
            },
        ]
        self.instruction_pages = [
            {
                "type": "smos_instruction",
                "reference": "audios/1.wav",
                "target": "audios/1.wav"
            },
            {
                "type": "cmos_instruction",
                "reference": "audios/4.wav",
                "target": "audios/4.wav"
            },
        ]

        # Remove these from __init__ - they'll be per-session now
        # self.current_page = 0
        # self.results = []
        # self.url_params = {}

    def sample_test_cases_for_session(self):
        """Sample new test cases for each session"""
        questions = self.case_sampler.sample_test_cases()
        test_cases = []
        for _, cases in questions.items():
            random.shuffle(cases)
            test_cases.extend(cases)
        
        for attention_check in self.attention_checks:
            test_cases.insert(
                random.randint(int(0.25 * len(test_cases)), int(0.9 * len(test_cases))), 
                attention_check
            )
        test_cases = self.instruction_pages + test_cases
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
            return PageFactory.create_page(test_case)
        return None

    def get_initial_test_updates(self, test_cases):
        """Get the initial test page updates when auto-starting"""
        page = self.get_current_page(test_cases, 0)
        if page:
            instructions = page.get_instructions()
            ref_audio = page.get_reference_audio() #if not isinstance(page, EMOSPage) else None
            tar_audio = page.get_target_audio()
            slider_update = page.get_slider_update()
            
            # Handle EMOS-specific elements
            if isinstance(page, EMOSPage):
                transcript = page.get_edited_transcript()
                transcript_visible = True
                editing_min, editing_max, editing_default = page.get_editing_slider_config()
                editing_slider_update = update(minimum=editing_min, maximum=editing_max, step=1, value=editing_default, visible=True)
            else:
                transcript = ""
                transcript_visible = False
                editing_slider_update = update(visible=False)
                
            return instructions, ref_audio, tar_audio, slider_update, transcript, transcript_visible, editing_slider_update
        return None, None, None, None, "", False, update(visible=False)

    def validate_id(self, email, prolific_pid):
        if not email and not prolific_pid:
            return None, "Please provide either Email or Prolific PID"
        return email or prolific_pid, None

    def run_test(self, user_id, naturalness_score, audio_played, editing_score=None, 
                 test_cases=None, current_page=0, results=None, url_params=None):
        # Initialize session data if not provided
        if test_cases is None:
            test_cases = []
        if results is None:
            results = []
        if url_params is None:
            url_params = {}
            
        total_pages = len(test_cases)
        
        # Set default update values
        instructions = update()
        progress = update()
        ref_audio = update(value=None)
        tar_audio = update(value=None)
        slider_update = update(visible=False)
        submit_score = update(visible=True)
        redirect = update()  # No redirect by default
        emos_label = update(visible=False)
        transcript = update(value="", visible=False)

        # Check that we have a valid user_id and are within bounds
        if not user_id or current_page >= total_pages:
            return (instructions, progress, ref_audio, tar_audio, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results)
            
        # Check that the target audio was played
        if audio_played is None:
            progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"
            return (instructions, progress, ref_audio, tar_audio, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results)
        
        # Get current page and validate score
        current_page_obj = self.get_current_page(test_cases, current_page)
        if current_page_obj and not current_page_obj.validate_score(naturalness_score):
            # Could add score validation error handling here
            pass
        
        test_case = test_cases[current_page]
        # Store result from the current page, including URL parameters
        result_entry = {
            "test_type": test_case["type"],
            "target_audio": test_case["target"],
            "system": test_case.get(
                "system", test_case.get("target_system", "")
            ),
            "score": naturalness_score
        }
        
        # Add editing score and transcript for EMOS tests
        if isinstance(current_page_obj, EMOSPage):
            result_entry["naturalness_score"] = naturalness_score
            result_entry["editing_score"] = editing_score
            result_entry["edited_transcript"] = current_page_obj.get_edited_transcript()
            # Remove the generic "score" for EMOS to avoid confusion
            del result_entry["score"]
        
        # Add URL parameters to the result if they exist
        if url_params:
            result_entry["url_params"] = url_params
            
        results.append(result_entry)

        current_page += 1
        progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"

        if current_page >= total_pages:
            filename = f"results/{user_id}_results.json"

            os.makedirs("results/", exist_ok=True)
            
            # Add timestamp to the results
            final_results = {
                "user_id": user_id,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "results": results
            }
            
            # Overwrite the file completely with new results
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
            slider_update = update(visible=False)
            emos_label = update(visible=False)
            transcript = update(value="", visible=False)
            return (
                instructions,
                progress,
                ref_audio,
                tar_audio,
                slider_update,
                submit_score,
                redirect,
                emos_label,
                transcript,
                test_cases,
                current_page,
                results
            )

        # Get next page configuration
        next_page = self.get_current_page(test_cases, current_page)
        if next_page:
            instructions = next_page.get_instructions()
            ref_audio = next_page.get_reference_audio() if not isinstance(next_page, EMOSPage) else None
            tar_audio = next_page.get_target_audio()
            slider_update = next_page.get_slider_update()
            
            # Handle EMOS-specific elements
            if isinstance(next_page, EMOSPage):
                emos_label = update(visible=True)
                transcript = update(value=next_page.get_edited_transcript(), visible=True)
            else:
                emos_label = update(visible=False)
                transcript = update(value="", visible=False)
        else:
            instructions = "Error: Could not load next test"
            ref_audio = None
            tar_audio = None
            slider_update = update()
            emos_label = update(visible=False)
            transcript = update(value="", visible=False)
            
        redirect = update()  # No redirect needed yet
        return (
            update(value=instructions),
            progress,
            update(value=ref_audio, label='sample A' if isinstance(next_page, CMOSPage) else 'Reference'),
            update(value=tar_audio, label='sample B' if isinstance(next_page, CMOSPage) else 'Target'),
            slider_update,
            submit_score,
            redirect,
            emos_label,
            transcript,
            test_cases,
            current_page,
            results
        )

    def create_interface(self):
        """Create the Gradio interface for the MOS test"""
        # Don't sample test cases here - do it per session
        with gr.Blocks() as interface:
            user_id = gr.State(value=None)
            url_params_state = gr.State(value={})
            
            # Add session-specific state variables
            test_cases_state = gr.State(value=[])
            current_page_state = gr.State(value=0)
            results_state = gr.State(value=[])
            
            # Add a component to display URL parameters (optional, for debugging)
            url_params_display = gr.JSON(label="URL Parameters", visible=False)
            
            # Conditional input fields - will be shown/hidden based on URL parameters
            with gr.Column() as id_input_section:
                email = gr.Textbox(label="Email", visible=True)
                prolific_pid = gr.Textbox(label="Prolific PID", visible=False)  # Hidden by default
                
                id_error = gr.Markdown("", visible=False)
                submit_id = gr.Button("Start Test")

            with gr.Column(visible=False) as test_interface:
                progress_text = gr.HTML("Progress: 0/0")
                instructions = gr.Markdown()
                
                # EMOS-specific elements
                emos_transcript_label = gr.Markdown("### Edited Transcript:", visible=False)
                edited_transcript = gr.Textbox(
                    label="Edited Transcript", 
                    interactive=False, 
                    lines=3,
                    value="",
                    visible=False
                )
                
                with gr.Row():
                    reference = gr.Audio(
                        label="Reference Audio",
                        interactive=False,
                        streaming=True,
                    )
                    target = gr.Audio(
                        label="Target Audio",
                        interactive=False,
                        streaming=True,
                    )
                
                # Get initial slider config from a default page
                score_input = gr.Slider(
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Your Score",
                    value=3
                )
                
                # EMOS editing effect slider
                editing_score_input = gr.Slider(
                    minimum=0,
                    maximum=3,
                    step=1,
                    label="Editing Effect Score",
                    value=1,
                    visible=False
                )
                
                submit_score = gr.Button("Submit Rating")

                redirect = gr.Button("Return to Prolific", visible=False)  # For redirecting to Prolific

            def load_and_populate(request: gr.Request):
                """Load page and capture URL parameters, then conditionally show/hide input fields"""
                params = self.capture_url_params(request)
                
                # Sample new test cases for this session
                new_test_cases = self.sample_test_cases_for_session()
                total_pages = len(new_test_cases)
                
                # Check for PROLIFIC_PID in URL parameters (exact match only)
                prolific_pid_from_url = params.get('PROLIFIC_PID')
                
                if prolific_pid_from_url:
                    # PROLIFIC_PID found in URL - hide input section and auto-start
                    instructions_val, ref_audio, tar_audio, slider_update, transcript_val, transcript_visible, editing_slider_update = self.get_initial_test_updates(new_test_cases)
                    return (
                        params,  # url_params_state
                        params,  # url_params_display
                        "",  # email textbox (hidden)
                        prolific_pid_from_url,  # prolific_pid textbox (hidden)
                        update(visible=False),  # hide id_input_section
                        update(visible=True),   # show test_interface
                        prolific_pid_from_url,  # user_id state
                        instructions_val,  # instructions
                        ref_audio,  # reference audio
                        tar_audio,  # target audio
                        slider_update,  # score input slider
                        update(visible=False),  # hide email textbox
                        update(visible=False),   # hide prolific_pid textbox
                        update(visible=transcript_visible),  # emos label visibility
                        update(value=transcript_val, visible=transcript_visible),  # edited transcript
                        editing_slider_update,  # editing score slider
                        new_test_cases,  # test_cases_state
                        0,  # current_page_state
                        [],  # results_state
                        f"Progress: 0/{total_pages} (0%)"  # progress_text
                    )
                else:
                    # No PROLIFIC_PID in URL - show input fields
                    return (
                        params,  # url_params_state
                        params,  # url_params_display
                        "",  # email textbox (empty, no pre-fill)
                        "",  # prolific_pid textbox (hidden)
                        update(visible=True),   # show id_input_section
                        update(visible=False),  # hide test_interface
                        None,  # user_id state (not set yet)
                        "",  # instructions (empty)
                        None,  # reference audio (empty)
                        None,  # target audio (empty)
                        update(value=3),  # score input (default value)
                        update(visible=True),   # show email textbox
                        update(visible=False),   # hide prolific_pid textbox
                        update(visible=False),  # emos label (hidden)
                        update(value="", visible=False),  # edited transcript (hidden)
                        update(visible=False),  # editing score slider (hidden)
                        new_test_cases,  # test_cases_state (still set for when they start)
                        0,  # current_page_state
                        [],  # results_state
                        f"Progress: 0/{total_pages} (0%)"  # progress_text
                    )

            def start_test(email_input, pid_input, test_cases):
                # Modified validation to only require email if no PID is provided
                if not is_valid_email(email_input) and not pid_input:
                    return (
                        None,
                        update(value="Please provide a valid Email address", visible=True),
                        update(visible=True),  # Keep id_input_section visible for retry
                        update(visible=False),  # Keep test_interface hidden
                        None,
                        None,
                        None,
                        update(),
                        update(visible=False),
                        update(value="", visible=False),
                        0,  # current_page_state
                        []   # results_state
                    )
                
                # Use email as user_id, or PID if email is not provided
                valid_id = email_input if email_input else pid_input
                
                # Get first page configuration
                first_page = self.get_current_page(test_cases, 0)
                if first_page:
                    ref_audio = first_page.get_reference_audio() if not isinstance(first_page, EMOSPage) else None
                    tar_audio = first_page.get_target_audio()
                    slider_update = first_page.get_slider_update()
                    instructions = first_page.get_instructions()
                    
                    # Handle EMOS-specific elements
                    if isinstance(first_page, EMOSPage):
                        transcript_val = first_page.get_edited_transcript()
                        transcript_visible = True
                        editing_min, editing_max, editing_default = first_page.get_editing_slider_config()
                        editing_slider_update = update(minimum=editing_min, maximum=editing_max, step=1, value=editing_default, visible=True)
                    else:
                        transcript_val = ""
                        transcript_visible = False
                        editing_slider_update = update(visible=False)
                else:
                    ref_audio = None
                    tar_audio = None
                    slider_update = update()
                    instructions = "Error loading test"
                    transcript_val = ""
                    transcript_visible = False
                    editing_slider_update = update(visible=False)
                
                return (
                    valid_id,
                    update(value="", visible=False),  # Hide error message
                    update(visible=False),  # Hide the entire id_input_section (email box + start button)
                    update(visible=True),   # Show the test_interface
                    instructions,
                    ref_audio,
                    tar_audio,
                    slider_update,
                    update(visible=transcript_visible),  # emos label visibility
                    update(value=transcript_val, visible=transcript_visible),  # edited transcript
                    0,  # current_page_state (reset to 0)
                    []   # results_state (reset to empty)
                )

            # Load URL parameters when the interface loads
            interface.load(
                load_and_populate,
                outputs=[
                    url_params_state, 
                    url_params_display, 
                    email, 
                    prolific_pid,
                    id_input_section,
                    test_interface,
                    user_id,
                    instructions,
                    reference, 
                    target, 
                    score_input,
                    email,  # email visibility
                    prolific_pid,  # prolific_pid visibility
                    emos_transcript_label,  # EMOS label visibility
                    edited_transcript,  # EMOS transcript
                    editing_score_input,  # EMOS editing score slider
                    test_cases_state,  # NEW: test cases for this session
                    current_page_state,  # NEW: current page
                    results_state,  # NEW: results
                    progress_text  # NEW: progress update
                ]
            )

            submit_id.click(
                start_test,
                inputs=[email, prolific_pid, test_cases_state],
                outputs=[user_id, id_error, id_input_section, test_interface, instructions, reference, target, score_input, emos_transcript_label, edited_transcript, current_page_state, results_state]
            )

            submit_score.click(
                self.run_test,
                inputs=[user_id, score_input, target, editing_score_input, 
                       test_cases_state, current_page_state, results_state, url_params_state],
                outputs=[instructions, progress_text, reference, target, score_input, submit_score, redirect, 
                        emos_transcript_label, edited_transcript, test_cases_state, current_page_state, results_state],
            )
            
            # Update editing slider visibility when instructions change
            def update_editing_slider(instructions_text):
                if "EMOS" in str(instructions_text):
                    return update(visible=True)
                else:
                    return update(visible=False)
            
            instructions.change(
                update_editing_slider,
                inputs=[instructions],
                outputs=[editing_score_input]
            )

            redirect_url = 'https://app.prolific.com/submissions/complete?cc=C1E3KUXW'
            redirect_js = f"() => {{ window.location.href = '{redirect_url}' }}"
            redirect.click(
                lambda: None,  # No action needed, just to trigger the redirect
                outputs=[],
                js=redirect_js
            )

        return interface

if __name__ == "__main__":
    sampler = TestCasesSampler(
        './test_lists/test_list_2.json',
        sample_size_per_test=4,
    )
    test = MOSTest(case_sampler=sampler)
    interface = test.create_interface()
    interface.launch(
        allowed_paths=[os.getcwd()],
        share=True,
    )