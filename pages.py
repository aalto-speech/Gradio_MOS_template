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
    
    def get_reference_audio(self):
        return self.reference
    
    def get_target_audio(self):
        return self.target
    
    def get_slider_update(self):
        """Get slider update configuration"""
        minimum, maximum, default = self.get_slider_config()
        return update(minimum=minimum, maximum=maximum, step=1, value=default)
    
    def requires_correspondence_question(self):
        """Returns True if this page type requires the correspondence question"""
        return False
    
    def validate_score(self, score):
        """Validate if the score is within acceptable range"""
        minimum, maximum, _ = self.get_slider_config()
        return minimum <= score <= maximum

class NoReferencePage(TestPage):
    """Abstract base class for pages without reference audio"""
    
    def get_reference_audio(self):
        return None

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

class NMOSPage(NoReferencePage):
    """NMOS (naturalness) test page"""
    
    def get_instructions(self):
        return """
        ### Speech Naturalness Test (NMOS)
        Please rate how natural the voice in the target audio.
        - Scale: 1-5 (1: very unnatural, 2: unnatural, 3: slightly unnatural, 4: natural, 5: very natural)
        - Use whole numbers only
        """
    
    def get_slider_config(self):
        return 1, 5, 3  # min, max, default


class NMOSInstructionPage(NoReferencePage):
    """NMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Speech Naturalness Test - Instruction (NMOS)
        **This is an instruction example where the target audios is a natural speech.**
        
        Please rate how similar the voice in the target audio is to the reference audio.
        - Scale: 1-5 (1: very unnatural, 2: unnatural, 3: slightly unnatural, 4: natural, 5: very natural)
        - **For this instruction example, you should give a score of 5 since it's a natural speech**
        - Use whole numbers only
        """
    
    def get_slider_config(self):
        return 1, 5, 3

class QMOSPage(NoReferencePage):
    """QMOS (quality) test page"""
    
    def get_instructions(self):
        return """
        ### Speech Quality Test (QMOS)
        Please rate the quality of the target audio.
        - Scale: 1-5 (1: very bad, 2: bad, 3: ok, 4: good, 5: very good)
        - Use whole numbers only
        Please consider the following aspect for your rating:
        1. Rate how pleasant the speech sounds to your ear.
        2. Are there any audio artefacts, such as background noise, crackling, echo, volume inconsistencies, or digital distortions.
        3. Is the speech clear and intelligible for you.
        """
    
    def get_slider_config(self):
        return 1, 5, 3  # min, max, default


class QMOSInstructionPage(NoReferencePage):
    """QMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Speech Quality Test - Instruction (QMOS)
        **This is an instruction example where the target audios is a high-quality speech.**
        
        Please rate the quality of the target audio.
        - Scale: 1-5 (1: very bad, 2: bad, 3: ok, 4: good, 5: very good)
        - **For this instruction example, you should give a score of 5 since it's a high-quality speech**
        - Use whole numbers only
        When evaluating the quality of the speech, please consider the following aspect for your rating:
        1. How pleasant the speech sounds to your ear.
        2. Are there any audio artefacts, such as background noise, crackling, echo, volume inconsistencies, or digital distortions.
        3. Is the speech clear and intelligible for you.
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


class EMOSPage(NoReferencePage):
    """EMOS (Editing Mean Opinion Score) test page"""
    
    def __init__(self, test_case):
        super().__init__(test_case)
        self.edited_transcript = test_case.get("edited_transcript", "")
    
    def get_instructions(self):
        return """
        ### Editing Mean Opinion Score Test (EMOS)
        Please evaluate the edited speech based on the provided transcript.
        
        **Instructions:**
        1. Read the edited transcript below
        2. Listen to the edited speech
        3. Rate the naturalness of the speech (1-5 scale)
        4. Rate how well the editing is reflected in the speech (0-3 scale)
        
        **Naturalness Scale:**
        - 1: Very Unnatural
        - 5: Very Natural
        
        **Editing Effect Scale:**
        - 0: The speech doesn't reflect the editing
        - 1: Some editing is reflected
        - 2: Most of the editing is reflected
        - 3: All editing is reflected
        """
    
    def get_slider_config(self):
        return 1, 5, 3  # naturalness slider: min, max, default
    
    def get_editing_slider_config(self):
        return 0, 3, 1  # editing effect slider: min, max, default
    
    def get_edited_transcript(self):
        return self.edited_transcript
    
class EMOSInstructionPage(EMOSPage):
    def get_instructions(self):
        return """
        ### Editing Mean Opinion Score Test (EMOS)
        Please evaluate the edited speech based on the provided edited transcript.
        The edited transcript have one or more characters being edited (e.g. replaced by other characters, inserting extra characters, switching the order of characters, etc.).

        The edited transcript may contains incorrect or non-exist words, which is expected. Please focus on the naturalness of the speech and how well the editing is reflected in the speech.
        
        **Instructions:**
        1. Read the edited transcript below
        2. Listen to the edited speech
        3. Rate the naturalness of the speech (1-5 scale)
        4. Rate how well the editing is reflected in the speech (0-3 scale)
        
        **Naturalness Scale:**
        - 1: Very Unnatural
        - 5: Very Natural
        
        **Editing Effect Scale:**
        - 0: The speech doesn't reflect the editing
        - 1: Some editing is reflected
        - 2: Most of the editing is reflected
        - 3: All editing is reflected
        """


class PageFactory:
    """Factory class to create appropriate test pages"""
    
    PAGE_CLASSES = {
        "smos": SMOSPage,
        "SMOS": SMOSPage,
        "smos_instruction": SMOSInstructionPage,
        "cmos": CMOSPage,
        "CMOS": CMOSPage,
        "cmos_instruction": CMOSInstructionPage,
        "attention": AttentionPage,
        "emos": EMOSPage,
        "EMOS": EMOSPage,
        "emos_instruction": EMOSInstructionPage,
        "nmos": NMOSPage,
        "NMOS": NMOSPage,
        "nmos_instruction": NMOSInstructionPage,
        "qmos": QMOSPage,
        "QMOS": QMOSPage,
        "qmos_instruction": QMOSInstructionPage,
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


