import os
from gradio import update

from pages.english import TestPage, NoReferencePage

class SMOSPage(TestPage):
    """SMOS (Speaker Similarity) test page"""
    
    def get_instructions(self):
        return """
        ### Puhujan samankaltaisuuden arviointi (similarity)

        Sinua pyydetään kuuntelemaan kahta ääninäytettä: Ääni A ja Ääni B.

        Ääninäytteet on voitu tallentaa eri olosuhteissa tai tuottaa eri tekniikoilla. Äänet voivat olla ihmisen tuottamia tai ne voivat olla keinotekoisia. Tehtäväsi ei ole tunnistaa, onko ääni ihmisen tuottama vai keinotekoinen, vaan yksinkertaisesti arvioida, edustavatko molemmat näytteet samaa puhujaa.

        Tehtäväsi on kuunnella molemmat ääninäytteet kokonaan ja antaa arviosi. Keskity puhujan äänellisiin ominaisuuksiin (kuten sävyyn, äänenkorkeuteen ja puhetapaan) sen sijaan, että kiinnittäisit huomiota taustameluun, tallennuslaatuun tai sisältöön.

        Käytä seuraavaa 5-portaista asteikkoa arvioinnissasi:
        - -2 - Ei sama puhuja
        - -1 - Todennäköisesti ei sama puhuja
        - 0 - En osaa sanoa
        - 1 - Todennäköisesti sama puhuja
        - 2 - Sama puhuja

        Luota ensivaikutelmaasi äläkä mieti päätöstäsi liikaa.
        Käytä "En osaa sanoa" -vaihtoehtoa vain satunnaisesti, jos et todella kallistu kumpaankaan suuntaan.
        """
    
    def get_slider_config(self):
        return -2, 2, 0  # min, max, default
    
    def get_level_label(self):
        return [
            "Ei sama puhuja", 
            "Todennäköisesti ei sama puhuja",
            "En osaa sanoa",
            "Todennäköisesti sama puhuja",
            "Sama puhuja"
        ]


class SMOSInstructionPage(SMOSPage):
    """SMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Puhujan samankaltaisuuden arviointi (similarity)

        Sinua pyydetään kuuntelemaan kahta ääninäytettä: Ääni A ja Ääni B.

        Ääninäytteet on voitu tallentaa eri olosuhteissa tai tuottaa eri tekniikoilla. Äänet voivat olla ihmisen tuottamia tai ne voivat olla keinotekoisia. Tehtäväsi ei ole tunnistaa, onko ääni ihmisen tuottama vai keinotekoinen, vaan yksinkertaisesti arvioida, edustavatko molemmat näytteet samaa puhujaa.

        Tehtäväsi on kuunnella molemmat ääninäytteet kokonaan ja antaa arviosi. Keskity puhujan äänellisiin ominaisuuksiin (kuten sävyyn, äänenkorkeuteen ja puhetapaan) sen sijaan, että kiinnittäisit huomiota taustameluun, tallennuslaatuun tai sisältöön.

        Käytä seuraavaa 5-portaista asteikkoa arvioinnissasi:
        - -2 - Ei sama puhuja
        - -1 - Todennäköisesti ei sama puhuja
        - 0 - En osaa sanoa
        - 1 - Todennäköisesti sama puhuja
        - 2 - Sama puhuja

        Luota ensivaikutelmaasi äläkä mieti päätöstäsi liikaa.

        Käytä "En osaa sanoa" -vaihtoehtoa vain satunnaisesti, jos et todella kallistu kumpaankaan suuntaan.

        **Tämä on ohjekysymys. Sinun tulisi arvioida tämä kysymys arvosanalla 2 - Sama puhuja, koska sekä äänellä A että äänellä B on sama kaiutin.**
        """


class CMOSPage(TestPage):
    """CMOS (Comparative Mean Opinion Score) test page"""
    
    def get_instructions(self):
        return """
        ### Puheen ihmismäisyyden arviointi (human-likeness)

        Sinua pyydetään kuuntelemaan kahta ääninäytettä: Ääni A ja Ääni B.

        Tehtäväsi on verrata kahta ääninäytettä ja arvioida, kumpi näytteistä kuulostaa enemmän ihmisääneltä. Tehtäväsi ei ole tunnistaa, onko ääni ihmisen tuottama vai keinotekoinen, vaan arvioida, kuinka ihmisen kaltaisilta näytteet kuulostavat.

        Ääninäytteet on voitu tallentaa eri olosuhteissa tai tuottaa eri tekniikoilla, ja ne voivat sisältää erilaisia puhetyylejä. Keskity puheäänen ominaisuuksiin, äläkä kiinnitä huomiota taustameluun, tallennuslaatuun tai sisältöön.

        Käytä seuraavaa 7-portaista asteikkoa arvioinnissasi:
        - -3 - Ääni A kuulostaa paljon enemmän ihmisen kaltaiselta
        - -2 - Ääni A kuulostaa enemmän ihmisen kaltaiselta
        - -1 - Ääni A kuulostaa hieman enemmän ihmisen kaltaiselta
        - 0 - Molemmat kuulostavat yhtä ihmisen kaltaisilta
        - 1 - Ääni B kuulostaa hieman enemmän ihmisen kaltaiselta
        - 2 - Ääni B kuulostaa enemmän ihmisen kaltaiselta
        - 3 - Ääni B kuulostaa paljon enemmän ihmisen kaltaiselta

        Kuuntele molemmat ääninäytteet kokonaan ennen arviosi antamista. Luota ensivaikutelmaasi äläkä mieti päätöstäsi liikaa. Käytä "0" -vaihtoehtoa vain satunnaisesti, jos et todella löydä eroa kahden näytteen välillä.
        """
    
    def get_slider_config(self):
        return -3, 3, 0
    
    def get_level_label(self):
        return ["Ääni A kuulostaa paljon enemmän ihmisen kaltaiselta",
                "Ääni A kuulostaa enemmän ihmisen kaltaiselta",
                "Ääni A kuulostaa hieman enemmän ihmisen kaltaiselta",
                "Molemmat kuulostavat yhtä ihmisen kaltaisilta",
                "Ääni B kuulostaa hieman enemmän ihmisen kaltaiselta",
                "Ääni B kuulostaa enemmän ihmisen kaltaiselta",
                "Ääni B kuulostaa paljon enemmän ihmisen kaltaiselta"]


class CMOSInstructionPage(CMOSPage):
    """CMOS instruction page"""
    
    def get_instructions(self):
        return """
        ### Puheen ihmismäisyyden arviointi (human-likeness)

        Sinua pyydetään kuuntelemaan kahta ääninäytettä: Ääni A ja Ääni B.

        Tehtäväsi on verrata kahta ääninäytettä ja arvioida, kumpi näytteistä kuulostaa enemmän ihmisääneltä. Tehtäväsi ei ole tunnistaa, onko ääni ihmisen tuottama vai keinotekoinen, vaan arvioida, kuinka ihmisen kaltaisilta näytteet kuulostavat.

        Ääninäytteet on voitu tallentaa eri olosuhteissa tai tuottaa eri tekniikoilla, ja ne voivat sisältää erilaisia puhetyylejä. Keskity puheäänen ominaisuuksiin, äläkä kiinnitä huomiota taustameluun, tallennuslaatuun tai sisältöön.

        Käytä seuraavaa 7-portaista asteikkoa arvioinnissasi:
        
        - -3 - Ääni A kuulostaa paljon enemmän ihmisen kaltaiselta
        - -2 - Ääni A kuulostaa enemmän ihmisen kaltaiselta
        - -1 - Ääni A kuulostaa hieman enemmän ihmisen kaltaiselta
        - 0 - Molemmat kuulostavat yhtä ihmisen kaltaisilta
        - 1 - Ääni B kuulostaa hieman enemmän ihmisen kaltaiselta
        - 2 - Ääni B kuulostaa enemmän ihmisen kaltaiselta
        - 3 - Ääni B kuulostaa paljon enemmän ihmisen kaltaiselta

        Kuuntele molemmat ääninäytteet kokonaan ennen arviosi antamista. Luota ensivaikutelmaasi äläkä mieti päätöstäsi liikaa. Käytä "0" -vaihtoehtoa vain satunnaisesti, jos et todella löydä eroa kahden näytteen välillä.

        **Tämä on ohjekysymys. Sinun tulisi arvioida tämä kysymys arvosanalla 0 - Molemmat kuulostavat yhtä ihmisiltä, koska sekä ääni A että ääni B ovat ihmisen tuottamia.**
        """


class AttentionPage(CMOSPage):
    """Attention check page"""
    
    def get_instructions(self):
        return """
        ### Huomiotarkistus
        Sekä viite- että kohdeäänitteet ovat identtisiä, ne ovat ohjeita sinulle tämän kysymyksen arvioimiseksi.

        Käytä seuraavaa 7-portaista asteikkoa arvioinnissasi:

        - -3 - Ääni A kuulostaa paljon enemmän ihmisen kaltaiselta
        - -2 - Ääni A kuulostaa enemmän ihmisen kaltaiselta
        - -1 - Ääni A kuulostaa hieman enemmän ihmisen kaltaiselta
        - 0 - Molemmat kuulostavat yhtä ihmisen kaltaisilta
        - 1 - Ääni B kuulostaa hieman enemmän ihmisen kaltaiselta
        - 2 - Ääni B kuulostaa enemmän ihmisen kaltaiselta
        - 3 - Ääni B kuulostaa paljon enemmän ihmisen kaltaiselta

        Vaikka äänitteet ovat identtiset, **kuuntele molemmat äänitteet loppuun ennen vastaustesi lähettämistä.**
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


