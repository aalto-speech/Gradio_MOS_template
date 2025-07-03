import os
from abc import ABC, abstractmethod

from gradio import update

class TestPage(ABC):
    """Abstract base class for test pages"""
    
    def __init__(self, test_case):
        self.test_case = test_case
        self.test_type = test_case["type"]
        self.reference = test_case["reference"]
        self.target = test_case["target"]
    
    @abstractmethod
    def get_instructions(self):
        """Return the instructions for this test type"""
        pass
    
    @abstractmethod
    def get_slider_config(self):
        """Return slider configuration (min, max, default)"""
        pass
    
    def get_audio_path(self, audio_file):
        """Convert relative audio file paths to absolute if needed"""
        if not os.path.isabs(audio_file):
            return os.path.abspath(audio_file)
        return audio_file
    
    def get_reference_audio(self):
        return self.get_audio_path(self.reference)
    
    def get_target_audio(self):
        return self.get_audio_path(self.target)
    
    def get_slider_update(self):
        """Get slider update configuration"""
        minimum, maximum, default = self.get_slider_config()
        return update(minimum=minimum, maximum=maximum, step=1, value=default)
    
    def validate_score(self, score):
        """Validate if the score is within acceptable range"""
        minimum, maximum, _ = self.get_slider_config()
        return minimum <= score <= maximum


class SMOSPage(TestPage):
    """SMOS (Speaker Similarity) test page"""
    
    def get_instructions(self):
        return """
        ### Speaker Similarity Test (SMOS)
        Please rate how similar the voice in the target audio is to the reference audio.
        - Scale: 1-5 (1: Very Different, 5: Very Similar)
        - Use whole numbers only
        """
    
    def get_slider_config(self):
        return 1, 5, 3  # min, max, default


class SMOSInstructionPage(TestPage):
    """SMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Speaker Similarity Test - Instruction (SMOS)
        **This is an instruction example where both audios are from the same speaker with different content.**
        
        Please rate how similar the voice in the target audio is to the reference audio.
        - Scale: 1-5 (1: Very Different, 5: Very Similar)
        - **For this instruction example, you should give a score of 5 since it's the same speaker**
        - Use whole numbers only
        """
    
    def get_slider_config(self):
        return 1, 5, 3


class CMOSPage(TestPage):
    """CMOS (Comparative Mean Opinion Score) test page"""
    
    def get_instructions(self):
        return """
        ### Comparative Mean Opinion Score Test (CMOS)
        Please compare the naturalness of the target audio against the reference audio.
        - Scale: -3 to +3
        - Negative: Reference is better
        - Positive: Target is better
        - 0: Equal quality
        """
    
    def get_slider_config(self):
        return -3, 3, 0


class CMOSInstructionPage(TestPage):
    """CMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Comparative Mean Opinion Score Test - Instruction (CMOS)
        **This is an instruction example where both audios are natural speech with equal quality.**
        
        Please compare the naturalness of the target audio against the reference audio.
        - Scale: -3 to +3
        - Negative: Reference is better
        - Positive: Target is better
        - **For this instruction example, you should give a score of 0 since both are natural speech with equal quality**
        """
    
    def get_slider_config(self):
        return -3, 3, 0


class AttentionPage(TestPage):
    """Attention check page"""
    
    def get_instructions(self):
        return """
        ### Attention Check
        Both the reference and target audios are identical.
        Please rate as the instruction instructed.
        - Scale: 1-5
        """
    
    def get_slider_config(self):
        return 1, 5, 3


class PageFactory:
    """Factory class to create appropriate test pages"""
    
    PAGE_CLASSES = {
        "smos": SMOSPage,
        "smos_instruction": SMOSInstructionPage,
        "cmos": CMOSPage,
        "cmos_instruction": CMOSInstructionPage,
        "attention": AttentionPage,
    }
    
    @classmethod
    def create_page(cls, test_case):
        """Create a test page based on test case type"""
        test_type = test_case["type"]
        page_class = cls.PAGE_CLASSES.get(test_type)
        
        if page_class is None:
            raise ValueError(f"Unknown test type: {test_type}")
        
        return page_class(test_case)
    
    @classmethod
    def register_page_type(cls, test_type, page_class):
        """Register a new page type"""
        cls.PAGE_CLASSES[test_type] = page_class
