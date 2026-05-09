# PrismBoard

Generative post-op care dashboard demo. Four roles (doctor / nurse / patient / family)
viewing the same two patients (one stable, one labile) — every dashboard is generated
on the fly from natural language, scoped by role permissions, and grounded on a mock
EHR built with DuckDB.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DEEPSEEK_API_KEY

python seed.py          # generate mock CSVs into ./data
python cache_specs.py rebuild   # optional: pre-bake fallback specs
streamlit run app.py
```

## Layout

```
app.py        Streamlit entry, role/patient sidebar, NL input, render area
prompts.py    All prompts (master system, role contexts, classifier, deepen, drilldown)
llm.py        DeepSeek client, spec generation (tool use), patient question classifier
renderer.py   spec -> Plotly/Streamlit (9 primitives, vital_trajectory)
data.py       DuckDB loader + SQL allow-list + role row filter
seed.py       Parameterised mock data generator (stable vs. labile profiles)
safety.py     Patient-side classifier router + fixed safety cards + nurse call
data/         Generated CSVs
cache_specs.py Pre-baked killer-prompt cache (fallback when LLM call fails)
cache/        Serialised specs from rehearsed killer prompts (fallback if LLM fails)
```

## Demo time anchor

Today is **Thursday morning, POD#2**. Surgery happened Monday afternoon; admission
Monday morning. All timestamps in seeded data are relative to this anchor.
