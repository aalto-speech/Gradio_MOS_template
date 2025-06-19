import gradio as gr
import json
import os
from gradio import update

from utils import is_valid_email

class MOSTest:
    def __init__(self):
        # Keep the structure of test_cases as a list
        self.test_cases = [
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
            {
                "type": "smos",
                "reference": "audios/1.wav",
                "target": "audios/2.wav"
            },
            {
                "type": "cmos",
                "reference": "audios/3.wav",
                "target": "audios/4.wav"
            },
            {
                "type": 'attention',
                'reference': 'audios/attention_high.wav',
                'target': 'audios/attention_high.wav'
            }
        ]
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

    def get_initial_test_updates(self):
        """Get the initial test page updates when auto-starting"""
        if self.current_page < len(self.test_cases):
            first_page = self.test_cases[self.current_page]
            ref_audio = self.get_audio_path(first_page["reference"])
            tar_audio = self.get_audio_path(first_page["target"])
            slider_update = self.get_slider_update(first_page["type"])
            instructions = self.get_instructions(first_page["type"])
            return instructions, ref_audio, tar_audio, slider_update
        return None, None, None, None

    def validate_id(self, email, prolific_pid):
        if not email and not prolific_pid:
            return None, "Please provide either Email or Prolific PID"
        return email or prolific_pid, None

    def get_instructions(self, test_type):
        if test_type == "smos":
            return """
            ### Speaker Similarity Test (SMOS)
            Please rate how similar the voice in the target audio is to the reference audio.
            - Scale: 1-5 (1: Very Different, 5: Very Similar)
            - Use whole numbers only
            """
        elif test_type == "smos_instruction":
            return """
            ### Speaker Similarity Test - Instruction (SMOS)
            **This is an instruction example where both audios are from the same speaker with different content.**
            
            Please rate how similar the voice in the target audio is to the reference audio.
            - Scale: 1-5 (1: Very Different, 5: Very Similar)
            - **For this instruction example, you should give a score of 5 since it's the same speaker**
            - Use whole numbers only
            """
        elif test_type == "cmos":
            return """
            ### Comparative Mean Opinion Score Test (CMOS)
            Please compare the naturalness of the target audio against the reference audio.
            - Scale: -3 to +3
            - Negative: Reference is better
            - Positive: Target is better
            - 0: Equal quality
            """
        elif test_type == "cmos_instruction":
            return """
            ### Comparative Mean Opinion Score Test - Instruction (CMOS)
            **This is an instruction example where both audios are natural speech with equal quality.**
            
            Please compare the naturalness of the target audio against the reference audio.
            - Scale: -3 to +3
            - Negative: Reference is better
            - Positive: Target is better
            - **For this instruction example, you should give a score of 0 since both are natural speech with equal quality**
            """
        elif test_type == "attention":
            return """
            ### Attention Check
            Both the reference and target audios are identical.
            Please rate as the instruction instructed.
            - Scale: 1-5
            """
        else:
            return """
            ### Unknown Test Type
            Please follow the instructions provided.
            """

    def get_audio_path(self, audio_file):
        # Convert relative audio file paths to absolute if needed.
        if not os.path.isabs(audio_file):
            return os.path.abspath(audio_file)
        return audio_file

    def get_slider_update(self, test_type):
        # For CMOS and CMOS_instruction, use -3 to 3; for SMOS, SMOS_instruction and attention, use 1 to 5.
        if test_type in ["cmos", "cmos_instruction"]:
            minimum, maximum, default = -3, 3, 0
        else:  # smos, smos_instruction, attention
            minimum, maximum, default = 1, 5, 3
        return update(minimum=minimum, maximum=maximum, step=1, value=default)

    def run_test(self, user_id, score, audio_played):

        # Set defult update values
        instructions = update()
        progress = update()
        ref_audio = update(value=None)
        tar_audio = update(value=None)
        slider_update = update(visible=False)
        submit_score = update(visible=True)
        redirect = update()  # No redirect by default

        # Check that we have a valid user_id and are within bounds
        if not user_id or self.current_page >= self.total_pages:
            return instructions, progress, ref_audio, tar_audio, submit_score, redirect
            
        # Check that the target audio was played
        if audio_played is None:
            progress = f"Progress: {self.current_page}/{self.total_pages} ({int(self.current_page/self.total_pages*100)}%)"
            return instructions, progress, ref_audio, tar_audio, submit_score, redirect
        
        test_page = self.test_cases[self.current_page]
        # Store result from the current page, including URL parameters
        result_entry = {
            "test_type": test_page["type"],
            "target_audio": test_page["target"],
            "score": score
        }
        
        # Add URL parameters to the result if they exist
        if self.url_params:
            result_entry["url_params"] = self.url_params
            
        self.results.append(result_entry)

        self.current_page += 1
        progress = f"Progress: {self.current_page}/{self.total_pages} ({int(self.current_page/self.total_pages*100)}%)"

        if self.current_page >= self.total_pages:
            filename = f"{user_id}_results.json"
            
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
            return (
                instructions,
                progress,
                ref_audio,
                tar_audio,
                slider_update,
                submit_score,
                redirect
            )

        next_page = self.test_cases[self.current_page]
        instructions = self.get_instructions(next_page["type"])
        ref_audio = self.get_audio_path(next_page["reference"])
        tar_audio = self.get_audio_path(next_page["target"])
        slider_update = self.get_slider_update(next_page["type"])
        redirect = update()  # No redirect needed yet
        return (
            update(value=instructions),
            progress,
            update(value=ref_audio),
            update(value=tar_audio),
            slider_update,
            submit_score,
            redirect
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
                
                with gr.Row():
                    reference = gr.Audio(label="Reference Audio")
                    target = gr.Audio(label="Target Audio")
                
                score_input = gr.Slider(
                    minimum=-3 if self.test_cases[0]["type"] in ["cmos", "cmos_instruction"] else 1,
                    maximum=3 if self.test_cases[0]["type"] in ["cmos", "cmos_instruction"] else 5,
                    step=1,
                    label="Score"
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
                    instructions_val, ref_audio, tar_audio, slider_update = self.get_initial_test_updates()
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
                        update(visible=False)   # hide prolific_pid textbox
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
                        update(visible=False)   # hide prolific_pid textbox
                    )

            def start_test(email_input, pid_input):
                # Modified validation to only require email if no PID is provided
                if not is_valid_email(email_input) and not pid_input:
                    return (
                        None,
                        update(value="Please provide an Email address", visible=True),
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
                
                first_page = self.test_cases[0]
                ref_audio = self.get_audio_path(first_page["reference"])
                tar_audio = self.get_audio_path(first_page["target"])
                slider_update = self.get_slider_update(first_page["type"])
                return (
                    valid_id,
                    update(value="", visible=False),
                    update(visible=True),
                    self.get_instructions(first_page["type"]),
                    ref_audio,
                    tar_audio,
                    slider_update
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
                    prolific_pid  # prolific_pid visibility
                ]
            )

            submit_id.click(
                start_test,
                inputs=[email, prolific_pid],
                outputs=[user_id, id_error, test_interface, instructions, reference, target, score_input]
            )

            submit_score.click(
                self.run_test,
                inputs=[user_id, score_input, target],
                outputs=[instructions, progress_text, reference, target, score_input, submit_score, redirect],
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
    test = MOSTest()
    interface = test.create_interface()
    interface.launch(
        allowed_paths=[os.getcwd()]
    )