import gradio as gr
import json
import os
import random
from typing import List
from gradio import update

from utils import is_valid_email, TestCasesSampler
from pages import PageFactory, EMOSPage

class MOSTest:
    def __init__(self, test_cases: List):
        # Keep the structure of test_cases as a list
        self.test_cases = test_cases

        # Add attention check cases
        self.test_cases.extend([
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
        ])
        random.shuffle(self.test_cases)
        instruction_pages = [
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
        self.test_cases = instruction_pages + self.test_cases
        # self.test_cases = [
        #     {
        #         "type": "smos_instruction",
        #         "reference": "audios/1.wav",
        #         "target": "audios/1.wav"
        #     },
        #     {
        #         "type": "cmos_instruction",
        #         "reference": "audios/4.wav",
        #         "target": "audios/4.wav"
        #     },
        #     {
        #         "type": "emos_instruction",
        #         "reference": "",  # Not used for EMOS
        #         "target": "audios/4.wav",
        #         "edited_transcript": "This is the edited transcript that the instruction speech should correspond to."
        #     },
        #     {
        #         "type": "qmos_instruction",
        #         "reference": None,
        #         "target": "audios/2.wav",
        #     },
        #     {
        #         "type": "emos",
        #         "reference": "",  # Not used for EMOS
        #         "target": "audios/3.wav",
        #         "edited_transcript": "This is the edited transcript that the speech should correspond to."
        #     },
        #     {
        #         "type": "smos",
        #         "reference": "audios/1.wav",
        #         "target": "audios/2.wav"
        #     },
        #     {
        #         "type": "cmos",
        #         "reference": "audios/3.wav",
        #         "target": "audios/4.wav"
        #     },
        #     {
        #         "type": 'attention',
        #         'reference': 'audios/attention_high.wav',
        #         'target': 'audios/attention_high.wav'
        #     }
        # ]
        self.current_page = 0
        self.total_pages = len(self.test_cases)
        self.results = []
        self.url_params = {}

    def capture_url_params(self, request: gr.Request):
        """Capture URL query parameters from the request"""
        if request and hasattr(request, 'query_params'):
            self.url_params = dict(request.query_params)
        return self.url_params

    def get_param_value(self, param_name, default=""):
        """Get a specific parameter value from URL parameters"""
        return self.url_params.get(param_name, default)

    def get_current_page(self):
        """Get the current test page object"""
        if self.current_page < len(self.test_cases):
            test_case = self.test_cases[self.current_page]
            return PageFactory.create_page(test_case)
        return None

    def get_initial_test_updates(self):
        """Get the initial test page updates when auto-starting"""
        page = self.get_current_page()
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

    def run_test(self, user_id, naturalness_score, audio_played, editing_score=None):
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
        if not user_id or self.current_page >= self.total_pages:
            return instructions, progress, ref_audio, tar_audio, submit_score, redirect, emos_label, transcript
            
        # Check that the target audio was played
        if audio_played is None:
            progress = f"Progress: {self.current_page}/{self.total_pages} ({int(self.current_page/self.total_pages*100)}%)"
            return instructions, progress, ref_audio, tar_audio, submit_score, redirect, emos_label, transcript
        
        # Get current page and validate score
        current_page = self.get_current_page()
        if current_page and not current_page.validate_score(naturalness_score):
            # Could add score validation error handling here
            pass
        
        test_case = self.test_cases[self.current_page]
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
        if isinstance(current_page, EMOSPage):
            result_entry["naturalness_score"] = naturalness_score
            result_entry["editing_score"] = editing_score
            result_entry["edited_transcript"] = current_page.get_edited_transcript()
            # Remove the generic "score" for EMOS to avoid confusion
            del result_entry["score"]
        
        # Add URL parameters to the result if they exist
        if self.url_params:
            result_entry["url_params"] = self.url_params
            
        self.results.append(result_entry)

        self.current_page += 1
        progress = f"Progress: {self.current_page}/{self.total_pages} ({int(self.current_page/self.total_pages*100)}%)"

        if self.current_page >= self.total_pages:
            filename = f"results/{user_id}_results.json"

            os.makedirs("results/", exist_ok=True)
            
            # Add timestamp to the results
            final_results = {
                "user_id": user_id,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "results": self.results
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
                transcript
            )

        # Get next page configuration
        next_page = self.get_current_page()
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
            update(value=ref_audio),
            update(value=tar_audio),
            slider_update,
            submit_score,
            redirect,
            emos_label,
            transcript
        )

    def create_interface(self):
        with gr.Blocks() as interface:
            user_id = gr.State(value=None)
            url_params_state = gr.State(value={})
            
            # Add a component to display URL parameters (optional, for debugging)
            url_params_display = gr.JSON(label="URL Parameters", visible=False)
            
            # Conditional input fields - will be shown/hidden based on URL parameters
            with gr.Column() as id_input_section:
                email = gr.Textbox(label="Email", visible=True)
                prolific_pid = gr.Textbox(label="Prolific PID", visible=False)  # Hidden by default
                
                id_error = gr.Markdown("", visible=False)
                submit_id = gr.Button("Start Test")

            with gr.Column(visible=False) as test_interface:
                progress_text = gr.HTML(f"Progress: 0/{self.total_pages}")
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
                    reference = gr.Audio(label="Reference Audio")
                    target = gr.Audio(label="Target Audio")
                
                # Get initial slider config from first test case
                first_page = PageFactory.create_page(self.test_cases[0])
                min_val, max_val, default_val = first_page.get_slider_config()
                
                score_input = gr.Slider(
                    minimum=min_val,
                    maximum=max_val,
                    step=1,
                    label="Your Score",
                    value=default_val
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
                
                # Reset test state for each new session/page load
                self.current_page = 0
                self.results = []
                
                # Check for PROLIFIC_PID in URL parameters (exact match only)
                prolific_pid_from_url = params.get('PROLIFIC_PID')
                
                if prolific_pid_from_url:
                    # PROLIFIC_PID found in URL - hide input section and auto-start
                    instructions_val, ref_audio, tar_audio, slider_update, transcript_val, transcript_visible, editing_slider_update = self.get_initial_test_updates()
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
                        editing_slider_update  # editing score slider
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
                        update(value=default_val),  # score input (default value)
                        update(visible=True),   # show email textbox
                        update(visible=False),   # hide prolific_pid textbox
                        update(visible=False),  # emos label (hidden)
                        update(value="", visible=False),  # edited transcript (hidden)
                        update(visible=False)  # editing score slider (hidden)
                    )

            def start_test(email_input, pid_input):
                # Modified validation to only require email if no PID is provided
                if not is_valid_email(email_input) and not pid_input:
                    return (
                        None,
                        update(value="Please provide a valid Email address", visible=True),
                        update(visible=False),
                        None,
                        None,
                        None,
                        update()
                    )
                
                # Use email as user_id, or PID if email is not provided
                valid_id = email_input if email_input else pid_input
                
                # Reset test state when starting manually
                self.current_page = 0
                self.results = []
                
                # Get first page configuration
                first_page = self.get_current_page()
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
                    update(value="", visible=False),
                    update(visible=True),
                    instructions,
                    ref_audio,
                    tar_audio,
                    slider_update,
                    update(visible=transcript_visible),  # emos label visibility
                    update(value=transcript_val, visible=transcript_visible)  # edited transcript
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
                    editing_score_input  # EMOS editing score slider
                ]
            )

            submit_id.click(
                start_test,
                inputs=[email, prolific_pid],
                outputs=[user_id, id_error, test_interface, instructions, reference, target, score_input, emos_transcript_label, edited_transcript]
            )

            submit_score.click(
                self.run_test,
                inputs=[user_id, score_input, target, editing_score_input],
                outputs=[instructions, progress_text, reference, target, score_input, submit_score, redirect, emos_transcript_label, edited_transcript],
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
    cases = sampler.sample_test_cases()
    with open('./test_lists/test_list_2_sampled.json', 'w') as f:
        json.dump(cases, f, indent=4)
    test = MOSTest(test_cases=cases)
    interface = test.create_interface()
    interface.launch(
        allowed_paths=[os.getcwd()]
    )
