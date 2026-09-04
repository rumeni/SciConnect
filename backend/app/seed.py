from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
    Researcher,
)
from app.modules.catalog.service import link_analysis_instrument, link_analysis_researcher

CATALOG_MODELS = (Institution, InstrumentType, AnalysisType, Microorganism, Researcher)


def is_empty(db: Session) -> bool:
    """True when no catalog record exists yet, so a seed cannot collide."""
    return all(db.scalar(select(model.id).limit(1)) is None for model in CATALOG_MODELS)


def seed_catalog(db: Session) -> str:
    """Populate an empty catalog and report what happened."""
    if not is_empty(db):
        return "Seed skipped: the catalog already contains data."

    instrument_types = {
        name: InstrumentType(name=name)
        for name in [
            "Real-Time PCR System",
            "Mass Spectrometer",
            "Next-Generation Sequencer",
            "Flow Cytometer",
            "High-Performance Liquid Chromatograph",
            "Electron Microscope",
        ]
    }
    analysis_types = {
        name: AnalysisType(name=name)
        for name in [
            "Real-Time PCR Detection",
            "Whole Genome Sequencing",
            "Proteomics by Mass Spectrometry",
            "Flow Cytometry",
            "HPLC Compound Analysis",
            "Electron Microscopy",
        ]
    }
    microorganisms = {
        name: Microorganism(scientific_name=name)
        for name in [
            "SARS-CoV-2",
            "Human cytomegalovirus",
            "Influenza A virus",
            "Escherichia coli",
            "Listeria monocytogenes",
            "Candida albicans",
        ]
    }
    db.add_all(
        [
            *instrument_types.values(),
            *analysis_types.values(),
            *microorganisms.values(),
        ]
    )
    db.flush()

    institutions = {
        "virology": Institution(
            name="Institute of Virology",
            slug="institute-of-virology",
            description="Viral diagnostics and genomic surveillance research center.",
            city="Belgrade",
            country="Serbia",
            website="https://example.org/virology",
            address="Bulevar despota Stefana 142",
            contact_email="contact.virology@example.org",
            latitude=44.8069,
            longitude=20.4744,
            status="active",
        ),
        "chemistry": Institution(
            name="Center for Analytical Chemistry",
            slug="center-for-analytical-chemistry",
            description="Analytical chemistry, proteomics and chromatography facility.",
            city="Novi Sad",
            country="Serbia",
            website="https://example.org/chemistry",
            address="Trg Dositeja Obradovica 3",
            contact_email="laboratory.chemistry@example.org",
            latitude=45.2452,
            longitude=19.8512,
            status="active",
        ),
        "genetics": Institution(
            name="Institute of Molecular Genetics",
            slug="institute-of-molecular-genetics",
            description="Molecular diagnostics and high-throughput sequencing facility.",
            city="Belgrade",
            country="Serbia",
            website="https://example.org/genetics",
            address="Vojvode Stepe 458",
            contact_email="office.genetics@example.org",
            latitude=44.8206,
            longitude=20.46,
            status="active",
        ),
        "veterinary": Institution(
            name="Faculty of Veterinary Medicine Core Facility",
            slug="veterinary-medicine-core-facility",
            description="Shared veterinary diagnostics and cell analysis facility.",
            city="Belgrade",
            country="Serbia",
            website="https://example.org/veterinary",
            address="Bulevar oslobodjenja 18",
            contact_email="core.veterinary@example.org",
            latitude=44.8021,
            longitude=20.4869,
            status="active",
        ),
        "environment": Institution(
            name="Environmental Research Center",
            slug="environmental-research-center",
            description="Environmental microbiology and contaminant analysis laboratory.",
            city="Nis",
            country="Serbia",
            website="https://example.org/environment",
            address="Univerzitetski trg 2",
            contact_email="lab.environment@example.org",
            latitude=43.3247,
            longitude=21.9033,
            status="active",
        ),
    }
    db.add_all(institutions.values())
    db.flush()

    def add_instrument(
        institution_key: str,
        instrument_type: str,
        display_name: str,
        manufacturer: str,
        model: str,
    ) -> InstitutionInstrument:
        item = InstitutionInstrument(
            institution_id=institutions[institution_key].id,
            instrument_type_id=instrument_types[instrument_type].id,
            display_name=display_name,
            manufacturer=manufacturer,
            model=model,
            status="operational",
        )
        db.add(item)
        db.flush()
        return item

    instruments = {
        "virology_pcr": add_instrument(
            "virology",
            "Real-Time PCR System",
            "QuantStudio 7",
            "Thermo Fisher Scientific",
            "QuantStudio 7 Flex",
        ),
        "virology_seq": add_instrument(
            "virology",
            "Next-Generation Sequencer",
            "MiSeq viral genomics platform",
            "Illumina",
            "MiSeq",
        ),
        # Intentionally not linked to the chemistry offerings.
        "chemistry_pcr": add_instrument(
            "chemistry",
            "Real-Time PCR System",
            "Shared PCR unit",
            "Bio-Rad",
            "CFX Opus 96",
        ),
        "chemistry_ms": add_instrument(
            "chemistry",
            "Mass Spectrometer",
            "Q Exactive proteomics platform",
            "Thermo Fisher Scientific",
            "Q Exactive Plus",
        ),
        "chemistry_hplc": add_instrument(
            "chemistry",
            "High-Performance Liquid Chromatograph",
            "Agilent analytical HPLC",
            "Agilent",
            "1260 Infinity II",
        ),
        "genetics_pcr": add_instrument(
            "genetics",
            "Real-Time PCR System",
            "CFX96 diagnostic platform",
            "Bio-Rad",
            "CFX96 Touch",
        ),
        "genetics_seq": add_instrument(
            "genetics",
            "Next-Generation Sequencer",
            "NovaSeq production sequencer",
            "Illumina",
            "NovaSeq 6000",
        ),
        "veterinary_pcr": add_instrument(
            "veterinary",
            "Real-Time PCR System",
            "LightCycler veterinary diagnostics",
            "Roche",
            "LightCycler 480 II",
        ),
        "veterinary_flow": add_instrument(
            "veterinary",
            "Flow Cytometer",
            "CytoFLEX cell analysis system",
            "Beckman Coulter",
            "CytoFLEX S",
        ),
        "environment_hplc": add_instrument(
            "environment",
            "High-Performance Liquid Chromatograph",
            "Prominence environmental HPLC",
            "Shimadzu",
            "Prominence-i LC-2030C",
        ),
        "environment_em": add_instrument(
            "environment",
            "Electron Microscope",
            "JEM microbial imaging platform",
            "JEOL",
            "JEM-1400 Plus",
        ),
    }

    def add_researcher(
        institution_key: str,
        full_name: str,
        title: str,
        email: str,
        orcid: str,
        expertise: str,
    ) -> Researcher:
        person = Researcher(
            institution_id=institutions[institution_key].id,
            full_name=full_name,
            title=title,
            email=email,
            orcid=orcid,
            expertise=expertise,
            status="active",
        )
        db.add(person)
        db.flush()
        return person

    researchers = {
        "virology_lead": add_researcher(
            "virology",
            "Milica Petrovic",
            "Principal Investigator",
            "m.petrovic@example.org",
            "0000-0002-0000-0101",
            "Respiratory virus diagnostics and molecular epidemiology.",
        ),
        "virology_genomics": add_researcher(
            "virology",
            "Nikola Ilic",
            "Genomics Specialist",
            "n.ilic@example.org",
            "0000-0002-0000-0102",
            "Viral genome assembly and variant surveillance.",
        ),
        "chemistry_lead": add_researcher(
            "chemistry",
            "Jelena Markovic",
            "Head of Proteomics",
            "j.markovic@example.org",
            "0000-0002-0000-0201",
            "Quantitative proteomics and mass spectrometry method development.",
        ),
        "chemistry_hplc": add_researcher(
            "chemistry",
            "Stefan Djordjevic",
            "Analytical Chemist",
            "s.djordjevic@example.org",
            "0000-0002-0000-0202",
            "Chromatographic separation of small molecules.",
        ),
        "genetics_lead": add_researcher(
            "genetics",
            "Ana Kovacevic",
            "Senior Research Associate",
            "a.kovacevic@example.org",
            "0000-0002-0000-0301",
            "Microbial genomics and molecular pathogen detection.",
        ),
        "veterinary_lead": add_researcher(
            "veterinary",
            "Marko Stankovic",
            "Veterinary Diagnostician",
            "m.stankovic@example.org",
            "0000-0002-0000-0401",
            "Veterinary pathogen panels and immune cell phenotyping.",
        ),
        "environment_lead": add_researcher(
            "environment",
            "Ivana Nikolic",
            "Environmental Microbiologist",
            "i.nikolic@example.org",
            "0000-0002-0000-0501",
            "Environmental contaminants and microbial ultrastructure imaging.",
        ),
    }

    def add_offering(
        institution_key: str,
        analysis_type: str,
        public_name: str,
        turnaround_days: int,
        instrument_keys: list[str],
        target_names: list[str] | None = None,
        availability: str = "available",
        researcher_roles: dict[str, str] | None = None,
    ) -> InstitutionAnalysis:
        offering = InstitutionAnalysis(
            institution_id=institutions[institution_key].id,
            analysis_type_id=analysis_types[analysis_type].id,
            public_name=public_name,
            turnaround_days=turnaround_days,
            availability=availability,
        )
        db.add(offering)
        db.flush()
        for instrument_key in instrument_keys:
            link_analysis_instrument(
                db,
                institution_analysis=offering,
                institution_instrument=instruments[instrument_key],
            )
        for target_name in target_names or []:
            db.add(
                InstitutionAnalysisTarget(
                    institution_analysis_id=offering.id,
                    microorganism_id=microorganisms[target_name].id,
                )
            )
        for researcher_key, role in (researcher_roles or {}).items():
            link_analysis_researcher(
                db,
                institution_analysis=offering,
                researcher=researchers[researcher_key],
                role=role,
            )
        return offering

    add_offering(
        "virology",
        "Real-Time PCR Detection",
        "Respiratory virus RT-PCR detection",
        2,
        ["virology_pcr"],
        ["SARS-CoV-2", "Influenza A virus", "Human cytomegalovirus"],
        researcher_roles={"virology_lead": "lead", "virology_genomics": "contributor"},
    )
    add_offering(
        "virology",
        "Whole Genome Sequencing",
        "Viral whole genome sequencing",
        7,
        ["virology_seq"],
        ["SARS-CoV-2", "Influenza A virus"],
        researcher_roles={"virology_genomics": "lead"},
    )
    add_offering(
        "chemistry",
        "Proteomics by Mass Spectrometry",
        "Quantitative proteomics service",
        10,
        ["chemistry_ms"],
        researcher_roles={"chemistry_lead": "lead"},
    )
    add_offering(
        "chemistry",
        "HPLC Compound Analysis",
        "Small molecule HPLC analysis",
        5,
        ["chemistry_hplc"],
        researcher_roles={"chemistry_hplc": "lead"},
    )
    add_offering(
        "genetics",
        "Real-Time PCR Detection",
        "Molecular pathogen detection",
        3,
        ["genetics_pcr"],
        ["Human cytomegalovirus", "Candida albicans"],
        researcher_roles={"genetics_lead": "lead"},
    )
    add_offering(
        "genetics",
        "Whole Genome Sequencing",
        "Microbial whole genome sequencing",
        12,
        ["genetics_seq"],
        ["Escherichia coli", "Listeria monocytogenes", "Candida albicans"],
        researcher_roles={"genetics_lead": "lead"},
    )
    add_offering(
        "veterinary",
        "Real-Time PCR Detection",
        "Veterinary pathogen RT-PCR panel",
        2,
        ["veterinary_pcr"],
        ["Influenza A virus", "Escherichia coli"],
        availability="limited",
        researcher_roles={"veterinary_lead": "contact"},
    )
    add_offering(
        "veterinary",
        "Flow Cytometry",
        "Veterinary immune cell phenotyping",
        4,
        ["veterinary_flow"],
        researcher_roles={"veterinary_lead": "lead"},
    )
    add_offering(
        "environment",
        "HPLC Compound Analysis",
        "Environmental contaminant analysis",
        6,
        ["environment_hplc"],
        researcher_roles={"environment_lead": "lead"},
    )
    add_offering(
        "environment",
        "Electron Microscopy",
        "Microbial ultrastructure imaging",
        8,
        ["environment_em"],
        ["Escherichia coli", "Listeria monocytogenes"],
        researcher_roles={"environment_lead": "lead"},
    )

    return (
        "Seed completed: 5 institutions, 11 instruments, 7 researchers, "
        "10 analysis offerings and 6 microorganisms."
    )


def seed() -> str:
    """Seed the configured database. Safe to run on every container start."""
    with SessionLocal.begin() as db:
        return seed_catalog(db)


if __name__ == "__main__":
    print(seed())
