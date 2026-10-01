"""Demo data for the catalogue, and the command that loads it.

    python -m app.seed            # fill an empty catalogue, do nothing otherwise
    python -m app.seed --reset    # empty it first, then fill it

Everything here is invented. The institutions, people, addresses and contact
details do not describe real organisations or real researchers; the cities and
instrument models are real so that the data reads plausibly and the map has
somewhere to put a pin.

The dataset is declarative. An institution owns instruments and employs
researchers, and offers analyses that state which of its own instruments they
use, which organisms they detect and which of its own researchers perform them.
Those statements are the point of the catalogue, so the data deliberately
includes loose ends too: instruments nobody has linked to an offering, organisms
nothing yet detects, and an offering with no target organisms at all.
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisInstrument,
    InstitutionAnalysisResearcher,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
    Researcher,
)
from app.modules.catalog.service import link_analysis_instrument, link_analysis_researcher

CATALOG_MODELS = (Institution, InstrumentType, AnalysisType, Microorganism, Researcher)

INSTRUMENT_TYPES: list[tuple[str, str]] = [
    (
        "Real-Time PCR System",
        "Thermal cycler with fluorescence detection, for quantifying a nucleic acid "
        "target as it amplifies.",
    ),
    (
        "Mass Spectrometer",
        "Ionises a sample and sorts the ions by mass to charge ratio to identify and "
        "quantify what is in it.",
    ),
    (
        "Next-Generation Sequencer",
        "Reads millions of DNA or RNA fragments in parallel.",
    ),
    (
        "Flow Cytometer",
        "Counts and characterises cells in suspension by light scatter and fluorescence.",
    ),
    (
        "High-Performance Liquid Chromatograph",
        "Separates the compounds of a liquid mixture by pushing it through a column "
        "under high pressure.",
    ),
    (
        "Electron Microscope",
        "Images specimens with a beam of electrons, resolving detail far below the "
        "limit of light.",
    ),
    (
        "Confocal Microscope",
        "Fluorescence microscope that rejects out-of-focus light, so a specimen can be "
        "imaged slice by slice.",
    ),
    (
        "Gas Chromatograph",
        "Separates volatile compounds carried through a column by an inert gas.",
    ),
    (
        "Automated Nucleic Acid Extractor",
        "Robotic platform that purifies DNA and RNA from batches of samples "
        "reproducibly.",
    ),
    (
        "Microplate Reader",
        "Measures absorbance, fluorescence or luminescence well by well across a plate.",
    ),
]

ANALYSIS_TYPES: list[tuple[str, str]] = [
    ("Real-Time PCR Detection", "Detects and quantifies a target sequence in a sample."),
    (
        "Whole Genome Sequencing",
        "Reads the complete genome of an isolate, for typing and variant calling.",
    ),
    (
        "Proteomics by Mass Spectrometry",
        "Identifies and quantifies the proteins present in a complex sample.",
    ),
    ("Flow Cytometry", "Phenotypes cell populations by surface and intracellular markers."),
    ("HPLC Compound Analysis", "Separates and quantifies small molecules in a liquid sample."),
    ("Electron Microscopy", "Images the ultrastructure of cells, tissues and particles."),
    ("Confocal Imaging", "Localises fluorescent markers within cells and tissue sections."),
    (
        "Antimicrobial Susceptibility Testing",
        "Determines which antimicrobials inhibit an isolate, and at what concentration.",
    ),
    (
        "16S rRNA Community Profiling",
        "Describes a bacterial community by sequencing a conserved marker gene.",
    ),
    (
        "ELISA Serology",
        "Measures antibodies or antigens in serum with an enzyme-linked immunoassay.",
    ),
]

# (scientific name, common name)
MICROORGANISMS: list[tuple[str, str | None]] = [
    ("SARS-CoV-2", "COVID-19 virus"),
    ("Human cytomegalovirus", "CMV"),
    ("Influenza A virus", "Flu A"),
    ("Escherichia coli", "E. coli"),
    ("Listeria monocytogenes", None),
    ("Candida albicans", None),
    ("Staphylococcus aureus", "Golden staph"),
    ("Salmonella enterica", None),
    ("Mycobacterium tuberculosis", "Tubercle bacillus"),
    ("Campylobacter jejuni", None),
    ("Legionella pneumophila", "Legionnaires' disease bacterium"),
    ("Aspergillus fumigatus", None),
    ("Clostridioides difficile", "C. diff"),
    ("Pseudomonas aeruginosa", None),
    ("Xanthomonas campestris", "Black rot bacterium"),
    ("Botrytis cinerea", "Grey mould"),
]

# Each institution: the record, what it owns, who works there, and what it offers.
# An offering names only its own institution's instruments and researchers, which
# is the invariant the service layer enforces.
INSTITUTIONS: list[dict] = [
    {
        "key": "virology",
        "name": "Institute of Virology",
        "slug": "institute-of-virology",
        "description": "Viral diagnostics and genomic surveillance research center.",
        "address": "Bulevar despota Stefana 142",
        "city": "Belgrade",
        "country": "Serbia",
        "website": "https://example.org/virology",
        "contact_email": "contact.virology@example.org",
        "latitude": 44.8069,
        "longitude": 20.4744,
        "instruments": [
            (
                "pcr",
                "Real-Time PCR System",
                "QuantStudio 7",
                "Thermo Fisher Scientific",
                "QuantStudio 7 Flex",
            ),
            (
                "seq",
                "Next-Generation Sequencer",
                "MiSeq viral genomics platform",
                "Illumina",
                "MiSeq",
            ),
        ],
        "researchers": [
            ("lead", "Milica Petrovic", "Principal Investigator",
             "Respiratory virus diagnostics and molecular epidemiology."),
            ("genomics", "Nikola Ilic", "Genomics Specialist",
             "Viral genome assembly and variant surveillance."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Respiratory virus RT-PCR detection",
                "turnaround_days": 2,
                "instruments": ["pcr"],
                "targets": ["SARS-CoV-2", "Influenza A virus", "Human cytomegalovirus"],
                "researchers": {"lead": "lead", "genomics": "contributor"},
            },
            {
                "analysis_type": "Whole Genome Sequencing",
                "public_name": "Viral whole genome sequencing",
                "turnaround_days": 7,
                "instruments": ["seq"],
                "targets": ["SARS-CoV-2", "Influenza A virus"],
                "researchers": {"genomics": "lead"},
            },
        ],
    },
    {
        "key": "chemistry",
        "name": "Center for Analytical Chemistry",
        "slug": "center-for-analytical-chemistry",
        "description": "Analytical chemistry, proteomics and chromatography facility.",
        "address": "Trg Dositeja Obradovica 3",
        "city": "Novi Sad",
        "country": "Serbia",
        "website": "https://example.org/chemistry",
        "contact_email": "laboratory.chemistry@example.org",
        "latitude": 45.2452,
        "longitude": 19.8512,
        "instruments": [
            # Deliberately left unlinked: owning an instrument is not the same as
            # stating that an offering uses it.
            ("pcr", "Real-Time PCR System", "Shared PCR unit", "Bio-Rad", "CFX Opus 96"),
            (
                "ms",
                "Mass Spectrometer",
                "Q Exactive proteomics platform",
                "Thermo Fisher Scientific",
                "Q Exactive Plus",
            ),
            (
                "hplc",
                "High-Performance Liquid Chromatograph",
                "Agilent analytical HPLC",
                "Agilent",
                "1260 Infinity II",
            ),
        ],
        "researchers": [
            ("lead", "Jelena Markovic", "Head of Proteomics",
             "Quantitative proteomics and mass spectrometry method development."),
            ("hplc", "Stefan Djordjevic", "Analytical Chemist",
             "Chromatographic separation of small molecules."),
        ],
        "offerings": [
            {
                "analysis_type": "Proteomics by Mass Spectrometry",
                "public_name": "Quantitative proteomics service",
                "turnaround_days": 10,
                "instruments": ["ms"],
                "researchers": {"lead": "lead"},
            },
            {
                "analysis_type": "HPLC Compound Analysis",
                "public_name": "Small molecule HPLC analysis",
                "turnaround_days": 5,
                "instruments": ["hplc"],
                "researchers": {"hplc": "lead"},
            },
        ],
    },
    {
        "key": "genetics",
        "name": "Institute of Molecular Genetics",
        "slug": "institute-of-molecular-genetics",
        "description": "Molecular diagnostics and high-throughput sequencing facility.",
        "address": "Vojvode Stepe 458",
        "city": "Belgrade",
        "country": "Serbia",
        "website": "https://example.org/genetics",
        "contact_email": "office.genetics@example.org",
        "latitude": 44.8206,
        "longitude": 20.46,
        "instruments": [
            ("pcr", "Real-Time PCR System", "CFX96 diagnostic platform", "Bio-Rad", "CFX96 Touch"),
            (
                "seq",
                "Next-Generation Sequencer",
                "NovaSeq production sequencer",
                "Illumina",
                "NovaSeq 6000",
            ),
        ],
        "researchers": [
            ("lead", "Ana Kovacevic", "Senior Research Associate",
             "Microbial genomics and molecular pathogen detection."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Molecular pathogen detection",
                "turnaround_days": 3,
                "instruments": ["pcr"],
                "targets": ["Human cytomegalovirus", "Candida albicans"],
                "researchers": {"lead": "lead"},
            },
            {
                "analysis_type": "Whole Genome Sequencing",
                "public_name": "Microbial whole genome sequencing",
                "turnaround_days": 12,
                "instruments": ["seq"],
                "targets": ["Escherichia coli", "Listeria monocytogenes", "Candida albicans"],
                "researchers": {"lead": "lead"},
            },
        ],
    },
    {
        "key": "veterinary",
        "name": "Faculty of Veterinary Medicine Core Facility",
        "slug": "veterinary-medicine-core-facility",
        "description": "Shared veterinary diagnostics and cell analysis facility.",
        "address": "Bulevar oslobodjenja 18",
        "city": "Belgrade",
        "country": "Serbia",
        "website": "https://example.org/veterinary",
        "contact_email": "core.veterinary@example.org",
        "latitude": 44.8021,
        "longitude": 20.4869,
        "instruments": [
            (
                "pcr",
                "Real-Time PCR System",
                "LightCycler veterinary diagnostics",
                "Roche",
                "LightCycler 480 II",
            ),
            (
                "flow",
                "Flow Cytometer",
                "CytoFLEX cell analysis system",
                "Beckman Coulter",
                "CytoFLEX S",
            ),
        ],
        "researchers": [
            ("lead", "Marko Stankovic", "Veterinary Diagnostician",
             "Veterinary pathogen panels and immune cell phenotyping."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Veterinary pathogen RT-PCR panel",
                "turnaround_days": 2,
                "instruments": ["pcr"],
                "targets": ["Influenza A virus", "Escherichia coli"],
                "availability": "limited",
                "researchers": {"lead": "contact"},
            },
            {
                "analysis_type": "Flow Cytometry",
                "public_name": "Veterinary immune cell phenotyping",
                "turnaround_days": 4,
                "instruments": ["flow"],
                "researchers": {"lead": "lead"},
            },
        ],
    },
    {
        "key": "environment",
        "name": "Environmental Research Center",
        "slug": "environmental-research-center",
        "description": "Environmental microbiology and contaminant analysis laboratory.",
        "address": "Univerzitetski trg 2",
        "city": "Nis",
        "country": "Serbia",
        "website": "https://example.org/environment",
        "contact_email": "lab.environment@example.org",
        "latitude": 43.3247,
        "longitude": 21.9033,
        "instruments": [
            (
                "hplc",
                "High-Performance Liquid Chromatograph",
                "Prominence environmental HPLC",
                "Shimadzu",
                "Prominence-i LC-2030C",
            ),
            (
                "em",
                "Electron Microscope",
                "JEM microbial imaging platform",
                "JEOL",
                "JEM-1400 Plus",
            ),
        ],
        "researchers": [
            ("lead", "Ivana Nikolic", "Environmental Microbiologist",
             "Environmental contaminants and microbial ultrastructure imaging."),
        ],
        "offerings": [
            {
                "analysis_type": "HPLC Compound Analysis",
                "public_name": "Environmental contaminant analysis",
                "turnaround_days": 6,
                "instruments": ["hplc"],
                "researchers": {"lead": "lead"},
            },
            {
                "analysis_type": "Electron Microscopy",
                "public_name": "Microbial ultrastructure imaging",
                "turnaround_days": 8,
                "instruments": ["em"],
                "targets": ["Escherichia coli", "Listeria monocytogenes"],
                "researchers": {"lead": "lead"},
            },
        ],
    },
    {
        "key": "food",
        "name": "Institute of Food Safety and Quality",
        "slug": "institute-of-food-safety-and-quality",
        "description": "Food microbiology, residue analysis and shelf-life testing.",
        "address": "Bulevar cara Lazara 1",
        "city": "Novi Sad",
        "country": "Serbia",
        "website": "https://example.org/food-safety",
        "contact_email": "office.food@example.org",
        "latitude": 45.2516,
        "longitude": 19.8369,
        "instruments": [
            (
                "pcr",
                "Real-Time PCR System",
                "Food pathogen PCR platform",
                "Thermo Fisher Scientific",
                "QuantStudio 5",
            ),
            (
                "hplc",
                "High-Performance Liquid Chromatograph",
                "Agilent food contaminant HPLC",
                "Agilent",
                "1290 Infinity II",
            ),
            (
                "gc",
                "Gas Chromatograph",
                "Trace residue analyser",
                "Thermo Fisher Scientific",
                "TRACE 1310",
            ),
        ],
        "researchers": [
            ("micro", "Dragana Vukovic", "Head of Food Microbiology",
             "Detection of foodborne pathogens along the production chain."),
            ("residue", "Petar Lazic", "Residue Analyst",
             "Veterinary drug and pesticide residues in food of animal origin."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Foodborne pathogen screening",
                "turnaround_days": 3,
                "instruments": ["pcr"],
                "targets": [
                    "Listeria monocytogenes",
                    "Salmonella enterica",
                    "Campylobacter jejuni",
                ],
                "researchers": {"micro": "lead"},
            },
            {
                "analysis_type": "HPLC Compound Analysis",
                "public_name": "Veterinary drug residue analysis",
                "turnaround_days": 7,
                "instruments": ["hplc", "gc"],
                "researchers": {"residue": "lead", "micro": "contact"},
            },
        ],
    },
    {
        "key": "clinical",
        "name": "Clinical Microbiology Laboratory Vojvodina",
        "slug": "clinical-microbiology-laboratory-vojvodina",
        "description": "Hospital microbiology, molecular diagnostics and resistance monitoring.",
        "address": "Hajduk Veljkova 1",
        "city": "Novi Sad",
        "country": "Serbia",
        "website": "https://example.org/clinical-microbiology",
        "contact_email": "lab.clinical@example.org",
        "latitude": 45.246,
        "longitude": 19.852,
        "instruments": [
            ("pcr", "Real-Time PCR System", "Clinical PCR workstation", "Roche", "LightCycler 96"),
            (
                "extractor",
                "Automated Nucleic Acid Extractor",
                "MagNA Pure extraction robot",
                "Roche",
                "MagNA Pure 24",
            ),
            (
                "reader",
                "Microplate Reader",
                "Multiskan susceptibility reader",
                "Thermo Fisher Scientific",
                "Multiskan SkyHigh",
            ),
        ],
        "researchers": [
            ("clinical", "Jovana Simic", "Clinical Microbiologist",
             "Antimicrobial resistance in hospital-acquired infections."),
            ("molecular", "Bojan Maric", "Molecular Diagnostics Lead",
             "Multiplex molecular panels for respiratory and enteric infections."),
        ],
        "offerings": [
            {
                "analysis_type": "Antimicrobial Susceptibility Testing",
                "public_name": "Clinical isolate susceptibility panel",
                "turnaround_days": 2,
                "instruments": ["reader"],
                "targets": [
                    "Staphylococcus aureus",
                    "Escherichia coli",
                    "Pseudomonas aeruginosa",
                    "Clostridioides difficile",
                ],
                "researchers": {"clinical": "lead"},
            },
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Respiratory panel PCR",
                "turnaround_days": 1,
                "instruments": ["pcr", "extractor"],
                "targets": ["SARS-CoV-2", "Influenza A virus"],
                "researchers": {"molecular": "lead", "clinical": "contributor"},
            },
        ],
    },
    {
        "key": "plants",
        "name": "Institute for Plant Protection",
        "slug": "institute-for-plant-protection",
        "description": "Phytopathology, crop disease diagnostics and host-pathogen imaging.",
        "address": "Banatska 33",
        "city": "Belgrade",
        "country": "Serbia",
        "website": "https://example.org/plant-protection",
        "contact_email": "office.plants@example.org",
        "latitude": 44.843,
        "longitude": 20.4012,
        "instruments": [
            ("pcr", "Real-Time PCR System", "Phytopathogen PCR system", "Bio-Rad", "CFX96 Touch"),
            ("confocal", "Confocal Microscope", "LSM plant imaging platform", "Zeiss", "LSM 900"),
        ],
        "researchers": [
            ("patho", "Nevena Pavlovic", "Plant Pathologist",
             "Bacterial and fungal diseases of field and orchard crops."),
            ("imaging", "Aleksandar Ristic", "Imaging Specialist",
             "Confocal imaging of plant tissue colonisation."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Plant pathogen detection",
                "turnaround_days": 4,
                "instruments": ["pcr"],
                "targets": ["Xanthomonas campestris", "Botrytis cinerea"],
                "researchers": {"patho": "lead"},
            },
            {
                "analysis_type": "Confocal Imaging",
                "public_name": "Host-pathogen interaction imaging",
                "turnaround_days": 10,
                "instruments": ["confocal"],
                "targets": ["Botrytis cinerea"],
                "researchers": {"imaging": "lead", "patho": "contributor"},
            },
        ],
    },
    {
        "key": "imaging",
        "name": "Center for Biomedical Imaging",
        "slug": "center-for-biomedical-imaging",
        "description": "Shared microscopy and cytometry facility for biomedical research.",
        "address": "Svetozara Markovica 69",
        "city": "Kragujevac",
        "country": "Serbia",
        "website": "https://example.org/biomedical-imaging",
        "contact_email": "core.imaging@example.org",
        "latitude": 44.0128,
        "longitude": 20.9114,
        "instruments": [
            (
                "confocal",
                "Confocal Microscope",
                "Stellaris confocal platform",
                "Leica",
                "Stellaris 5",
            ),
            (
                "em",
                "Electron Microscope",
                "Talos transmission microscope",
                "Thermo Fisher Scientific",
                "Talos L120C",
            ),
            (
                "flow",
                "Flow Cytometer",
                "Attune cell analyser",
                "Thermo Fisher Scientific",
                "Attune NxT",
            ),
        ],
        "researchers": [
            ("head", "Tijana Maksimovic", "Head of Imaging",
             "Fluorescence and electron imaging of infected tissue."),
            ("cyto", "Luka Djuric", "Cytometry Specialist",
             "Multicolour panel design for immune phenotyping."),
        ],
        "offerings": [
            {
                "analysis_type": "Confocal Imaging",
                "public_name": "Fluorescence tissue imaging",
                "turnaround_days": 8,
                "instruments": ["confocal"],
                "researchers": {"head": "lead"},
            },
            {
                "analysis_type": "Electron Microscopy",
                "public_name": "Ultrastructural pathology imaging",
                "turnaround_days": 12,
                "instruments": ["em"],
                "targets": ["Aspergillus fumigatus"],
                "researchers": {"head": "contact"},
            },
            {
                "analysis_type": "Flow Cytometry",
                "public_name": "Immune phenotyping panel",
                "turnaround_days": 5,
                "instruments": ["flow"],
                "researchers": {"cyto": "lead"},
            },
        ],
    },
    {
        "key": "water",
        "name": "National Reference Laboratory for Water Microbiology",
        "slug": "national-reference-laboratory-for-water-microbiology",
        "description": "Drinking and recreational water microbiology, reference testing.",
        "address": "Vojvode Tankosica 15",
        "city": "Nis",
        "country": "Serbia",
        "website": "https://example.org/water-microbiology",
        "contact_email": "reference.water@example.org",
        "latitude": 43.318,
        "longitude": 21.896,
        "instruments": [
            ("pcr", "Real-Time PCR System", "Waterborne pathogen PCR", "Bio-Rad", "CFX Opus 96"),
            (
                "extractor",
                "Automated Nucleic Acid Extractor",
                "KingFisher water sample extractor",
                "Thermo Fisher Scientific",
                "KingFisher Flex",
            ),
            # Owned for routine enzymatic testing, which the catalogue does not
            # describe as an analysis type yet.
            (
                "reader",
                "Microplate Reader",
                "Enzymatic water testing reader",
                "BioTek",
                "Synergy LX",
            ),
        ],
        "researchers": [
            ("head", "Milan Tosic", "Water Microbiology Lead",
             "Reference methods for waterborne pathogen detection."),
            ("analyst", "Sanja Ilic", "Laboratory Analyst",
             "Routine sampling and nucleic acid extraction from water matrices."),
        ],
        "offerings": [
            {
                "analysis_type": "Real-Time PCR Detection",
                "public_name": "Waterborne pathogen screening",
                "turnaround_days": 3,
                "instruments": ["pcr", "extractor"],
                "targets": ["Legionella pneumophila", "Escherichia coli", "Campylobacter jejuni"],
                "researchers": {"head": "lead", "analyst": "contributor"},
            },
        ],
    },
    {
        "key": "soil",
        "name": "Institute of Soil Microbiology",
        "slug": "institute-of-soil-microbiology",
        "description": "Soil community ecology, metagenomics and isolate characterisation.",
        "address": "Trg Lazara Neseica 1",
        "city": "Subotica",
        "country": "Serbia",
        "website": "https://example.org/soil-microbiology",
        "contact_email": "office.soil@example.org",
        "latitude": 46.1,
        "longitude": 19.665,
        "instruments": [
            (
                "seq",
                "Next-Generation Sequencer",
                "MiSeq soil community sequencer",
                "Illumina",
                "MiSeq",
            ),
            (
                "extractor",
                "Automated Nucleic Acid Extractor",
                "PowerSoil extraction robot",
                "Qiagen",
                "QIAcube HT",
            ),
        ],
        "researchers": [
            ("ecology", "Vesna Popov", "Soil Ecologist",
             "Microbial community structure under different land use."),
            ("bioinf", "Marko Zivanovic", "Bioinformatician",
             "Metagenomic assembly and taxonomic assignment."),
        ],
        "offerings": [
            {
                "analysis_type": "16S rRNA Community Profiling",
                "public_name": "Soil bacterial community profiling",
                "turnaround_days": 15,
                "instruments": ["seq", "extractor"],
                "targets": ["Pseudomonas aeruginosa"],
                "researchers": {"ecology": "lead", "bioinf": "contributor"},
            },
            {
                "analysis_type": "Whole Genome Sequencing",
                "public_name": "Environmental isolate genome sequencing",
                "turnaround_days": 14,
                "instruments": ["seq"],
                "targets": ["Escherichia coli", "Pseudomonas aeruginosa"],
                "researchers": {"bioinf": "lead"},
            },
        ],
    },
    {
        "key": "pharmacy",
        "name": "Faculty of Pharmacy Analytical Core",
        "slug": "faculty-of-pharmacy-analytical-core",
        "description": "Pharmaceutical analysis, metabolite profiling and assay development.",
        "address": "Vojvode Stepe 450",
        "city": "Belgrade",
        "country": "Serbia",
        "website": "https://example.org/pharmacy-core",
        "contact_email": "core.pharmacy@example.org",
        "latitude": 44.782,
        "longitude": 20.476,
        "instruments": [
            (
                "ms",
                "Mass Spectrometer",
                "Orbitrap metabolite platform",
                "Thermo Fisher Scientific",
                "Orbitrap Exploris 120",
            ),
            (
                "hplc",
                "High-Performance Liquid Chromatograph",
                "Nexera purity HPLC",
                "Shimadzu",
                "Nexera X3",
            ),
            (
                "reader",
                "Microplate Reader",
                "SpectraMax assay reader",
                "Molecular Devices",
                "SpectraMax iD3",
            ),
        ],
        "researchers": [
            ("head", "Katarina Milos", "Head of Analytical Core",
             "Separation science and method validation for medicines."),
            ("ms", "Filip Jovic", "Mass Spectrometry Specialist",
             "Metabolite identification and drug-protein interaction studies."),
            ("assay", "Ana Radic", "Assay Development Scientist",
             "Immunoassay design and validation for serological testing."),
        ],
        "offerings": [
            {
                "analysis_type": "Proteomics by Mass Spectrometry",
                "public_name": "Drug-protein binding proteomics",
                "turnaround_days": 12,
                "instruments": ["ms"],
                "researchers": {"ms": "lead", "head": "contributor"},
            },
            {
                "analysis_type": "HPLC Compound Analysis",
                "public_name": "Pharmaceutical purity analysis",
                "turnaround_days": 6,
                "instruments": ["hplc"],
                "researchers": {"head": "lead"},
            },
            {
                "analysis_type": "ELISA Serology",
                "public_name": "Immunoassay development service",
                "turnaround_days": 9,
                "instruments": ["reader"],
                "targets": ["SARS-CoV-2", "Human cytomegalovirus"],
                "researchers": {"assay": "lead"},
            },
        ],
    },
]


def is_empty(db: Session) -> bool:
    """True when no catalog record exists yet, so a seed cannot collide."""
    return all(db.scalar(select(model.id).limit(1)) is None for model in CATALOG_MODELS)


def _contact(full_name: str) -> str:
    first, _, last = full_name.partition(" ")
    return f"{first[0].lower()}.{last.lower().replace(' ', '')}@example.org"


def reset_catalog(db: Session) -> int:
    """Empty the catalogue, children first. Returns how many rows went."""
    removed = 0
    # Link rows first: the composite foreign keys mean they cannot outlive either
    # side, and deleting them explicitly keeps the order obvious.
    for model in (
        InstitutionAnalysisInstrument,
        InstitutionAnalysisTarget,
        InstitutionAnalysisResearcher,
        InstitutionAnalysis,
        InstitutionInstrument,
        Researcher,
        Institution,
        InstrumentType,
        AnalysisType,
        Microorganism,
    ):
        removed += db.execute(delete(model)).rowcount or 0
    db.flush()
    return removed


def seed_catalog(db: Session) -> str:
    """Populate an empty catalogue and report what happened."""
    if not is_empty(db):
        return "Seed skipped: the catalog already contains data."

    instrument_types = {
        name: InstrumentType(name=name, description=description)
        for name, description in INSTRUMENT_TYPES
    }
    analysis_types = {
        name: AnalysisType(name=name, description=description)
        for name, description in ANALYSIS_TYPES
    }
    microorganisms = {
        scientific: Microorganism(scientific_name=scientific, common_name=common)
        for scientific, common in MICROORGANISMS
    }
    db.add_all(
        [*instrument_types.values(), *analysis_types.values(), *microorganisms.values()]
    )
    db.flush()

    orcid_serial = 0
    counts = {"institutions": 0, "instruments": 0, "researchers": 0, "offerings": 0}

    for spec in INSTITUTIONS:
        institution = Institution(
            name=spec["name"],
            slug=spec["slug"],
            description=spec["description"],
            address=spec["address"],
            city=spec["city"],
            country=spec["country"],
            website=spec["website"],
            contact_email=spec["contact_email"],
            latitude=spec["latitude"],
            longitude=spec["longitude"],
            status="active",
        )
        db.add(institution)
        db.flush()
        counts["institutions"] += 1

        instruments: dict[str, InstitutionInstrument] = {}
        for key, type_name, display_name, manufacturer, model in spec["instruments"]:
            unit = InstitutionInstrument(
                institution_id=institution.id,
                instrument_type_id=instrument_types[type_name].id,
                display_name=display_name,
                manufacturer=manufacturer,
                model=model,
                status="operational",
            )
            db.add(unit)
            db.flush()
            instruments[key] = unit
            counts["instruments"] += 1

        people: dict[str, Researcher] = {}
        for key, full_name, title, expertise in spec["researchers"]:
            orcid_serial += 1
            person = Researcher(
                institution_id=institution.id,
                full_name=full_name,
                title=title,
                email=_contact(full_name),
                orcid=f"0000-0002-{orcid_serial:04d}-0000",
                expertise=expertise,
                status="active",
            )
            db.add(person)
            db.flush()
            people[key] = person
            counts["researchers"] += 1

        for offering_spec in spec["offerings"]:
            offering = InstitutionAnalysis(
                institution_id=institution.id,
                analysis_type_id=analysis_types[offering_spec["analysis_type"]].id,
                public_name=offering_spec["public_name"],
                turnaround_days=offering_spec["turnaround_days"],
                availability=offering_spec.get("availability", "available"),
            )
            db.add(offering)
            db.flush()
            counts["offerings"] += 1

            for key in offering_spec.get("instruments", []):
                link_analysis_instrument(
                    db, institution_analysis=offering, institution_instrument=instruments[key]
                )
            for target in offering_spec.get("targets", []):
                db.add(
                    InstitutionAnalysisTarget(
                        institution_analysis_id=offering.id,
                        microorganism_id=microorganisms[target].id,
                    )
                )
            for key, role in offering_spec.get("researchers", {}).items():
                link_analysis_researcher(
                    db, institution_analysis=offering, researcher=people[key], role=role
                )

    return (
        f"Seed completed: {counts['institutions']} institutions, "
        f"{counts['instruments']} instruments, {counts['researchers']} researchers, "
        f"{counts['offerings']} analysis offerings, "
        f"{len(microorganisms)} microorganisms, "
        f"{len(instrument_types)} instrument types and "
        f"{len(analysis_types)} analysis types."
    )


def seed(*, reset: bool = False) -> str:
    """Seed the configured database. Safe to run on every container start."""
    with SessionLocal.begin() as db:
        notes = []
        if reset:
            notes.append(f"Removed {reset_catalog(db)} existing records.")
        notes.append(seed_catalog(db))
        return "\n".join(notes)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed",
        description="Fill the catalogue with demo data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete everything in the catalogue first, then seed it again.",
    )
    args = parser.parse_args(argv)
    print(seed(reset=args.reset))


if __name__ == "__main__":
    main()
