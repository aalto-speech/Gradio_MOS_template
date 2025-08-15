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

    def create_radio_choices_and_default(self, page_obj, editing=False):
        """Create radio button choices with labels from page object"""
        if not editing:
            min_val, max_val, _ = page_obj.get_slider_config()  # Ignore default value
            level_labels = page_obj.get_level_label()  # Get labels for each level
        else:
            min_val, max_val, _ = page_obj.get_editing_slider_config()  # Ignore default value
            level_labels = page_obj.get_editing_level_label()
        
        choices = []
        values = []
        current = min_val
        label_index = 0
        
        while current <= max_val and label_index < len(level_labels):
            # Create choice as "value: label" format
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
            
            # Get radio button config with labels
            choices, values, _ = self.create_radio_choices_and_default(page)
            radio_update = update(choices=choices, value=None, visible=True)
            
            # Handle EMOS-specific elements
            if isinstance(page, EMOSPage):
                transcript = page.get_edited_transcript()
                transcript_visible = True
                # For EMOS editing score, we need to create a temporary page object or handle differently
                # Assuming EMOS page has editing score configuration
                editing_choices, editing_values, _ = self.create_radio_choices_and_default(page, editing=True)  # You might need separate method for editing
                editing_radio_update = update(choices=editing_choices, value=None, visible=True)
            else:
                transcript = ""
                transcript_visible = False
                editing_radio_update = update(visible=False)
                
            return instructions, ref_audio, tar_audio, radio_update, transcript, transcript_visible, editing_radio_update
        return None, None, None, None, "", False, update(visible=False)

    def validate_id(self, email, prolific_pid):
        if not email and not prolific_pid:
            return None, "Please provide either Email or Prolific PID"
        return email or prolific_pid, None

    def run_test(self, user_id, naturalness_score, ref_audio_played, target_audio_played, editing_score=None, 
                 test_cases=None, current_page=0, results=None, url_params=None):
        # Initialize session data if not provided
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
        emos_label = update()
        transcript = update()

        # Check that we have a valid user_id and are within bounds
        if not user_id or current_page >= total_pages:
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results, ref_audio_played, target_audio_played)
        
        # Get current page to check requirements
        current_page_obj = self.get_current_page(test_cases, current_page)
        needs_reference = not isinstance(current_page_obj, EMOSPage) and current_page_obj.get_reference_audio() is not None
        
        # Check that required audios were played
        if not target_audio_played:
            progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)"
            f"- Please finishing listening all given audio to completion"
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results, ref_audio_played, target_audio_played)
        
        if needs_reference and not ref_audio_played:
            progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%)" 
            f"- Please finishing listening all given audio to completion"
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results, ref_audio_played, target_audio_played)
        
        # Check that a score was selected
        if naturalness_score is None:
            progress = f"Progress: {current_page}/{total_pages} ({int(current_page/total_pages*100)}%) - Please select a score"
            return (instructions, progress, ref_audio, tar_audio, radio_update, submit_score, redirect, 
                   emos_label, transcript, test_cases, current_page, results, ref_audio_played, target_audio_played)
        
        # Extract numeric value from "value: label" format
        try:
            naturalness_score_int = int(naturalness_score.split(':')[0]) if naturalness_score else None
            editing_score_int = int(editing_score.split(':')[0]) if editing_score else None
        except (ValueError, TypeError, AttributeError):
            naturalness_score_int = None
            editing_score_int = None
        
        if current_page_obj and naturalness_score_int is not None and not current_page_obj.validate_score(naturalness_score_int):
            # Could add score validation error handling here
            pass
        
        test_case = test_cases[current_page]
        # Store result from the current page, including URL parameters
        result_entry = {
            "test_type": test_case["type"],
            "reference_audio": test_case.get("reference", ""),
            "target_audio": test_case["target"],
            "ref_system": test_case.get(
                "ref_system", ""
            ),
            "target_system": test_case.get(
                "target_system", ""
            ),
            "swap": test_case.get("swap", False),
            "score": naturalness_score_int
        }
        
        # Add editing score and transcript for EMOS tests
        if isinstance(current_page_obj, EMOSPage):
            result_entry["naturalness_score"] = naturalness_score_int
            result_entry["editing_score"] = editing_score_int
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
            radio_update = update(visible=False)
            emos_label = update(visible=False)
            transcript = update(value="", visible=False)
            return (
                instructions,
                progress,
                ref_audio,
                tar_audio,
                radio_update,
                submit_score,
                redirect,
                emos_label,
                transcript,
                test_cases,
                current_page,
                results,
                False,  # Reset ref_audio_played for next session
                False   # Reset target_audio_played for next session
            )

        # Get next page configuration
        next_page = self.get_current_page(test_cases, current_page)
        if next_page:
            instructions = next_page.get_instructions()
            ref_audio = next_page.get_reference_audio() if not isinstance(next_page, EMOSPage) else None
            tar_audio = next_page.get_target_audio()
            
            # Get radio button configuration for next page
            choices, values, _ = self.create_radio_choices_and_default(next_page)
            radio_update = update(choices=choices, value=None, visible=True)
            
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
            radio_update = update()
            emos_label = update(visible=False)
            transcript = update(value="", visible=False)
            
        # Ensure submit_score is always defined for normal progression
        submit_score = update(visible=True)
        redirect = update()
        
        return (
            update(value=instructions),
            progress,
            update(value=ref_audio, label='sample A' if isinstance(next_page, CMOSPage) else 'Reference'),
            update(value=tar_audio, label='sample B' if isinstance(next_page, CMOSPage) else 'Target'),
            radio_update,
            submit_score,
            redirect,
            emos_label,
            transcript,
            test_cases,
            current_page,
            results,
            False,  # Reset ref_audio_played for next page
            False   # Reset target_audio_played for next page
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
            
            # Add audio playback tracking state variables
            ref_audio_played_state = gr.State(value=False)
            target_audio_played_state = gr.State(value=False)
            
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
                
                # Replace slider with radio buttons for score input
                score_input = gr.Radio(
                    choices=[],
                    value=None,
                    label="Your Score",
                    interactive=True
                )
                
                # EMOS editing effect radio buttons
                editing_score_input = gr.Radio(
                    choices=[],
                    value=None,
                    label="Editing Effect Score",
                    visible=False,
                    interactive=True
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
                    instructions_val, ref_audio, tar_audio, radio_update, transcript_val, transcript_visible, editing_radio_update = self.get_initial_test_updates(new_test_cases)
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
                        radio_update,  # score input radio
                        update(visible=False),  # hide email textbox
                        update(visible=False),   # hide prolific_pid textbox
                        update(visible=transcript_visible),  # emos label visibility
                        update(value=transcript_val, visible=transcript_visible),  # edited transcript
                        editing_radio_update,  # editing score radio
                        new_test_cases,  # test_cases_state
                        0,  # current_page_state
                        [],  # results_state
                        f"Progress: 0/{total_pages} (0%)",  # progress_text
                        False,  # ref_audio_played_state
                        False   # target_audio_played_state
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
                        update(value=None),  # score input (no default value)
                        update(visible=True),   # show email textbox
                        update(visible=False),   # hide prolific_pid textbox
                        update(visible=False),  # emos label (hidden)
                        update(value="", visible=False),  # edited transcript (hidden)
                        update(visible=False),  # editing score radio (hidden)
                        new_test_cases,  # test_cases_state (still set for when they start)
                        0,  # current_page_state
                        [],  # results_state
                        f"Progress: 0/{total_pages} (0%)",  # progress_text
                        False,  # ref_audio_played_state
                        False   # target_audio_played_state
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
                    instructions = first_page.get_instructions()
                    
                    # Get radio button configuration with labels
                    choices, values, _ = self.create_radio_choices_and_default(first_page)
                    radio_update = update(choices=choices, value=None, visible=True)
                    
                    # Handle EMOS-specific elements
                    if isinstance(first_page, EMOSPage):
                        transcript_val = first_page.get_edited_transcript()
                        transcript_visible = True
                        # For EMOS editing, you might need a separate method or handle differently
                        editing_choices, editing_values, _ = self.create_radio_choices_and_default(first_page, editing=True)
                        editing_radio_update = update(choices=editing_choices, value=None, visible=True)
                    else:
                        transcript_val = ""
                        transcript_visible = False
                        editing_radio_update = update(visible=False)
                else:
                    ref_audio = None
                    tar_audio = None
                    radio_update = update()
                    instructions = "Error loading test"
                    transcript_val = ""
                    transcript_visible = False
                    editing_radio_update = update(visible=False)
                
                return (
                    valid_id,
                    update(value="", visible=False),  # Hide error message
                    update(visible=False),  # Hide the entire id_input_section (email box + start button)
                    update(visible=True),   # Show the test_interface
                    instructions,
                    ref_audio,
                    tar_audio,
                    radio_update,
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
                    editing_score_input,  # EMOS editing score radio
                    test_cases_state,  # NEW: test cases for this session
                    current_page_state,  # NEW: current page
                    results_state,  # NEW: results
                    progress_text,  # NEW: progress update
                    ref_audio_played_state,  # NEW: reference audio played tracking
                    target_audio_played_state  # NEW: target audio played tracking
                ]
            )

            submit_id.click(
                start_test,
                inputs=[email, prolific_pid, test_cases_state],
                outputs=[user_id, id_error, id_input_section, test_interface, instructions, reference, target, score_input, emos_transcript_label, edited_transcript, current_page_state, results_state]
            )

            # Audio playback tracking - set state to True when audio finishes playing
            def mark_ref_audio_played():
                return True
            
            def mark_target_audio_played():
                return True

            reference.stop(
                mark_ref_audio_played,
                outputs=[ref_audio_played_state]
            )
            
            target.stop(
                mark_target_audio_played,
                outputs=[target_audio_played_state]
            )

            submit_score.click(
                self.run_test,
                inputs=[user_id, score_input, ref_audio_played_state, target_audio_played_state, editing_score_input, 
                       test_cases_state, current_page_state, results_state, url_params_state],
                outputs=[instructions, progress_text, reference, target, score_input, submit_score, redirect, 
                        emos_transcript_label, edited_transcript, test_cases_state, current_page_state, results_state,
                        ref_audio_played_state, target_audio_played_state],
            )
            
            # Update editing radio visibility when instructions change
            def update_editing_radio(instructions_text):
                if "EMOS" in str(instructions_text):
                    return update(visible=True)
                else:
                    return update(visible=False)
            
            instructions.change(
                update_editing_radio,
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
        './test_lists/test_list_webhome_Finnish.json',
        sample_size_per_test=4,
    )
    test = MOSTest(case_sampler=sampler)
    interface = test.create_interface()
    interface.launch(
        allowed_paths=[os.getcwd()],
        share=True,
    )
