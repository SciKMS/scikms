"""scikms.kms.config — constants, EBM taxonomy, clinical keywords."""

from __future__ import annotations

from scikms.kms import ATLAS_ROOT


ATLAS_PARQUET = ATLAS_ROOT / "metadata.parquet"
ATLAS_CSV = ATLAS_ROOT / "metadata.csv"
ATLAS_META_COLS = [
    "kms_paper_id", "book_name", "image_path", "thumb_path",
    "page_num", "fig_num", "group_key", "caption", "context",
    "figure_type", "subject_domain", "confidence", "source",
    "saved_at", "bytes_md5", "relevance_score", "notes", "source_document_path",
]

NAV_ITEMS: list[dict] = [
    {"key": "library",  "icon": "library",  "label_key": "nav-library"},
    {"key": "import",   "icon": "import",   "label_key": "nav-import"},
    {"key": "search",   "icon": "search",   "label_key": "nav-search"},
    {"key": "atlas",    "icon": "atlas",    "label_key": "nav-atlas"},
    {"key": "stats",    "icon": "stats",    "label_key": "nav-stats"},
    {"key": "rename",   "icon": "rename",   "label_key": "nav-rename"},
    {"key": "export",   "icon": "export",   "label_key": "nav-export"},
    {"key": "settings", "icon": "settings", "label_key": "nav-settings"},
]
NAV_DEFAULT = "library"

EBM_LEVELS: dict[str, dict] = {
    "I":  {"label_key": "ebm-1", "icon": "🏆", "color": "#064E3B"},
    "II": {"label_key": "ebm-2", "icon": "🔬", "color": "#065F46"},
    "III": {"label_key": "ebm-3", "icon": "👥", "color": "#0F766E"},
    "IV": {"label_key": "ebm-4", "icon": "📊", "color": "#B45309"},
    "V":  {"label_key": "ebm-5", "icon": "📝", "color": "#7C3AED"},
    "":   {"label_key": "ebm-unclassified", "icon": "❓", "color": "#A8A29E"},
}

EVIDENCE_LEVEL_KEYWORDS: dict[str, list[str]] = {
    "I":   ["systematic review", "meta-analysis", "cochrane", "pooled analysis",
            "network meta-analysis", "systematic literature review", "meta-regression"],
    "II":  ["randomized controlled trial", "rct", "randomised controlled trial",
            "randomized trial", "double-blind", "placebo-controlled",
            "single-blind", "crossover trial", "phase 3", "phase iii trial"],
    "III": ["cohort study", "prospective study", "longitudinal study",
            "controlled cohort", "quasi-experimental", "interrupted time series",
            "non-randomized", "propensity score", "before-after study"],
    "IV":  ["case-control", "cross-sectional", "survey", "observational study",
            "retrospective study", "retrospective cohort", "registry study"],
    "V":   ["case series", "case report", "expert opinion", "narrative review",
            "editorial", "letter to editor", "in vitro", "animal study", "preclinical"],
}

STUDY_DESIGN_KEYWORDS: dict[str, list[str]] = {
    "Systematic Review":    ["systematic review", "cochrane review"],
    "Meta-analysis":        ["meta-analysis", "pooled analysis", "meta-regression", "network meta-analysis"],
    "RCT":                  ["randomized controlled trial", "rct", "double-blind", "placebo-controlled"],
    "Prospective Cohort":   ["prospective cohort", "prospective study", "longitudinal study"],
    "Retrospective Cohort": ["retrospective cohort", "retrospective study", "retrospective analysis"],
    "Case-Control":         ["case-control", "case control study", "matched controls"],
    "Cross-sectional":      ["cross-sectional", "prevalence study", "survey"],
    "Case Series":          ["case series", "consecutive cases"],
    "Case Report":          ["case report", "case presentation", "we present a"],
    "Review":               ["narrative review", "literature review", "scoping review"],
}

CLINICAL_SPECIALTIES: list[str] = [
    "Cardiology", "Oncology", "Neurology", "Pulmonology", "Gastroenterology",
    "Endocrinology", "Nephrology", "Rheumatology", "Infectious Disease", "Hematology",
    "Surgery", "Orthopedics", "Pediatrics", "Geriatrics", "Psychiatry", "Dermatology",
    "Radiology", "Pathology", "Anesthesiology", "Emergency Medicine", "Obstetrics",
    "Urology", "Ophthalmology", "ENT", "Pharmacology", "Epidemiology", "Public Health",
    "Basic Science",
]

SPECIALTY_KEYWORDS: dict[str, list[str]] = {
    "Cardiology":         ["cardiac", "heart", "coronary", "myocardial", "arrhythmia", "ecg", "hypertension"],
    "Oncology":           ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "chemotherapy"],
    "Neurology":          ["brain", "stroke", "dementia", "alzheimer", "parkinson", "epilepsy", "neural"],
    "Pulmonology":        ["lung", "pulmonary", "copd", "asthma", "respiratory", "pneumonia"],
    "Gastroenterology":   ["gastric", "intestinal", "colon", "liver", "hepatic", "ibd", "crohn"],
    "Endocrinology":      ["diabetes", "insulin", "thyroid", "hormone", "metabolic", "obesity"],
    "Nephrology":         ["kidney", "renal", "dialysis", "creatinine", "nephropathy"],
    "Surgery":            ["surgical", "operation", "postoperative", "laparoscopic", "resection"],
    "Pediatrics":         ["children", "pediatric", "neonatal", "infant", "adolescent"],
    "Infectious Disease": ["infection", "bacteria", "virus", "antibiotic", "sepsis", "covid", "hiv"],
    "Psychiatry":         ["depression", "anxiety", "schizophrenia", "bipolar", "psychiatric"],
    "Radiology":          ["mri", "ct scan", "imaging", "radiograph", "ultrasound", "pet"],
    "Pharmacology":       ["pharmacokinetics", "drug", "dose", "pharmacodynamics", "bioavailability"],
    "Epidemiology":       ["prevalence", "incidence", "epidemiology", "population-based"],
}

FIGURE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "graph":            ["graph", "plot", "scatter", "line plot", "curve", "regression", "kaplan-meier",
                         "survival curve", "forest plot", "funnel plot", "roc curve", "auc", "hazard ratio"],
    "bar_chart":        ["bar chart", "bar graph", "histogram", "frequency distribution", "stacked bar"],
    "table":            ["table", "baseline characteristics", "demographic", "multivariate", "odds ratio",
                         "relative risk", "confidence interval", "p-value", "regression table"],
    "diagram":          ["diagram", "schematic", "flowchart", "workflow", "pathway", "mechanism",
                         "consort", "prisma", "flow diagram"],
    "microscopy":       ["microscopy", "histology", "h&e", "immunohistochemistry", "ihc",
                         "immunofluorescence", "confocal", "electron microscopy", "\u00d7", "\u03bcm"],
    "radiology":        ["mri", "ct scan", "x-ray", "radiograph", "ultrasound", "echo",
                         "pet scan", "fmri", "sagittal", "coronal", "axial", "t1", "t2"],
    "photo_clinical":   ["photograph", "photo", "clinical image", "preoperative", "postoperative",
                         "intraoperative", "surgical", "wound", "lesion"],
    "chart_other":      ["pie chart", "heatmap", "box plot", "violin plot", "waterfall", "sankey"],
    "illustration":     ["illustration", "drawing", "anatomy", "anatomical", "cross-section", "3d model"],
    "gel_blot":         ["gel", "western blot", "pcr", "electrophoresis", "sds-page", "agarose", "band"],
    "equation_formula": ["equation", "formula", "mathematical", "calculation", "derivation"],
    "map_geographic":   ["map", "geographic", "gis", "region", "distribution map", "choropleth"],
}

SUBJECT_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "medicine_clinical": ["patient", "clinical trial", "randomized", "treatment", "therapy",
                          "diagnosis", "surgery", "drug", "cohort", "meta-analysis"],
    "cardiology":        ["cardiac", "heart", "coronary", "myocardial", "ecg", "hypertension"],
    "oncology":          ["cancer", "tumor", "carcinoma", "chemotherapy", "metastasis", "survival"],
    "neurology":         ["brain", "neural", "neuron", "cortex", "stroke", "dementia", "mri", "fmri"],
    "biology_basic":     ["cell", "gene", "protein", "dna", "rna", "pcr", "blot", "molecular"],
    "engineering_tech":  ["algorithm", "network", "system", "model", "simulation",
                          "machine learning", "deep learning", "computer vision"],
    "epidemiology":      ["prevalence", "incidence", "mortality", "population", "cohort", "public health"],
    "pharmacology":      ["drug", "pharmacokinetics", "pharmacodynamics", "dose", "bioavailability"],
}

DEFAULT_TAGS: list[str] = [
    "Randomized Controlled Trial", "Meta-analysis", "Systematic Review", "Cohort Study",
    "Case-Control", "Cross-sectional", "Observational", "Prospective", "Retrospective",
    "Pilot Study", "Phase II", "Phase III", "Multivariate Analysis", "Regression",
    "ROC Curve", "Kaplan-Meier", "Confidence Interval", "Sample Size", "Bias", "Propensity Score",
    "Deep Learning", "Machine Learning", "Neural Network", "Artificial Intelligence", "NLP",
    "Diagnosis", "Biomarker", "Prognosis", "Treatment Outcome", "Drug Therapy",
    "Surgical Technique", "Complication", "Patient Reported Outcome", "Quality of Life",
    "Oncology", "Cardiology", "Neurology", "Diabetes Mellitus", "Hypertension",
    "COPD", "Stroke", "Sepsis", "Pediatrics", "Psychiatry",
    "MRI", "CT Scan", "Ultrasound", "PET Scan", "Histology",
    "Immunohistochemistry", "Pathology", "Radiology",
    "CRISPR", "Gene Therapy", "Stem Cell", "Immunotherapy",
    "Survival Analysis", "Overall Survival", "Progression-Free Survival",
    "PRISMA", "CONSORT", "STROBE", "Open Access",
]
DEFAULT_TAG_DICT = DEFAULT_TAGS

SEARCH_TEMPLATES: list[tuple[str, str]] = [
    ("RCT hypertension",        "randomized controlled trial hypertension"),
    ("Meta-analysis DM",        "meta-analysis diabetes mellitus"),
    ("Kaplan-Meier cancer",     "kaplan-meier survival cancer"),
    ("Forest plot",             "forest plot meta-analysis"),
    ("Propensity score",        "propensity score matching"),
    ("Deep learning radiology", "deep learning radiology imaging"),
    ("Systematic review COPD",  "systematic review COPD treatment"),
    ("ROC curve biomarker",     "ROC curve diagnostic biomarker"),
]

SORT_OPTIONS = [
    "Recently added",
    "Year (newest)",
    "Year (oldest)",
    "Title A→Z",
    "Authors A→Z",
    "Evidence Level",
    "Most pages",
    "Impact Factor",
]
