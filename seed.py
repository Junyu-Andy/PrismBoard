"""Generate mock data for the post-op care dashboard demo.

Two main patients drive the differentiation argument:
  P001 Wang Wei      - 32M, healthy, ORIF tibial plateau, 'stable' profile
  P002 Li Xiuying    - 71F, DM2/HTN/AF/prior MI/CKD, THA, 'labile' profile

Plus four background patients used only for the ward-overview panel.

The generator is parameterised on a 'profile' tag (stable | labile) so that
vitals fluctuation, abnormal-event density, medication count and nurse task
load all scale together.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Demo time anchor: Thursday morning, ~POD#2.
DEMO_NOW = datetime(2026, 5, 7, 10, 0)
ADMISSION_DT = datetime(2026, 5, 4, 8, 30)
SURGERY_START = datetime(2026, 5, 4, 13, 0)


# ----------------------------------------------------------------------- staff
DOCTORS = [
    {"id": "D001", "name": "Dr. Chen",  "department": "Orthopedics",     "title": "Attending"},
    {"id": "D002", "name": "Dr. Wang",  "department": "Orthopedics",     "title": "Resident"},
    {"id": "D003", "name": "Dr. Liu",   "department": "Endocrinology",   "title": "Attending"},
    {"id": "D004", "name": "Dr. Zhao",  "department": "Cardiology",      "title": "Attending"},
    {"id": "D005", "name": "Dr. Sun",   "department": "Anesthesiology",  "title": "Attending"},
]

NURSES = [
    {"id": "N001", "name": "Nurse Zhang Li",  "level": "senior", "current_shift": "morning"},
    {"id": "N002", "name": "Nurse Li Hua",    "level": "junior", "current_shift": "morning"},
    {"id": "N003", "name": "Nurse Wang Mei",  "level": "charge", "current_shift": "morning"},
    {"id": "N004", "name": "Nurse Zhou Min",  "level": "senior", "current_shift": "afternoon"},
    {"id": "N005", "name": "Nurse Wu Jing",   "level": "junior", "current_shift": "afternoon"},
    {"id": "N006", "name": "Nurse Sun Lei",   "level": "senior", "current_shift": "afternoon"},
    {"id": "N007", "name": "Nurse Yang Fang", "level": "junior", "current_shift": "night"},
    {"id": "N008", "name": "Nurse Hu Yan",    "level": "senior", "current_shift": "night"},
    {"id": "N009", "name": "Nurse Xu Ping",   "level": "junior", "current_shift": "night"},
    {"id": "N010", "name": "Nurse Gao Qiang", "level": "senior", "current_shift": "morning"},
]


# ---------------------------------------------------------------------- patients
PATIENTS = [
    {
        "patient_id": "P001", "name": "Wang Wei", "age": 32, "gender": "M", "blood_type": "A+",
        "ward": "Ortho-3", "bed": "12",
        "admission_date": ADMISSION_DT.date(), "surgery_date": SURGERY_START.date(),
        "primary_diagnosis": "Closed tibial plateau fracture (right)",
        "surgery_type": "ORIF (right tibial plateau)",
        "attending_doctor_id": "D001", "primary_nurse_id": "N001",
        "profile_summary": "32M athlete, healthy baseline; ORIF for tibial plateau fracture, smooth intra-op course; ambulating, expected discharge POD#3.",
        "_profile": "stable",
    },
    {
        "patient_id": "P002", "name": "Li Xiuying", "age": 71, "gender": "F", "blood_type": "B+",
        "ward": "Ortho-3", "bed": "08",
        "admission_date": ADMISSION_DT.date(), "surgery_date": SURGERY_START.date(),
        "primary_diagnosis": "Femoral neck fracture (left)",
        "surgery_type": "Total hip arthroplasty (left)",
        "attending_doctor_id": "D001", "primary_nurse_id": "N003",
        "profile_summary": "71F with DM2, HTN, AF, prior MI, mild CKD; THA for femoral neck fracture; complex course, ongoing glycaemic and anticoagulation management; discharge POD#7+.",
        "_profile": "labile",
    },
    {"patient_id":"P003","name":"Zhao Gang","age":54,"gender":"M","blood_type":"O+","ward":"Ortho-3","bed":"05",
     "admission_date":ADMISSION_DT.date(),"surgery_date":SURGERY_START.date(),
     "primary_diagnosis":"Ankle fracture (left)","surgery_type":"ORIF (left ankle)",
     "attending_doctor_id":"D002","primary_nurse_id":"N002",
     "profile_summary":"54M, ORIF ankle, uncomplicated.","_profile":"stable"},
    {"patient_id":"P004","name":"Liu Hong","age":63,"gender":"F","blood_type":"A-","ward":"Ortho-3","bed":"07",
     "admission_date":ADMISSION_DT.date(),"surgery_date":SURGERY_START.date(),
     "primary_diagnosis":"Distal radius fracture","surgery_type":"ORIF (right wrist)",
     "attending_doctor_id":"D002","primary_nurse_id":"N002",
     "profile_summary":"63F, ORIF wrist, mild HTN.","_profile":"stable"},
    {"patient_id":"P005","name":"Chen Bo","age":78,"gender":"M","blood_type":"O+","ward":"Ortho-3","bed":"10",
     "admission_date":ADMISSION_DT.date(),"surgery_date":SURGERY_START.date(),
     "primary_diagnosis":"Femoral neck fracture (right)","surgery_type":"Hemiarthroplasty",
     "attending_doctor_id":"D001","primary_nurse_id":"N003",
     "profile_summary":"78M, hemiarthroplasty, mild CHF.","_profile":"labile"},
    {"patient_id":"P006","name":"Yang Mei","age":45,"gender":"F","blood_type":"AB+","ward":"Ortho-3","bed":"15",
     "admission_date":ADMISSION_DT.date(),"surgery_date":SURGERY_START.date(),
     "primary_diagnosis":"Patella fracture (left)","surgery_type":"Tension band wiring",
     "attending_doctor_id":"D002","primary_nurse_id":"N001",
     "profile_summary":"45F, patella TBW, healthy baseline.","_profile":"stable"},
]


# --------------------------------------------------------------------- helpers
def shift_tag_for(dt: datetime) -> str:
    h = dt.hour
    if 7 <= h < 15:
        return "morning"
    if 15 <= h < 23:
        return "afternoon"
    return "night"


def round1(x: float) -> float:
    return round(x, 1)


# ---------------------------------------------------------- comorbidities / home meds
def gen_comorbidities():
    rows = []
    li = "P002"
    rows += [
        {"patient_id": li, "condition": "Type 2 diabetes mellitus",      "severity": "moderate", "since_date": "2014-03-01"},
        {"patient_id": li, "condition": "Hypertension",                  "severity": "moderate", "since_date": "2010-06-01"},
        {"patient_id": li, "condition": "Atrial fibrillation",           "severity": "moderate", "since_date": "2018-09-15"},
        {"patient_id": li, "condition": "Status post myocardial infarction (3y)", "severity": "severe",   "since_date": "2023-01-20"},
        {"patient_id": li, "condition": "Mild chronic kidney disease (stage 2)",  "severity": "mild",     "since_date": "2022-04-10"},
    ]
    rows += [
        {"patient_id": "P005", "condition": "Congestive heart failure (NYHA II)", "severity": "moderate", "since_date": "2020-01-01"},
        {"patient_id": "P004", "condition": "Hypertension",              "severity": "mild",     "since_date": "2019-05-01"},
    ]
    return rows


def gen_home_meds():
    rows = []
    li = "P002"
    rows += [
        {"patient_id": li, "drug_name": "Insulin glargine",  "dosage": "18 U",   "frequency": "qHS"},
        {"patient_id": li, "drug_name": "Insulin aspart",    "dosage": "6-8 U",  "frequency": "TID with meals"},
        {"patient_id": li, "drug_name": "Amlodipine",        "dosage": "5 mg",   "frequency": "QD"},
        {"patient_id": li, "drug_name": "Rivaroxaban",       "dosage": "20 mg",  "frequency": "QD"},
        {"patient_id": li, "drug_name": "Atorvastatin",      "dosage": "20 mg",  "frequency": "qHS"},
        {"patient_id": li, "drug_name": "Metoprolol",        "dosage": "47.5 mg","frequency": "QD"},
    ]
    rows += [
        {"patient_id": "P004", "drug_name": "Amlodipine", "dosage": "5 mg", "frequency": "QD"},
        {"patient_id": "P005", "drug_name": "Furosemide", "dosage": "20 mg", "frequency": "QD"},
        {"patient_id": "P005", "drug_name": "Bisoprolol", "dosage": "2.5 mg", "frequency": "QD"},
    ]
    return rows


# --------------------------------------------------------------------- surgeries
def gen_surgeries():
    rows = []
    for p in PATIENTS:
        if p["patient_id"] == "P001":
            duration, anesth, blood, comp = 150, "Spinal + sedation", 180, "Uneventful."
            surgeon = "D001"
        elif p["patient_id"] == "P002":
            duration, anesth, blood, comp = 240, "General", 520, "Anticoagulation reversal extended OR time; haemostasis adequate."
            surgeon = "D001"
        elif p["patient_id"] == "P003":
            duration, anesth, blood, comp = 110, "Regional", 90, "Uneventful."
            surgeon = "D002"
        elif p["patient_id"] == "P004":
            duration, anesth, blood, comp = 90, "Regional", 60, "Uneventful."
            surgeon = "D002"
        elif p["patient_id"] == "P005":
            duration, anesth, blood, comp = 180, "General", 380, "Mild intra-op hypotension, responsive to fluids."
            surgeon = "D001"
        else:
            duration, anesth, blood, comp = 100, "General", 100, "Uneventful."
            surgeon = "D002"
        ended = SURGERY_START + timedelta(minutes=duration)
        rows.append({
            "id": f"S{p['patient_id'][1:]}", "patient_id": p["patient_id"],
            "surgery_type": p["surgery_type"],
            "started_at": SURGERY_START, "ended_at": ended,
            "duration_minutes": duration, "surgeon_id": surgeon,
            "anesthesia_type": anesth, "blood_loss_ml": blood,
            "complications_text": comp,
        })
    return rows


# --------------------------------------------------------------------- vitals
def gen_vitals_for(patient_id: str, profile: str, age: int):
    """30-min cadence, 5 days post-op (~240 rows).

    Recovery is modelled monotonically: a smooth daily-decline baseline
    plus small noise, with a small number of *deliberate* out-of-range
    events so demo dashboards have something to highlight. The labile
    profile (Li Xiuying) has clearly more events than the stable one.
    """
    rows = []
    surgery_end = SURGERY_START + timedelta(minutes=240 if profile == "labile" else 150)
    t = surgery_end
    end_t = surgery_end + timedelta(days=5)
    step = timedelta(minutes=30)

    while t < end_t:
        hours_post = (t - surgery_end).total_seconds() / 3600.0
        days_post  = hours_post / 24.0  # 0..5

        if profile == "stable":
            # Smooth recovery: HR 80 -> 66, BP_sys 124 -> 116, RR 16 -> 13.
            hr   = 80 - 14 * (days_post / 5)  + random.gauss(0, 1.5)
            sys_ = 124 - 8 * (days_post / 5)  + random.gauss(0, 2.0)
            dia  = 78  - 6 * (days_post / 5)  + random.gauss(0, 1.5)
            spo2 = 98 + random.gauss(0, 0.4)
            rr   = 16 - 3 * (days_post / 5)  + random.gauss(0, 0.7)
            # One mild fever evening of POD#1 (32-36h post-op).
            if 32 <= hours_post <= 36:
                temp = 37.4 + random.gauss(0, 0.1)
            else:
                temp = 36.7 + random.gauss(0, 0.15)
            # One transient HR spike during ambulation on POD#2.
            if 50 <= hours_post <= 51:
                hr += 22
            pain = max(1, round(4 - 3 * (days_post / 5) + random.uniform(-0.4, 0.4)))
            urine = random.randint(80, 120)

        else:  # labile - Li Xiuying
            # Elevated baseline due to AF and post-op stress, gradual
            # improvement towards day 5 (HR 105 -> 85, BP_sys 150 -> 128).
            hr   = 105 - 20 * (days_post / 5) + random.gauss(0, 4)
            sys_ = 150 - 22 * (days_post / 5) + random.gauss(0, 5)
            dia  = 90  - 10 * (days_post / 5) + random.gauss(0, 3.5)
            spo2 = 96 + random.gauss(0, 0.6)
            rr   = 20 - 4 * (days_post / 5)  + random.gauss(0, 1)
            temp = 36.8 + random.gauss(0, 0.2)

            # POD#0-1 tachycardia episodes (~20% of readings).
            if days_post < 1.5 and random.random() < 0.20:
                hr += random.uniform(15, 25)
            # BP excursions (~10%).
            if random.random() < 0.10:
                sys_ += random.choice([-30, 30]) + random.gauss(0, 5)
            # SpO2 dips on POD#0-1 (~8%).
            if days_post < 1.5 and random.random() < 0.08:
                spo2 -= random.uniform(2, 5)
            # Two clear fever episodes: 28-36h and 76-82h.
            if 28 <= hours_post <= 36:
                temp = 38.0 + random.gauss(0, 0.15)
            elif 76 <= hours_post <= 82:
                temp = 37.7 + random.gauss(0, 0.1)

            pain = max(3, round(7 - 4 * (days_post / 5) + random.uniform(-0.6, 0.8)))
            if random.random() < 0.06:
                pain += 2
            urine = (random.randint(30, 60) if days_post < 1.0
                     else random.randint(50, 90))

        sh = shift_tag_for(t)
        nurse = random.choice([n_["id"] for n_ in NURSES if n_["current_shift"] == sh])

        rows.append({
            "patient_id": patient_id,
            "recorded_at": t,
            "hr":          int(round(max(45, min(170, hr)))),
            "bp_sys":      int(round(max(70, min(220, sys_)))),
            "bp_dia":      int(round(max(40, min(130, dia)))),
            "spo2":        int(round(max(85, min(100, spo2)))),
            "rr":          int(round(max(8,  min(35,  rr)))),
            "temp_c":      round1(max(35.5, min(40.0, temp))),
            "pain_score":  int(min(10, pain)),
            "urine_output_ml": urine,
            "recorded_by_nurse_id": nurse,
        })
        t += step
    return rows


# --------------------------------------------------------------------- glucose
def gen_glucose():
    """Li Xiuying only: 6-8 readings/day x 5 days, with a clear recovery
    arc and one demo-friendly hypoglycaemia event."""
    rows = []
    contexts = [
        ("06:30", "fasting"),
        ("08:00", "post_breakfast"),
        ("11:30", "pre_lunch"),
        ("13:30", "post_lunch"),
        ("17:30", "pre_dinner"),
        ("19:30", "post_dinner"),
        ("22:00", "bedtime"),
    ]
    # Day-by-day target glucose (mmol/L): post-op stress on day 0,
    # gradual control by day 4.
    day_targets = {
        0: (10.0, 14.0, 11.0),  # fasting / post-meal / other
        1: (9.0,  13.0, 10.0),
        2: (8.0,  11.0,  9.0),
        3: (7.0,  10.0,  8.0),
        4: (6.5,   9.0,  7.5),
    }
    for d in range(5):
        day = (SURGERY_START + timedelta(days=d)).date()
        f_t, p_t, o_t = day_targets[d]
        for hhmm, ctx in contexts:
            if random.random() < 0.92:
                hh, mm = map(int, hhmm.split(":"))
                ts = datetime.combine(day, datetime.min.time()).replace(hour=hh, minute=mm)
                if ts < SURGERY_START:
                    continue
                if ctx == "fasting":
                    val = f_t + random.gauss(0, 1.0)
                elif ctx.startswith("post"):
                    val = p_t + random.gauss(0, 1.5)
                else:
                    val = o_t + random.gauss(0, 1.2)
                rows.append({
                    "patient_id":  "P002",
                    "recorded_at": ts,
                    "value_mmol":  round1(max(3.0, min(20, val))),
                    "context":     ctx,
                })
    # Insert a single hypoglycaemia event on POD#1 mid-morning.
    rows.append({
        "patient_id":  "P002",
        "recorded_at": (SURGERY_START + timedelta(days=1)).replace(hour=10, minute=15),
        "value_mmol":  4.0,
        "context":     "between_meals",
    })
    rows.sort(key=lambda r: r["recorded_at"])
    return rows


# --------------------------------------------------------------------- medications
def _med_rows(patient_id, drug, dose, route, start: datetime, every_h: int, days: int, refusal_rate=0.02):
    rows = []
    t = start
    end = SURGERY_START + timedelta(days=days)
    while t < end:
        scheduled = t
        status = "scheduled"
        admin_at = None
        admin_by = None
        if scheduled < DEMO_NOW:
            r = random.random()
            if r < refusal_rate:
                status = "refused"
            elif r < refusal_rate + 0.02:
                status = "held"
            else:
                status = "administered"
                admin_at = scheduled + timedelta(minutes=random.randint(-5, 25))
                sh = shift_tag_for(admin_at)
                admin_by = random.choice([n_["id"] for n_ in NURSES if n_["current_shift"] == sh])
        rows.append({
            "patient_id": patient_id, "scheduled_at": scheduled,
            "drug_name": drug, "dose": dose, "route": route,
            "status": status, "administered_at": admin_at,
            "administered_by": admin_by,
        })
        t += timedelta(hours=every_h)
    return rows


def gen_medications():
    rows = []
    s_end = SURGERY_START + timedelta(minutes=150)
    # Wang Wei: simple regimen
    rows += _med_rows("P001", "Acetaminophen",  "500 mg", "PO", s_end + timedelta(hours=2), 6, 5)
    rows += _med_rows("P001", "Cefuroxime",     "750 mg", "IV", s_end + timedelta(hours=1), 8, 3)
    rows += _med_rows("P001", "Enoxaparin",     "40 mg",  "SC", s_end + timedelta(hours=12), 24, 5)
    rows += _med_rows("P001", "Ibuprofen",      "400 mg", "PO", s_end + timedelta(hours=4), 8, 5)

    # Li Xiuying: complex regimen
    s_end2 = SURGERY_START + timedelta(minutes=240)
    rows += _med_rows("P002", "Insulin glargine", "16 U",  "SC", s_end2 + timedelta(hours=20), 24, 5)
    rows += _med_rows("P002", "Insulin aspart",   "4-8 U", "SC", s_end2 + timedelta(hours=18), 6, 5)  # before meals approximated
    rows += _med_rows("P002", "Amlodipine",       "5 mg",  "PO", s_end2 + timedelta(hours=20), 24, 5)
    rows += _med_rows("P002", "Rivaroxaban",      "15 mg", "PO", s_end2 + timedelta(hours=24), 24, 5)
    rows += _med_rows("P002", "Atorvastatin",     "20 mg", "PO", s_end2 + timedelta(hours=22), 24, 5)
    rows += _med_rows("P002", "Metoprolol",       "23.75 mg","PO", s_end2 + timedelta(hours=20), 12, 5)
    rows += _med_rows("P002", "Acetaminophen",    "500 mg","PO", s_end2 + timedelta(hours=2), 6, 5)
    rows += _med_rows("P002", "Tramadol",         "50 mg", "PO", s_end2 + timedelta(hours=4), 8, 4)
    rows += _med_rows("P002", "Cefuroxime",       "750 mg","IV", s_end2 + timedelta(hours=1), 8, 3)
    rows += _med_rows("P002", "Pantoprazole",     "40 mg", "IV", s_end2 + timedelta(hours=2), 24, 4)
    return rows


# --------------------------------------------------------------------- labs
def _lab(patient_id, sampled_at, panel, name, value, unit, ref, flag=""):
    return {
        "patient_id": patient_id, "sampled_at": sampled_at,
        "panel": panel, "test_name": name, "value": value, "unit": unit,
        "reference_range": ref, "abnormal_flag": flag,
    }


def gen_labs():
    rows = []
    days = [SURGERY_START - timedelta(hours=4),
            SURGERY_START + timedelta(hours=20),
            SURGERY_START + timedelta(days=2, hours=6),
            SURGERY_START + timedelta(days=4, hours=6)]

    for ts in days[:3]:
        # Wang Wei: CBC + BMP, all normal
        rows += [
            _lab("P001", ts, "CBC", "WBC", round1(random.uniform(5.5, 8.5)), "10^9/L", "4.0-10.0"),
            _lab("P001", ts, "CBC", "Hgb", random.randint(125, 145), "g/L", "120-160"),
            _lab("P001", ts, "CBC", "Plt", random.randint(180, 280), "10^9/L", "100-300"),
            _lab("P001", ts, "BMP", "K",   round1(random.uniform(3.8, 4.6)), "mmol/L", "3.5-5.0"),
            _lab("P001", ts, "BMP", "Na",  random.randint(138, 142), "mmol/L", "135-145"),
            _lab("P001", ts, "BMP", "Cr",  random.randint(70, 95),  "umol/L",  "60-110"),
        ]

    # Li Xiuying: CBC + BMP + coag + troponin, with abnormalities
    for i, ts in enumerate(days):
        rows += [
            _lab("P002", ts, "CBC", "WBC", round1(random.uniform(8.5, 13.0)), "10^9/L", "4.0-10.0", "H" if random.random() < 0.5 else ""),
            _lab("P002", ts, "CBC", "Hgb", random.randint(95, 115),           "g/L",    "115-150",  "L"),
            _lab("P002", ts, "CBC", "Plt", random.randint(180, 260),          "10^9/L", "100-300"),
            _lab("P002", ts, "BMP", "K",   round1(random.uniform(3.4, 4.9)),  "mmol/L", "3.5-5.0",  "L" if random.random() < 0.3 else ""),
            _lab("P002", ts, "BMP", "Cr",  random.randint(110, 150),          "umol/L", "60-110",   "H"),
            _lab("P002", ts, "BMP", "Glucose", round1(random.uniform(8.0, 14.0)), "mmol/L", "3.9-7.0", "H"),
            _lab("P002", ts, "Coag","INR", round1(random.uniform(1.6, 2.6)),  "",       "0.9-1.2",  "H"),
            _lab("P002", ts, "Coag","PT",  round1(random.uniform(15, 24)),    "s",      "11-13.5",  "H"),
            _lab("P002", ts, "Cardiac","Troponin I", round1(random.uniform(0.02, 0.08)), "ng/mL", "<0.04",
                 "H" if i <= 1 else ""),
        ]
    return rows


# --------------------------------------------------------------------- care tasks
def _task(patient_id, scheduled_at, task_type, description, priority, status, by=None):
    return {
        "patient_id": patient_id, "scheduled_at": scheduled_at,
        "task_type": task_type, "description": description,
        "priority": priority, "status": status,
        "completed_at": scheduled_at + timedelta(minutes=random.randint(2, 25)) if status == "completed" else None,
        "completed_by_nurse_id": by if status == "completed" else None,
        "shift_tag": shift_tag_for(scheduled_at),
    }


def gen_care_tasks():
    rows = []
    # Wang Wei: ~4-5/day x 5 days = ~20
    for d in range(5):
        day_start = SURGERY_START.replace(hour=7, minute=0) + timedelta(days=d)
        for hhmm, ttype, desc, prio in [
            ("07:30", "vitals",   "Vitals check",                 "routine"),
            ("09:00", "dressing", "Wound dressing inspection",    "routine"),
            ("11:00", "mobility", "Assisted ambulation",          "routine"),
            ("14:00", "pain_assess", "Pain reassessment (NRS)",   "routine"),
            ("19:30", "vitals",   "Vitals check (evening)",       "routine"),
        ]:
            hh, mm = map(int, hhmm.split(":"))
            ts = day_start.replace(hour=hh, minute=mm)
            if ts < SURGERY_START + timedelta(hours=2):
                continue
            status = "completed" if ts < DEMO_NOW - timedelta(minutes=20) else (
                "in_progress" if ts < DEMO_NOW + timedelta(minutes=30) else "scheduled")
            sh = shift_tag_for(ts)
            by = random.choice([n_["id"] for n_ in NURSES if n_["current_shift"] == sh])
            rows.append(_task("P001", ts, ttype, desc, prio, status, by))
        if d == 2:
            rows.append(_task("P001", day_start.replace(hour=10, minute=30),
                              "mobilization_milestone", "Independent transfer bed-to-chair",
                              "routine",
                              "completed",
                              "N001"))

    # Li Xiuying: ~12-15/day x 5 days = ~60+
    for d in range(5):
        day_start = SURGERY_START.replace(hour=6, minute=0) + timedelta(days=d)
        plan = [
            ("06:30", "glucose",  "Fasting glucose check",                "high"),
            ("07:00", "vitals",   "Vitals check incl. SpO2 + telemetry",  "high"),
            ("08:00", "glucose",  "Post-breakfast glucose",               "high"),
            ("09:00", "dressing", "Wound dressing + drain inspection",    "routine"),
            ("10:00", "meal",     "Diabetic meal supervision",            "routine"),
            ("11:30", "glucose",  "Pre-lunch glucose",                    "high"),
            ("13:30", "glucose",  "Post-lunch glucose",                   "high"),
            ("14:00", "pain_assess", "Pain reassessment (NRS)",           "routine"),
            ("15:00", "mobility", "Assisted sit-up + leg exercises",      "routine"),
            ("17:30", "glucose",  "Pre-dinner glucose",                   "high"),
            ("19:00", "vitals",   "Vitals check (evening)",               "high"),
            ("19:30", "glucose",  "Post-dinner glucose",                  "high"),
            ("21:00", "family_facilitate", "Family update call",          "routine"),
            ("22:00", "glucose",  "Bedtime glucose",                      "high"),
        ]
        for hhmm, ttype, desc, prio in plan:
            hh, mm = map(int, hhmm.split(":"))
            ts = day_start.replace(hour=hh, minute=mm)
            if ts < SURGERY_START + timedelta(hours=2):
                continue
            status = "completed" if ts < DEMO_NOW - timedelta(minutes=20) else (
                "in_progress" if ts < DEMO_NOW + timedelta(minutes=30) else "scheduled")
            sh = shift_tag_for(ts)
            by = random.choice([n_["id"] for n_ in NURSES if n_["current_shift"] == sh])
            rows.append(_task("P002", ts, ttype, desc, prio, status, by))
    return rows


# --------------------------------------------------------------------- doctor notes
def gen_doctor_notes():
    rows = []
    rows += [
        {"patient_id":"P001","written_at":SURGERY_START + timedelta(hours=4),"doctor_id":"D001","note_type":"order",
         "content":"Post-op orders: NPO x 4h, then advance diet as tolerated. Acetaminophen + ibuprofen scheduled. Enoxaparin 40mg SC daily x 5d. Cefuroxime 750mg IV q8h x 3d. NWB right LE x 2d, then PWB."},
        {"patient_id":"P001","written_at":SURGERY_START + timedelta(days=1, hours=8),"doctor_id":"D001","note_type":"rounds",
         "content":"POD#1: vitals stable, pain controlled, ambulated 10m with crutches. Wound clean & dry. Plan: continue current regimen, advance mobility."},
        {"patient_id":"P001","written_at":SURGERY_START + timedelta(days=2, hours=8),"doctor_id":"D001","note_type":"discharge_planning",
         "content":"POD#2: meets discharge criteria pending PT clearance and 24h tolerance of full diet. Plan discharge POD#3 with PT follow-up at 2 weeks."},
    ]
    rows += [
        {"patient_id":"P002","written_at":SURGERY_START + timedelta(hours=6),"doctor_id":"D001","note_type":"order",
         "content":"Post-op orders: telemetry monitoring x 48h. Resume basal insulin at 80%, sliding-scale aspart pre-meal + bedtime. Hold rivaroxaban x 24h, restart 15mg PO daily. Metoprolol 23.75mg PO BID. Cefuroxime 750mg IV q8h x 3d. Endocrine + cardiology consults requested."},
        {"patient_id":"P002","written_at":SURGERY_START + timedelta(hours=10),"doctor_id":"D003","note_type":"consult",
         "content":"Endocrine: blood glucose 11.8 mmol/L. Recommend basal-bolus insulin per sliding scale, target 6-10 mmol/L. Avoid hypoglycaemia. Resume home insulin glargine at reduced dose."},
        {"patient_id":"P002","written_at":SURGERY_START + timedelta(hours=14),"doctor_id":"D004","note_type":"consult",
         "content":"Cardiology: AF rate-controlled on metoprolol. Hold rivaroxaban x 24h then restart at therapeutic dose. Monitor for post-op AF. ECG unchanged from baseline."},
        {"patient_id":"P002","written_at":SURGERY_START + timedelta(days=1, hours=8),"doctor_id":"D001","note_type":"rounds",
         "content":"POD#1: BP 95-160 swings, HR controlled, glucose 8-14, mild orthostatic dizziness on sit-up. Plan: reinforce IV fluids, recheck Hgb, continue endocrine regimen."},
        {"patient_id":"P002","written_at":SURGERY_START + timedelta(days=2, hours=8),"doctor_id":"D001","note_type":"rounds",
         "content":"POD#2: vitals borderline, pain 6/10, glucose still labile. Continue current plan; PT to defer ambulation today, sit-to-stand only. Discharge not before POD#7."},
    ]
    return rows


# --------------------------------------------------------------------- family comms
def gen_family_comms():
    rows = []
    rows += [
        {"patient_id":"P001","recorded_at":SURGERY_START + timedelta(days=1, hours=10),
         "family_name":"Wang Tao","relationship":"brother","channel":"visit",
         "summary":"Brother visited for 30min, brought clean clothes; updated on smooth recovery."},
        {"patient_id":"P001","recorded_at":SURGERY_START + timedelta(days=1, hours=18),
         "family_name":"Liu Jia","relationship":"wife","channel":"phone",
         "summary":"Wife asked about discharge; informed POD#3 likely."},
    ]
    rows += [
        {"patient_id":"P002","recorded_at":SURGERY_START + timedelta(hours=20),
         "family_name":"Li Min","relationship":"daughter","channel":"phone",
         "summary":"Daughter anxious; explained ICU not needed, telemetry monitoring overnight, glucose stabilising."},
        {"patient_id":"P002","recorded_at":SURGERY_START + timedelta(days=1, hours=11),
         "family_name":"Li Min","relationship":"daughter","channel":"visit",
         "summary":"Daughter visited 1h; reviewed care plan, glycaemic targets, anticoagulation restart timing."},
        {"patient_id":"P002","recorded_at":SURGERY_START + timedelta(days=1, hours=20),
         "family_name":"Li Qiang","relationship":"son","channel":"phone",
         "summary":"Son requested cardiology update; provided summary of consult."},
        {"patient_id":"P002","recorded_at":SURGERY_START + timedelta(days=2, hours=8),
         "family_name":"Li Min","relationship":"daughter","channel":"message",
         "summary":"Daughter messaged for morning status; replied stable, glucose 9.2, plan unchanged."},
        {"patient_id":"P002","recorded_at":SURGERY_START + timedelta(days=2, hours=9),
         "family_name":"Li Min","relationship":"daughter","channel":"phone",
         "summary":"Daughter asking about safe visit time; recommended after 2pm when PT done."},
    ]
    return rows


# --------------------------------------------------------------------- write
def write_csv(name, rows, columns=None):
    if columns and not rows:
        df = pd.DataFrame({c: pd.Series(dtype="object") for c in columns})
    else:
        df = pd.DataFrame(rows)
        if columns:
            df = df[columns]
    df.to_csv(DATA_DIR / f"{name}.csv", index=False)
    print(f"  {name:24s} {len(df):5d} rows  -> data/{name}.csv")


def main():
    print("Generating mock data ...")

    # patients (drop the internal _profile field before writing)
    patients_clean = [{k: v for k, v in p.items() if not k.startswith("_")} for p in PATIENTS]
    write_csv("patients", patients_clean)
    write_csv("doctors", DOCTORS)
    write_csv("nurses", NURSES)
    write_csv("comorbidities", gen_comorbidities())
    write_csv("home_medications", gen_home_meds())
    write_csv("surgeries", gen_surgeries())

    vitals = []
    for p in PATIENTS:
        if p["patient_id"] in ("P001", "P002"):
            vitals += gen_vitals_for(p["patient_id"], p["_profile"], p["age"])
    write_csv("vitals", vitals)

    write_csv("glucose_logs", gen_glucose())
    write_csv("medications", gen_medications())
    write_csv("lab_results", gen_labs())
    write_csv("care_tasks", gen_care_tasks())
    write_csv("doctor_notes", gen_doctor_notes())
    write_csv("family_communications", gen_family_comms())

    # patient_questions (empty table, populated at runtime by safety.py)
    write_csv("patient_questions", [], columns=[
        "patient_id", "asked_at", "question", "classification", "routed_to_nurse_id"
    ])

    print("Done.")


if __name__ == "__main__":
    main()
