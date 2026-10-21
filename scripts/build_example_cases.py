"""Generate examples/synthetic_cases.json.

Everything here is SYNTHETIC. Patients, claims, member IDs, policies and clinicians are
invented; the policies are written for testing and are NOT real Medicare (NCD/LCD) or payer
text. Cases are assembled from templates so the dataset is reproducible, and each case ships a
"good" reference draft and a "flawed" one with exactly the seeded flaws listed.

Run:  python scripts/build_example_cases.py > examples/synthetic_cases.json
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta

CPT = "{cpt}"
NPI = "NPI SYN-0000 (synthetic)"
REQUEST = "We request that the denial be overturned and the service authorized."
GENERIC = (
    "We believe this service is medically appropriate for our patient and ask the plan "
    "to review the request promptly."
)

# (name, dob, provider, title, cpt, icd, policy_title, criteria, unmet, code,
#  reason_text, reason_terms, facts[(date,text)], response_core, flaw)
# unmet is a 1-based criterion index, or a list of them when the plan names several.
S = [
    (
        "Dana Testwell",
        "1968-03-14",
        "Dr. Lee Placeholder",
        "Lumbar spine MRI",
        "72148",
        "M54.16",
        "Advanced imaging of the lumbar spine (synthetic)",
        [
            "Radicular low back pain lasting at least 6 weeks",
            "At least 6 weeks of documented conservative therapy (physical therapy or supervised "
            "exercise, plus medication)",
            "Neurological deficit, red-flag finding, or planned intervention",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: conservative therapy not documented",
        ["physical therapy", "6 weeks"],
        [
            ("2026-01-05", "Low back pain radiating to the left leg, onset 2025-11-20."),
            ("2026-01-05", "Straight leg raise positive on the left at 40 degrees."),
            ("2026-01-12", "Started physical therapy, 2 sessions per week."),
            (
                "2026-02-23",
                "Completed 6 weeks of physical therapy (12 sessions); pain remains 7/10.",
            ),
            ("2026-02-23", "Naproxen 500 mg twice daily for 6 weeks without relief."),
            ("2026-02-23", "Mild left ankle dorsiflexion weakness, 4/5."),
        ],
        "the chart documents 6 weeks of physical therapy (12 sessions) and 6 weeks of naproxen "
        "without relief",
        {"kind": "citation_invented"},
    ),
    (
        "Riley Mockson",
        "1959-07-22",
        "Dr. Avery Specimen",
        "Attended sleep study",
        "95810",
        "G47.30",
        "Attended polysomnography (synthetic)",
        [
            "Clinical suspicion of obstructive sleep apnea documented with a validated "
            "screening score",
            "Home sleep apnea testing is contraindicated or was technically inadequate",
            "Significant cardiopulmonary or neuromuscular comorbidity",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: home sleep testing not shown to be inadequate",
        ["home sleep", "inadequate"],
        [
            ("2026-01-10", "Excessive daytime sleepiness; Epworth score 14."),
            ("2026-01-10", "STOP-BANG score 6."),
            (
                "2026-02-02",
                "Home sleep apnea test attempted; recording was technically inadequate "
                "(under 4 hours of usable signal).",
            ),
            ("2026-02-02", "Heart failure with reduced ejection fraction, EF 35%."),
        ],
        "the home sleep apnea test on 2026-02-02 was technically inadequate, and the patient has "
        "heart failure",
        {"kind": "citation_wrong_policy"},
    ),
    (
        "Jordan Sample",
        "1955-11-03",
        "Dr. Kim Fictional",
        "Total knee replacement",
        "27447",
        "M17.11",
        "Total knee arthroplasty (synthetic)",
        [
            "Radiographic advanced osteoarthritis (Kellgren-Lawrence grade 3 or 4)",
            "At least 3 months of documented non-operative treatment",
            "Functional limitation affecting daily activities",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: non-operative treatment duration not documented",
        ["non-operative", "3 months"],
        [
            (
                "2025-11-04",
                "Right knee pain with walking; X-ray shows Kellgren-Lawrence grade 4 "
                "osteoarthritis.",
            ),
            (
                "2025-11-04",
                "Unable to climb stairs without a handrail; walking limited to one block.",
            ),
            ("2025-11-18", "Started weight-bearing exercise program and acetaminophen."),
            (
                "2026-02-10",
                "Intra-articular corticosteroid injection given 2025-12-15 with relief "
                "lasting 2 weeks.",
            ),
            (
                "2026-02-10",
                "Completed 12 weeks of non-operative treatment including exercise, bracing "
                "and one injection.",
            ),
        ],
        "the patient completed 12 weeks (more than 3 months) of non-operative treatment",
        {
            "kind": "fact_numeric",
            "bullet": "Completed 26 weeks of supervised physical therapy (2026-02-10).",
        },
    ),
    (
        "Casey Fakename",
        "1972-05-30",
        "Dr. Pat Demo",
        "Lumbar epidural steroid injection",
        "64483",
        "M51.16",
        "Lumbar transforaminal epidural injection (synthetic)",
        [
            "Radicular pain for at least 4 weeks with imaging or exam correlation",
            "Pain of at least 4/10 with functional impairment",
            "No contraindication such as anticoagulation or active infection",
        ],
        3,
        "SYN-D02",
        "Documentation insufficient: absence of contraindications not documented",
        ["anticoagulants", "infection"],
        [
            (
                "2026-01-20",
                "Right leg radicular pain for 8 weeks; MRI shows L5-S1 disc protrusion "
                "contacting the right S1 root.",
            ),
            ("2026-01-20", "Pain 8/10; unable to sit longer than 15 minutes."),
            (
                "2026-02-03",
                "Not on anticoagulants or antiplatelet agents; no signs of infection; afebrile.",
            ),
            ("2026-02-03", "Platelet count 240 and INR 1.0."),
        ],
        "the chart documents that the patient takes no anticoagulants and has no signs of "
        "infection (INR 1.0)",
        {
            "kind": "fact_nonnumeric",
            "bullet": "Documented history of prior lumbar surgery with retained hardware "
            "(2026-02-03).",
        },
    ),
    (
        "Morgan Demo",
        "1963-09-09",
        "Dr. Sam Notreal",
        "Myocardial perfusion imaging",
        "78452",
        "R07.9",
        "Myocardial perfusion SPECT (synthetic)",
        [
            "Intermediate or high pretest probability of coronary disease",
            "Resting ECG uninterpretable or patient unable to exercise adequately",
            "Prior non-invasive testing non-diagnostic",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: stress imaging rationale not documented",
        ["unable to exercise", "ECG"],
        [
            (
                "2026-02-12",
                "Exertional chest pressure for 3 weeks; 62-year-old with hypertension and "
                "diabetes.",
            ),
            ("2026-02-12", "Resting ECG shows left bundle branch block."),
            (
                "2026-02-12",
                "Unable to complete treadmill exercise: severe knee osteoarthritis limits "
                "walking to 2 minutes.",
            ),
            ("2026-02-12", "Estimated pretest probability of coronary disease: intermediate."),
        ],
        "the resting ECG shows left bundle branch block and the patient is unable to exercise "
        "adequately because of knee osteoarthritis",
        {"kind": "reason_unaddressed"},
    ),
    (
        "Taylor Placeholder",
        "1971-02-17",
        "Dr. Robin Dummy",
        "Brain MRI after first seizure",
        "70553",
        "R56.9",
        "Brain MRI with and without contrast (synthetic)",
        [
            "New-onset seizure with focal features or abnormal neurological exam",
            "Prior CT or EEG non-diagnostic or insufficient for the clinical question",
            "Age over 40 with new-onset seizure, or known malignancy",
        ],
        1,
        "SYN-D01",
        "Not medically necessary: focal features not documented",
        ["focal", "neurological exam"],
        [
            (
                "2026-02-18",
                "First seizure 2026-02-17: witnessed left arm jerking lasting about 2 minutes.",
            ),
            ("2026-02-18", "Neurological exam: mild left facial droop."),
            ("2026-02-18", "Head CT without contrast read as no acute abnormality."),
            ("2026-02-18", "Age 54."),
        ],
        "the seizure had focal features (left arm jerking) and the neurological exam is abnormal "
        "(left facial droop)",
        {"kind": "criterion_not_cited"},
    ),
    (
        "Alex Notreal",
        "1950-12-01",
        "Dr. Jamie Specimen",
        "Follow-up chest CT",
        "71250",
        "R91.1",
        "Chest CT for pulmonary nodule follow-up (synthetic)",
        [
            "Solitary pulmonary nodule of 6 mm or larger on prior imaging",
            "Follow-up interval consistent with accepted guidance for nodule size and risk",
            "Risk factors documented (smoking history, prior malignancy)",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: follow-up interval not supported",
        ["interval", "guideline"],
        [
            ("2025-08-14", "Chest X-ray: 8 mm nodule in the right upper lobe."),
            ("2025-08-14", "Former smoker, 30 pack-years."),
            ("2026-02-20", "Follow-up CT is due 6 months after the 2025-08-14 finding."),
        ],
        "a 6 month follow-up interval fits guideline-based surveillance for an 8 mm nodule in a "
        "former heavy smoker",
        {"kind": "wrong_member"},
    ),
    (
        "Jamie Dummy",
        "1966-04-25",
        "Dr. Casey Mockdoc",
        "Diagnostic colonoscopy",
        "45378",
        "K62.5",
        "Diagnostic colonoscopy (synthetic)",
        [
            "Rectal bleeding persisting over 2 weeks, or bleeding with anemia",
            "Age 45 or older, or alarm features",
            "No colonoscopy in the past 10 years unless newly indicated",
        ],
        1,
        "SYN-D02",
        "Documentation insufficient: bleeding duration and anemia not documented",
        ["bleeding", "anemia"],
        [
            ("2026-01-27", "Bright red rectal bleeding for 5 weeks."),
            ("2026-01-27", "Hemoglobin 10.2 g/dL, consistent with iron-deficiency anemia."),
            ("2026-01-27", "Age 51; no prior colonoscopy."),
        ],
        "the chart documents 5 weeks of rectal bleeding with iron-deficiency anemia",
        {"kind": "wrong_cpt", "to": "45380"},
    ),
    (
        "Sam Fictional",
        "1948-08-19",
        "Dr. Alex Testdoc",
        "Transthoracic echocardiogram",
        "93306",
        "I50.9",
        "Complete echocardiography (synthetic)",
        [
            "New or worsening heart failure symptoms",
            "No echocardiogram in the prior 12 months unless there is a clinical change",
            "Result expected to change management",
        ],
        2,
        "SYN-D02",
        "Documentation insufficient: change since prior echocardiogram not shown",
        ["clinical change", "prior echocardiogram"],
        [
            ("2026-02-05", "Prior echocardiogram 2025-03-04 showed EF 45%."),
            ("2026-02-05", "New orthopnea and 6 kg weight gain over 2 weeks."),
            ("2026-02-05", "BNP 980 pg/mL."),
            ("2026-02-05", "Diuretic dose increased; further medication changes depend on EF."),
        ],
        "there has been a clinical change since the prior echocardiogram of 2025-03-04: new "
        "orthopnea and 6 kg weight gain",
        {"kind": "missing_elements"},
    ),
    (
        "Robin Specimen",
        "1980-10-12",
        "Dr. Morgan Placeholder",
        "Knee arthroscopy",
        "29881",
        "M23.221",
        "Knee arthroscopy with meniscectomy (synthetic)",
        [
            "Mechanical symptoms (locking or catching) documented",
            "MRI confirming a meniscal tear",
            "Failure of at least 6 weeks of non-operative treatment",
        ],
        3,
        "SYN-D01",
        "Not medically necessary: non-operative treatment failure not documented",
        ["6 weeks", "non-operative"],
        [
            ("2026-01-08", "Right knee locking and catching for 10 weeks."),
            (
                "2026-01-08",
                "MRI 2026-01-06 shows complex tear of the posterior horn of the medial meniscus.",
            ),
            (
                "2026-02-26",
                "Completed 6 weeks of non-operative treatment with physical therapy; "
                "locking episodes persist.",
            ),
        ],
        "the patient completed 6 weeks of non-operative treatment with physical therapy and the "
        "locking episodes persist",
        {"kind": "late_and_incomplete", "icd": "M23.222"},
    ),
    (
        "Pat Testwell",
        "1975-06-08",
        "Dr. Quinn Specimen",
        "Left shoulder MRI",
        "73221",
        "M75.41",
        "Shoulder MRI without contrast (synthetic)",
        [
            "Shoulder pain lasting at least 6 weeks with functional limitation",
            "Failed or incomplete response to at least 6 weeks of conservative care",
            "No contraindication to MRI (no incompatible implanted device)",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: conservative care failure not documented",
        ["conservative", "6 weeks"],
        [
            ("2026-01-15", "Left shoulder pain for 10 weeks; unable to reach overhead."),
            ("2026-01-15", "Not on anticoagulants; no implanted cardiac device."),
            ("2026-02-28", "Completed 6 weeks of physical therapy without meaningful improvement."),
            ("2026-02-28", "Continued naproxen; pain remains 6/10."),
        ],
        "the chart documents 6 weeks of physical therapy without meaningful improvement",
        {
            "kind": "negation_flip",
            "bullet": "Currently on anticoagulants and has an implanted cardiac device "
            "(2026-01-15).",
        },
    ),
    (
        "Chris Mockson",
        "1961-01-29",
        "Dr. Drew Placeholder",
        "Outpatient cardiac rehab",
        "93798",
        "I25.10",
        "Cardiac rehabilitation (synthetic)",
        [
            "Recent qualifying cardiac event or procedure within 12 months",
            "Cleared by cardiology for supervised exercise",
            "Documented need for monitoring during exercise",
        ],
        1,
        "SYN-D01",
        "Not medically necessary: qualifying cardiac event not documented",
        ["cardiac event", "12 months"],
        [
            ("2026-01-08", "STEMI treated with PCI to the LAD on 2025-12-20."),
            ("2026-01-08", "Cleared by cardiology for Phase II cardiac rehab."),
            ("2026-01-08", "Exertional dyspnea; needs ECG-monitored exercise."),
        ],
        "the patient had a STEMI treated with PCI on 2025-12-20, within 12 months",
        {"kind": "near_miss_member"},
    ),
    (
        "Leslie Sample",
        "1957-09-14",
        "Dr. Blair Fictional",
        "Upper endoscopy",
        "43239",
        "K21.0",
        "Esophagogastroduodenoscopy (synthetic)",
        [
            "Alarm features (dysphagia, bleeding, or iron-deficiency anemia) or refractory reflux",
            "Age 50 or older, or prior Barrett surveillance indication",
            "No EGD in the prior 3 years unless newly indicated",
        ],
        1,
        "SYN-D02",
        "Documentation insufficient: alarm features not documented",
        ["dysphagia", "anemia"],
        [
            ("2026-02-01", "Progressive dysphagia to solids for 6 weeks."),
            ("2026-02-01", "Hemoglobin 9.8 g/dL with iron-deficiency anemia."),
            ("2026-02-01", "Age 68; last EGD was 2019."),
        ],
        "the chart documents progressive dysphagia and iron-deficiency anemia",
        {"kind": "near_miss_cpt", "to": "43240"},
    ),
    (
        "Shannon Fakename",
        "1969-12-21",
        "Dr. Cameron Demo",
        "Cervical spine MRI",
        "72141",
        "M54.12",
        "Cervical spine MRI without contrast (synthetic)",
        [
            "Neck pain with radicular symptoms for at least 6 weeks",
            "Neurological deficit or progressive symptoms",
            "Inadequate response to conservative therapy",
        ],
        3,
        "SYN-D01",
        "Not medically necessary: conservative therapy response not shown",
        ["conservative", "inadequate"],
        [
            (
                "2026-01-11",
                "Right arm radicular pain for 8 weeks; neck pain radiating to digits 1-2.",
            ),
            ("2026-01-11", "Right biceps reflex diminished; mild wrist extension weakness 4/5."),
            (
                "2026-02-24",
                "Completed 6 weeks of physical therapy with inadequate response; pain still 7/10.",
            ),
        ],
        "the patient completed 6 weeks of physical therapy with an inadequate response",
        {"kind": "swapped_icd", "to": "M54.13"},
    ),
    (
        "Drew Notreal",
        "1954-04-02",
        "Dr. Harper Testdoc",
        "Home oxygen evaluation",
        "94760",
        "J44.1",
        "Pulse oximetry for home oxygen (synthetic)",
        [
            "Chronic lung disease with recent exacerbation or resting desaturation",
            "Resting SpO2 of 88 percent or lower, or exertional desaturation",
            "Optimized medical therapy documented",
        ],
        2,
        "SYN-D02",
        "Documentation insufficient: qualifying saturation values not shown",
        ["SpO2", "88"],
        [
            ("2026-02-10", "COPD with recent exacerbation requiring steroids."),
            ("2026-02-10", "Resting SpO2 86 percent on room air."),
            ("2026-02-10", "On optimized inhaler therapy including LABA/LAMA."),
            ("2026-02-10", "Walks 20 meters before stopping for dyspnea."),
        ],
        "resting SpO2 is 86 percent on room air, below the 88 percent threshold",
        {
            "kind": "paraphrase_flip",
            "bullet": "Resting SpO2 improved to 96 percent on room air after the recent "
            "exacerbation (2026-02-10).",
        },
    ),
    (
        "Avery Testcase",
        "1977-03-03",
        "Dr. Reese Placeholder",
        "Right hip MRI",
        "73721",
        "M25.551",
        "MRI of the hip without contrast (synthetic)",
        [
            "Hip pain for at least 6 weeks with limited range of motion",
            "Plain radiographs obtained and non-diagnostic",
            "At least 6 weeks of conservative therapy",
        ],
        2,
        "SYN-D02",
        "Documentation insufficient: plain radiograph result not documented",
        ["radiographs", "non-diagnostic"],
        [
            ("2026-01-19", "Right hip pain for 9 weeks; internal rotation limited and painful."),
            ("2026-01-19", "Plain radiographs of the right hip were non-diagnostic."),
            ("2026-02-27", "Completed 6 weeks of physical therapy; pain remains 6/10."),
        ],
        "plain radiographs of the right hip on 2026-01-19 were non-diagnostic",
        {"kind": "citation_bad_criterion"},
    ),
    (
        "Quinn Mockdata",
        "1964-06-17",
        "Dr. Ellis Specimen",
        "Spirometry",
        "94010",
        "R06.02",
        "Spirometry for unexplained dyspnea (synthetic)",
        [
            "Unexplained dyspnea or chronic cough for at least 8 weeks",
            "Exam and chest imaging do not explain the symptoms",
            "Result expected to guide treatment",
        ],
        1,
        "SYN-D01",
        "Not medically necessary: symptom duration not documented",
        ["dyspnea", "8 weeks"],
        [
            ("2026-01-22", "Exertional dyspnea and dry cough for 12 weeks."),
            ("2026-01-22", "Chest X-ray clear; cardiac exam normal."),
            ("2026-01-22", "Inhaler choice depends on the spirometry result."),
        ],
        "the chart documents exertional dyspnea and cough for 12 weeks, longer than 8 weeks",
        {"kind": "wrong_patient_name", "to": "Riley Mockson"},
    ),
    (
        "Jesse Samplecase",
        "1958-10-30",
        "Dr. Rowan Fictional",
        "Carotid duplex ultrasound",
        "93880",
        "G45.9",
        "Carotid duplex ultrasound (synthetic)",
        [
            "Focal neurological symptoms suggesting TIA or stroke",
            "Carotid bruit or symptoms in a carotid territory",
            "Patient is a candidate for intervention if stenosis is found",
        ],
        1,
        "SYN-D01",
        "Not medically necessary: focal neurological symptoms not documented",
        ["focal", "transient"],
        [
            (
                "2026-02-09",
                "Transient right hand weakness and slurred speech lasting 20 minutes on "
                "2026-02-08.",
            ),
            ("2026-02-09", "Left carotid bruit on exam."),
            ("2026-02-09", "Fit for carotid intervention if significant stenosis is found."),
        ],
        "the patient had a transient focal episode of right hand weakness and slurred speech on "
        "2026-02-08",
        {
            "kind": "date_shift",
            "bullet": "Earlier transient episode of right hand weakness (2026-01-25).",
        },
    ),
    (
        "Morgan Testrecord",
        "1973-08-11",
        "Dr. Sky Mockdoc",
        "Bone density scan",
        "77080",
        "M81.0",
        "Dual-energy X-ray absorptiometry (synthetic)",
        [
            "Age 65 or older, or a risk factor such as long-term glucocorticoid use",
            "No DXA in the prior 2 years unless newly indicated",
            "Result expected to change management",
        ],
        1,
        "SYN-D02",
        "Documentation insufficient: glucocorticoid exposure not documented",
        ["glucocorticoid", "prednisone"],
        [
            ("2026-01-30", "Prednisone 10 mg daily for 7 months for polymyalgia rheumatica."),
            ("2026-01-30", "No prior DXA."),
            ("2026-01-30", "Bisphosphonate decision depends on the DXA result."),
        ],
        "the patient has taken prednisone 10 mg daily for 7 months, which is long-term "
        "glucocorticoid use",
        {"kind": "reason_terms_missing"},
    ),
    (
        "Harper Notacase",
        "1966-02-14",
        "Dr. Logan Testdoc",
        "Lower extremity venous duplex",
        "93970",
        "I87.2",
        "Venous duplex for chronic venous disease (synthetic)",
        [
            "Symptomatic varicose veins or venous insufficiency",
            "At least 3 months of compression therapy",
            "Intervention is being considered",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: compression therapy not documented",
        ["compression", "3 months"],
        [
            ("2025-11-03", "Aching and swelling of both legs with visible varicose veins."),
            (
                "2026-02-12",
                "Wore prescribed compression stockings daily for 3 months without relief.",
            ),
            ("2026-02-12", "Referred to vascular surgery to consider ablation."),
        ],
        "the patient wore compression stockings daily for 3 months without relief",
        {"kind": "late_filing"},
    ),
    (
        "Tess Mockwell",
        "1952-06-08",
        "Dr. Rowan Placeholder",
        "Cataract surgery, right eye",
        "66984",
        "H25.11",
        "Cataract extraction with lens implant (synthetic)",
        [
            "Best-corrected visual acuity of 20/50 or worse in the operative eye",
            "Cataract-related functional impairment affecting daily activities such as driving or "
            "reading",
            "Ocular exam attributes the visual loss to the cataract",
        ],
        [1, 2],
        "SYN-D02",
        "Documentation insufficient: visual acuity and functional impairment not documented",
        ["visual acuity", "20/70", "driving", "read"],
        [
            ("2026-01-14", "Best-corrected visual acuity 20/70 in the right eye."),
            (
                "2026-01-14",
                "Stopped driving at night because of glare; unable to read medication labels.",
            ),
            (
                "2026-01-14",
                "Slit-lamp exam: dense nuclear cataract in the right eye; retina normal.",
            ),
            (
                "2026-02-02",
                "Glare testing: best-corrected visual acuity drops to 20/200 in the right eye.",
            ),
        ],
        "best-corrected visual acuity is 20/70 in the right eye, and the patient stopped "
        "driving at "
        "night and is unable to read medication labels",
        {
            "kind": "multiple_unmet",
            "partial": "best-corrected visual acuity is 20/70 in the right eye",
        },
    ),
    (
        "Lane Fictionalis",
        "1961-10-27",
        "Dr. Quinn Testdoc",
        "PET/CT for lymphoma restaging",
        "78815",
        "C83.30",
        "FDG PET/CT for oncologic restaging (synthetic)",
        [
            "Biopsy-proven malignancy for which PET is an accepted imaging modality",
            "Completed a planned course of therapy and restaging will guide further management",
            "No PET for the same indication in the prior 90 days",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: completion of therapy not documented",
        ["completed", "chemotherapy"],
        [
            ("2025-09-02", "Excisional lymph node biopsy: diffuse large B-cell lymphoma."),
            ("2026-02-11", "Completed 6 cycles of R-CHOP chemotherapy on 2026-02-04."),
            (
                "2026-02-11",
                "Hematology plans end-of-treatment PET/CT to decide on consolidation radiotherapy.",
            ),
            ("2026-02-11", "Last PET/CT 2025-09-15 at diagnosis."),
        ],
        "the patient completed 6 cycles of R-CHOP chemotherapy on 2026-02-04, and restaging will "
        "decide on consolidation radiotherapy",
        {"kind": "citation_real_looking_ncd", "cite": "NCD 220.6.17"},
    ),
    (
        "Kit Specimen",
        "1990-01-19",
        "Dr. Morgan Mockdoc",
        "Allergen immunotherapy",
        "95165",
        "J30.2",
        "Subcutaneous allergen immunotherapy (synthetic)",
        [
            "Allergic rhinitis with sensitization confirmed by skin or serum testing",
            "Symptoms persist despite an adequate trial of avoidance and medication",
            "No uncontrolled asthma",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: failure of medication trial not documented",
        ["nasal steroid", "antihistamine"],
        [
            (
                "2025-10-06",
                "Seasonal allergic rhinitis; skin prick test positive to grass and ragweed pollen.",
            ),
            (
                "2026-01-26",
                "Daily nasal steroid and oral antihistamine for 2 seasons with persistent "
                "symptoms.",
            ),
            ("2026-01-26", "Asthma well controlled; spirometry normal."),
        ],
        "the patient used a daily nasal steroid and oral antihistamine for 2 seasons with "
        "persistent symptoms",
        # 900-xx-xxxx is outside the range ever issued as an SSN.
        {"kind": "extra_phi_ssn", "ssn": "900-00-0023"},
    ),
    (
        "Ellis Notreal",
        "1958-12-03",
        "Dr. Jordan Fakedoc",
        "Negative pressure wound therapy",
        "97605",
        "L97.412",
        "Negative pressure wound therapy (synthetic)",
        [
            "Chronic wound present at least 30 days despite standard wound care",
            "Wound measurements documented at baseline and follow-up",
            "Underlying cause addressed (offloading, glucose control, or perfusion assessed)",
        ],
        2,
        "SYN-D02",
        "Documentation insufficient: wound measurements not documented",
        ["measurements", "cm"],
        [
            (
                "2026-01-08",
                "Right heel diabetic foot ulcer present since 2025-11-25; daily moist dressings.",
            ),
            ("2026-01-08", "Wound 3.2 cm x 2.1 cm x 0.6 cm at baseline."),
            ("2026-02-05", "Wound 3.0 cm x 2.0 cm x 0.6 cm after 4 weeks of standard care."),
            ("2026-02-05", "Offloading boot in use; HbA1c 7.4%; ankle-brachial index 0.95."),
        ],
        "wound measurements are documented at baseline (3.2 cm x 2.1 cm) and after 4 weeks of "
        "standard care (3.0 cm x 2.0 cm)",
        {"kind": "near_miss_claim"},
    ),
    (
        "Robin Mockrecord",
        "1969-05-12",
        "Dr. Taylor Specimen",
        "CPAP titration study",
        "95811",
        "G47.33",
        "Attended CPAP titration polysomnography (synthetic)",
        [
            "Obstructive sleep apnea diagnosed by a prior sleep study",
            "Auto-titrating CPAP failed or is not appropriate",
            "Titration result is expected to set the treatment pressure",
        ],
        2,
        "SYN-D01",
        "Not medically necessary: auto-titrating CPAP trial not documented",
        ["auto-titrating", "failed"],
        [
            (
                "2025-12-01",
                "Home sleep apnea test: AHI 38 events per hour, consistent with severe "
                "obstructive sleep apnea.",
            ),
            (
                "2026-01-15",
                "Auto-titrating CPAP for 30 days failed: persistent AHI 22 and "
                "pressure-intolerance awakenings.",
            ),
            ("2026-01-15", "Fixed-pressure CPAP will be set from the attended titration result."),
        ],
        "a 30 day trial of auto-titrating CPAP failed with a persistent AHI of 22",
        {"kind": "missing_overturn_request"},
    ),
]


def pid(n: int) -> str:
    return f"SYN-LCD-{1000 + n}"


def policy(i: int) -> dict:
    s = S[i]
    return {
        "id": pid(i + 1),
        "title": s[6],
        "criteria": [{"id": f"{pid(i + 1)}-C{k + 1}", "text": t} for k, t in enumerate(s[7])],
    }


def render(
    c: dict,
    *,
    date_s,
    response,
    bullets,
    policy_ref,
    crit_ids,
    request,
    enclosures,
    signature,
    patient_name,
    member,
    claim,
    cpt,
    icd,
    header_extra="",
) -> str:
    out = [
        f"Date: {date_s}",
        f"RE: Appeal of denial, claim {claim} (SYNTHETIC CASE)",
        f"Patient: {patient_name} | Member ID: {member} | DOB: {c['dob']}{header_extra}",
        f"Requested service: CPT {cpt} | Diagnosis: ICD-10 {icd}",
        "",
        "## Response to denial reason",
        response,
        "",
        "## Clinical summary",
        *[f"- {b}" for b in bullets],
        "",
        "## Policy basis",
        f"Under {policy_ref} ({c['policy_title']}), the relevant criteria are "
        f"{crit_ids}. {request}".rstrip(),
        "",
    ]
    if enclosures:
        out += ["## Enclosures", *[f"- {e}" for e in enclosures], ""]
    out += signature
    return "\n".join(out) + "\n"


def build() -> dict:
    cases = []
    for i, s in enumerate(S):
        (
            name,
            dob,
            prov,
            title,
            cpt,
            icd,
            ptitle,
            crits,
            unmet,
            code,
            rtext,
            rterms,
            facts,
            core,
            flaw,
        ) = s
        n = i + 1
        policy_id = pid(n)
        distract = pid(n % len(S) + 1)
        claim, member = f"SYN-CLM-{200100 + n}", f"SYN-MBR-{300100 + n}"
        denial_dt = date(2026, 3, 2) + timedelta(days=n)
        deadline = denial_dt + timedelta(days=60)
        filed = denial_dt + timedelta(days=14)
        unmet_ids = [f"{policy_id}-C{k}" for k in (unmet if isinstance(unmet, list) else [unmet])]
        unmet_str = " and ".join(unmet_ids)
        plural = len(unmet_ids) > 1
        crit_ids = ", ".join(f"{policy_id}-C{k + 1}" for k in range(len(crits)))
        bullets = [f"{t[:-1] if t.endswith('.') else t} ({d})." for d, t in facts]
        response = (
            f"The plan denied this request under {code} ({rtext.split(':')[0]}), stating "
            f"that {unmet_str} {'are' if plural else 'is'} not met. "
            f"{'Those criteria are' if plural else 'That criterion is'} met: {core}."
        )
        encl = [f"Chart notes dated {facts[0][0]} through {facts[-1][0]}", "Copy of denial letter"]
        base = dict(
            date_s=str(filed),
            response=response,
            bullets=bullets,
            policy_ref=policy_id,
            crit_ids=crit_ids,
            request=REQUEST,
            enclosures=encl,
            signature=["Sincerely,", f"{prov}, {NPI}"],
            patient_name=name,
            member=member,
            claim=claim,
            cpt=cpt,
            icd=icd,
        )
        ctx = {"dob": dob, "policy_title": ptitle.replace(" (synthetic)", "")}
        good = render(ctx, **base)
        f = dict(base)
        kind, flaws = flaw["kind"], []
        if kind == "citation_invented":
            f["policy_ref"], flaws = "LCD L99999", ["citations"]
        elif kind == "citation_wrong_policy":
            f["policy_ref"], flaws = distract, ["citations"]
        elif kind == "fact_numeric":
            f["bullets"] = bullets + [flaw["bullet"]]
            flaws = ["facts_in_chart"]
        elif kind == "fact_nonnumeric":
            f["bullets"] = bullets + [flaw["bullet"]]
            flaws = ["facts_in_chart"]
        elif kind == "reason_unaddressed":
            f["response"], flaws = GENERIC, ["denial_reason_addressed"]
        elif kind == "criterion_not_cited":
            f["response"] = (
                f"The plan denied this request under {code}, stating that a "
                f"criterion is not met. That is not correct: {core}."
            )
            flaws = ["denial_reason_addressed"]
        elif kind == "wrong_member":
            f["member"], flaws = f"SYN-MBR-{300100 + n + 7}", ["identifiers_match"]
        elif kind == "wrong_cpt":
            f["cpt"], flaws = flaw["to"], ["identifiers_match"]
        elif kind == "missing_elements":
            f["enclosures"], f["signature"] = [], ["Thank you for your attention."]
            flaws = ["required_elements"]
        elif kind == "late_and_incomplete":
            f["date_s"] = str(deadline + timedelta(days=9))
            f["request"], f["icd"] = "", flaw["icd"]
            flaws = ["identifiers_match", "required_elements"]
        elif kind == "negation_flip":
            f["bullets"] = bullets + [flaw["bullet"]]
            flaws = ["facts_in_chart"]
        elif kind == "near_miss_member":
            # One-digit near-miss on the member id (last digit + 1, wrapping 9->0).
            last = int(member[-1])
            f["member"] = member[:-1] + str((last + 1) % 10)
            flaws = ["identifiers_match"]
        elif kind == "near_miss_cpt":
            f["cpt"], flaws = flaw["to"], ["identifiers_match"]
        elif kind == "swapped_icd":
            f["icd"], flaws = flaw["to"], ["identifiers_match"]
        elif kind == "paraphrase_flip":
            f["bullets"] = bullets + [flaw["bullet"]]
            flaws = ["facts_in_chart"]
        elif kind == "citation_bad_criterion":
            # Real policy, but a criterion number the policy does not have.
            f["crit_ids"] = f"{crit_ids}, {policy_id}-C{len(crits) + 1}"
            flaws = ["citations"]
        elif kind == "wrong_patient_name":
            # Patient name pasted from another case; every id still matches.
            f["patient_name"], flaws = flaw["to"], ["identifiers_match"]
        elif kind == "date_shift":
            f["bullets"] = bullets + [flaw["bullet"]]
            flaws = ["facts_in_chart"]
        elif kind == "reason_terms_missing":
            # Cites the unmet criterion but never engages with what the plan said was missing.
            f["response"] = (
                f"The plan denied this request under {code}, stating that "
                f"{unmet_ids[0]} is not met. We respectfully disagree with this "
                f"determination and ask the plan to reconsider."
            )
            flaws = ["denial_reason_addressed"]
        elif kind == "late_filing":
            f["date_s"], flaws = str(deadline + timedelta(days=3)), ["required_elements"]
        elif kind == "multiple_unmet":
            # Plan named two unmet criteria; the flawed letter answers only the first.
            f["response"] = (
                f"The plan denied this request under {code} "
                f"({rtext.split(':')[0]}), stating that {unmet_ids[0]} is not "
                f"met. That criterion is met: {flaw['partial']}."
            )
            flaws = ["denial_reason_addressed"]
        elif kind == "citation_real_looking_ncd":
            # Governing policy is cited, but so is a real-looking NCD that was never provided.
            f["request"] = f"Coverage is also supported by {flaw['cite']}. {REQUEST}"
            flaws = ["citations"]
        elif kind == "extra_phi_ssn":
            # Header over-shares an SSN that is nowhere in the chart or denial.
            f["header_extra"], flaws = f" | SSN: {flaw['ssn']}", ["extra_phi"]
        elif kind == "near_miss_claim":
            # One-digit near-miss on the claim id (last digit + 1, wrapping 9->0).
            f["claim"] = claim[:-1] + str((int(claim[-1]) + 1) % 10)
            flaws = ["identifiers_match"]
        elif kind == "missing_overturn_request":
            # Everything else is in place; the explicit request to overturn is dropped.
            f["request"], flaws = "", ["required_elements"]
        cases.append(
            {
                "id": f"PA-{n:03d}",
                "title": f"{title}: {kind.replace('_', ' ')} (synthetic)",
                "denial": {
                    "claim_id": claim,
                    "cpt": cpt,
                    "icd10": icd,
                    "reason_code": code,
                    "reason_text": rtext,
                    "unmet_criteria": unmet_ids,
                    "reason_terms": rterms,
                    "applicable_policy": policy_id,
                    "denial_date": str(denial_dt),
                    "appeal_deadline": str(deadline),
                    "letter_text": (
                        f"SYNTHETIC DENIAL LETTER. Example Health Plan (fictional). "
                        f"Claim {claim}, member {member}. CPT {cpt} denied under {code}: "
                        f"{rtext}. {'Criteria' if plural else 'Criterion'} {unmet_str} "
                        f"not met. You may appeal "
                        f"by {deadline}."
                    ),
                },
                "chart": {
                    "patient_id": f"SYN-PT-{n:04d}",
                    "patient_name": name,
                    "dob": dob,
                    "member_id": member,
                    "provider_name": prov,
                    "facts": [
                        {"id": f"F{k + 1}", "date": d, "text": t} for k, (d, t) in enumerate(facts)
                    ],
                },
                "policies": [policy(i), policy(n % len(S))],
                "reference_drafts": {
                    "good": {"text": good, "seeded_flaws": []},
                    "flawed": {"text": render(ctx, **f), "seeded_flaws": flaws},
                },
            }
        )
    return {
        "label": "SYNTHETIC EXAMPLE DATA: invented patients, claims, policies and letters "
        "for testing. Not real PHI, payer policy or Medicare NCD/LCD text.",
        "cases": cases,
    }


if __name__ == "__main__":
    json.dump(build(), sys.stdout, indent=2)
    sys.stdout.write("\n")
