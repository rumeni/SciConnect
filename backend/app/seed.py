from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
)
from app.modules.catalog.service import link_analysis_instrument


def seed() -> None:
    with SessionLocal.begin() as db:
        if db.scalar(select(Institution.id).limit(1)) is not None:
            print("Seed skipped: institutions already exist.")
            return

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
                contact_email="contact.virology@example.org",
                status="active",
            ),
            "chemistry": Institution(
                name="Center for Analytical Chemistry",
                slug="center-for-analytical-chemistry",
                description="Analytical chemistry, proteomics and chromatography facility.",
                city="Novi Sad",
                country="Serbia",
                website="https://example.org/chemistry",
                contact_email="laboratory.chemistry@example.org",
                status="active",
            ),
            "genetics": Institution(
                name="Institute of Molecular Genetics",
                slug="institute-of-molecular-genetics",
                description="Molecular diagnostics and high-throughput sequencing facility.",
                city="Belgrade",
                country="Serbia",
                website="https://example.org/genetics",
                contact_email="office.genetics@example.org",
                status="active",
            ),
            "veterinary": Institution(
                name="Faculty of Veterinary Medicine Core Facility",
                slug="veterinary-medicine-core-facility",
                description="Shared veterinary diagnostics and cell analysis facility.",
                city="Belgrade",
                country="Serbia",
                website="https://example.org/veterinary",
                contact_email="core.veterinary@example.org",
                status="active",
            ),
            "environment": Institution(
                name="Environmental Research Center",
                slug="environmental-research-center",
                description="Environmental microbiology and contaminant analysis laboratory.",
                city="Nis",
                country="Serbia",
                website="https://example.org/environment",
                contact_email="lab.environment@example.org",
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

        def add_offering(
            institution_key: str,
            analysis_type: str,
            public_name: str,
            turnaround_days: int,
            instrument_keys: list[str],
            target_names: list[str] | None = None,
            availability: str = "available",
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
            return offering

        add_offering(
            "virology",
            "Real-Time PCR Detection",
            "Respiratory virus RT-PCR detection",
            2,
            ["virology_pcr"],
            ["SARS-CoV-2", "Influenza A virus", "Human cytomegalovirus"],
        )
        add_offering(
            "virology",
            "Whole Genome Sequencing",
            "Viral whole genome sequencing",
            7,
            ["virology_seq"],
            ["SARS-CoV-2", "Influenza A virus"],
        )
        add_offering(
            "chemistry",
            "Proteomics by Mass Spectrometry",
            "Quantitative proteomics service",
            10,
            ["chemistry_ms"],
        )
        add_offering(
            "chemistry",
            "HPLC Compound Analysis",
            "Small molecule HPLC analysis",
            5,
            ["chemistry_hplc"],
        )
        add_offering(
            "genetics",
            "Real-Time PCR Detection",
            "Molecular pathogen detection",
            3,
            ["genetics_pcr"],
            ["Human cytomegalovirus", "Candida albicans"],
        )
        add_offering(
            "genetics",
            "Whole Genome Sequencing",
            "Microbial whole genome sequencing",
            12,
            ["genetics_seq"],
            ["Escherichia coli", "Listeria monocytogenes", "Candida albicans"],
        )
        add_offering(
            "veterinary",
            "Real-Time PCR Detection",
            "Veterinary pathogen RT-PCR panel",
            2,
            ["veterinary_pcr"],
            ["Influenza A virus", "Escherichia coli"],
            availability="limited",
        )
        add_offering(
            "veterinary",
            "Flow Cytometry",
            "Veterinary immune cell phenotyping",
            4,
            ["veterinary_flow"],
        )
        add_offering(
            "environment",
            "HPLC Compound Analysis",
            "Environmental contaminant analysis",
            6,
            ["environment_hplc"],
        )
        add_offering(
            "environment",
            "Electron Microscopy",
            "Microbial ultrastructure imaging",
            8,
            ["environment_em"],
            ["Escherichia coli", "Listeria monocytogenes"],
        )

    print(
        "Seed completed: 5 institutions, 11 instruments, 10 analysis offerings, "
        "and 6 microorganisms."
    )


if __name__ == "__main__":
    seed()
