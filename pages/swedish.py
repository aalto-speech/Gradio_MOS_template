import os
from gradio import update

from pages.english import TestPage, NoReferencePage

class SMOSPage(TestPage):
    """SMOS (Speaker Similarity) test page"""
    
    def get_instructions(self):
        return """
        ### Instruktioner för test av talarlikhet

        Du kommer att bli ombedd att lyssna på två ljudexempel: Ljud A och Ljud B

        Ljudexemplen kan ha spelats in under Olika omständigheter eller producerats med hjälp av olika tekniker.
        De kan komma från mänskliga talare eller artificiella röster.
        Din uppgift är inte att avgöra om rösten är mänsklig eller artificiell, utan helt enkelt att utvärdera om båda ljudexemplen representerar samma talare.

        Din uppgift är att lyssna igenom båda ljudexemplen helt och hållet, och sedan ge ditt omdöme. Fokusera på talarens röstegenskaper (till exempel ton, tonhöjd, och talstil), snarare än på bakgrundsljud, inspelningskvalitet och innehåll.

        Använd denna 5-gradiga skala för din bedömning:
        - -2 - inte samma talare
        - -1 - troligen inte samma talare
        - 0 - osäker
        - 1 - troligen samma talare 
        - 2 - samma talare

        Det är viktigt att du litar på ditt första intryck och inte övertänker ditt beslut. 
        Använd bara "osäker" undantagsvis, då du verkligen inte lutar åt något håll alls.
        """
    
    def get_slider_config(self):
        return -2, 2, 0  # min, max, default
    
    def get_level_label(self):
        return [
            "inte samma talare", 
            "troligen inte samma talare",
            "osäker",
            "troligen samma talare",
            "samma talare"
        ]


class SMOSInstructionPage(SMOSPage):
    """SMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Instruktioner för test av talarlikhet

        Du kommer att bli ombedd att lyssna på två ljudexempel: Ljud A och Ljud B

        Ljudexemplen kan ha spelats in under Olika omständigheter eller producerats med hjälp av olika tekniker.
        De kan komma från mänskliga talare eller artificiella röster.
        Din uppgift är inte att avgöra om rösten är mänsklig eller artificiell, utan helt enkelt att utvärdera om båda ljudexemplen representerar samma talare.

        Din uppgift är att lyssna igenom båda ljudexemplen helt och hållet, och sedan ge ditt omdöme. Fokusera på talarens röstegenskaper (till exempel ton, tonhöjd, och talstil), snarare än på bakgrundsljud, inspelningskvalitet och innehåll.

        Använd denna 5-gradiga skala för din bedömning:
        - -2 - inte samma talare
        - -1 - troligen inte samma talare
        - 0 - osäker
        - 1 - troligen samma talare 
        - 2 - samma talare

        Det är viktigt att du litar på ditt första intryck och inte övertänker ditt beslut.

        Använd bara "osäker" undantagsvis, då du verkligen inte lutar åt något håll alls.

        **Detta är en riktlinjefråga. Du bör betygsätta frågan med poängen 2 - Samma talare eftersom både ljud A och ljud B kommer från samma talare.**
        """


class CMOSPage(TestPage):
    """CMOS (Comparative Mean Opinion Score) test page"""
    
    def get_instructions(self):
        return """
        ### Instruktioner för test av människolikhet

        Du kommer att bli ombedd att lyssna på två ljudexempel: Ljud A och Ljud B.

        Din uppgift är att jämföra de två ljudexemplen och avgöra vilket som låter mest som en mänsklig röst. Du ska inte avgöra om rösten verkligen kommer från en människa, utan bara vilken som låter mest människolik.

        Ljudexemplen kan skilja i hur de spelades in, hur de pproducerades, och i talstil. Fokusera på rösten i sig, inte på bakgrundsljud, inspelningskvalitet, eller innehåll.


        Använd denna 7-gradiga skala för din bedömning:

        - -3 - Audio A är mycket mer människolik
        - -2 - Audio A är mer människolik
        - -1 - Audio A är lite mer människolik
        - 0 - De låter lika människolika
        - 1 - Audio B är lite mer människolik
        - 2 - Audio B är mer människolik
        - 3 - Audio B är mycket mer människolik

        Lyssna genom båda ljudexemplen helt och hållet innan du ger ditt omdöme.
        Det är viktigt att du litar på ditt första intryck och inte övertänker ditt beslut. 
        Använd bara "lika" undantagsvis, då du verkligen inte lutar åt något håll alls.
        """
    
    def get_slider_config(self):
        return -3, 3, 0
    
    def get_level_label(self):
        return ["Audio A är mycket mer människolik",
                "Audio A är mer människolik",
                "Audio A är lite mer människolik",
                "De låter lika människolika",
                "Audio B är lite mer människolik",
                "Audio B är mer människolik",
                "Audio B är mycket mer människolik"]


class CMOSInstructionPage(CMOSPage):
    """CMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Instruktioner för test av människolikhet

        Du kommer att bli ombedd att lyssna på två ljudexempel: Ljud A och Ljud B.

        Din uppgift är att jämföra de två ljudexemplen och avgöra vilket som låter mest som en mänsklig röst. Du ska inte avgöra om rösten verkligen kommer från en människa, utan bara vilken som låter mest människolik.

        Ljudexemplen kan skilja i hur de spelades in, hur de pproducerades, och i talstil. Fokusera på rösten i sig, inte på bakgrundsljud, inspelningskvalitet, eller innehåll.


        Använd denna 7-gradiga skala för din bedömning:

        - -3 - Audio A är mycket mer människolik
        - -2 - Audio A är mer människolik
        - -1 - Audio A är lite mer människolik
        - 0 - De låter lika människolika
        - 1 - Audio B är lite mer människolik
        - 2 - Audio B är mer människolik
        - 3 - Audio B är mycket mer människolik

        Lyssna genom båda ljudexemplen helt och hållet innan du ger ditt omdöme.

        Det är viktigt att du litar på ditt första intryck och inte övertänker ditt beslut.

        Använd bara "lika" undantagsvis, då du verkligen inte lutar åt något håll alls.

        **Detta är en riktlinjefråga. Du bör betygsätta frågan med poängen 0 - De låter lika människolika eftersom både ljud A och ljud B produceras av människor.**
        """


class AttentionPage(CMOSPage):
    """Attention check page"""
    
    def get_instructions(self):
        return """
        ### Attention Check
        Both the reference and target audios are identical, they are instructions to you on how to rate this question.

        Please rate as the audio instructed.
        - Scale: -3 to 3

        Even though the audios are identical, **please finish listening both audios before submit your answers.**
        """



class EMOSPage(NoReferencePage):
    """EMOS (Editing Mean Opinion Score) test page"""
    
    def __init__(self, test_case):
        raise NotImplementedError("EMOS test is not ready for Finnish yet.")


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
        # "emos_instruction": EMOSInstructionPage,
        # "nmos": NMOSPage,
        # "NMOS": NMOSPage,
        # "nmos_instruction": NMOSInstructionPage,
        # "qmos": QMOSPage,
        # "QMOS": QMOSPage,
        # "qmos_instruction": QMOSInstructionPage,
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


