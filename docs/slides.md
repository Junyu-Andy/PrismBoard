---
theme: default
title: Prisma — Agentic UI for post-op care
info: |
  ## Prisma
  One truth. Four views. Made for this person, right now.

  Junyu Zhao (Andy) · Open to collab
class: text-center
highlighter: shiki
drawings:
  persist: false
transition: slide-left
mdc: true
fonts:
  sans: Inter
  weights: '300,400,500,600,700'
---

<div class="flex flex-col items-center justify-center h-full pb-20">

<img src="/prisma-hero.png" class="max-h-[55vh] object-contain" />

<p class="text-xl opacity-80 mt-5">One truth. Four views.<br/>Made for this person, right now.</p>

</div>

<div class="absolute bottom-8 left-0 right-0 text-center text-sm opacity-60">
Junyu Zhao (Andy) · Open to collab · zhaojyxs@gmail.com · X @realAndyZhao
</div>

<!--
Don't speak. Let them read it.
The illustration does the work — the prism is the product thesis,
the four colored rays preview the four stakeholders.
-->

---
layout: default
---

# Hospital information is broken — in four different ways

<div class="grid grid-cols-2 gap-4 mt-6">

<div class="border-l-4 border-blue-500 pl-4">
  <p class="text-xs uppercase tracking-wider opacity-60 mb-1">Doctor</p>
  <p class="text-xl font-medium mb-1">Drowning in data</p>
  <p class="text-xs opacity-70">2 hours of paperwork for every 1 hour with patients</p>
</div>

<div class="border-l-4 border-green-500 pl-4">
  <p class="text-xs uppercase tracking-wider opacity-60 mb-1">Nurse</p>
  <p class="text-xl font-medium mb-1">Lost at handoff</p>
  <p class="text-xs opacity-70">80% of serious medical errors involve handoff communication <span class="opacity-60">— Joint Commission</span></p>
</div>

<div class="border-l-4 border-amber-500 pl-4 bg-amber-50 dark:bg-amber-900/20 -mx-1 px-4 py-2 rounded">
  <p class="text-xs uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">⭐ Patient</p>
  <p class="text-xl font-medium mb-1">Information vacuum</p>
  <p class="text-xs opacity-80">5 minutes a day with the doctor.<br/>23 hours alone with their anxiety.</p>
</div>

<div class="border-l-4 border-red-500 pl-4">
  <p class="text-xs uppercase tracking-wider opacity-60 mb-1">Family</p>
  <p class="text-xl font-medium mb-1">Phone tag</p>
  <p class="text-xs opacity-70">Missed calls → worry → calls flood the nurse station</p>
</div>

</div>

<div class="mt-4 text-center">
  <p class="text-lg leading-snug">
    Most medical AI helps the doctor.
    <span class="text-amber-600 dark:text-amber-400 font-bold">Nobody is serving the other three.</span>
  </p>
</div>

<!--
"Hospital information flow is broken — but not in one place.
It's broken in four different ways for four different people.

The one most products ignore is the middle:
the patient sitting in an information vacuum.

Today's medical AI mostly helps the doctor.
Nobody's serving the other three."

(45 seconds. Don't rush the patient quadrant — point at it.)
-->

---
layout: default
---

# This is a math problem

<div class="grid grid-cols-2 gap-10 mt-4">

<div class="flex flex-col justify-center">

<p class="text-xl font-medium mb-4">Static dashboards can't keep up</p>

<div class="text-2xl font-mono leading-relaxed opacity-90">
stakeholder<br/>
× condition<br/>
× recovery stage<br/>
× current event<br/>
× user intent
</div>

<p class="mt-5 text-xl text-red-500 font-medium">
= tens of thousands of combinations
</p>

<p class="mt-3 text-sm opacity-70 leading-relaxed">
No team can hand-design that many dashboards.<br/>
This is math, not design.
</p>

</div>

<div class="flex flex-col justify-center items-center">

<div class="grid grid-cols-2 gap-3 w-full">

<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
<div class="text-4xl mb-1">🏃</div>
<p class="font-medium text-sm">Wang Wei</p>
<p class="text-xs opacity-70 mt-1">32, athlete<br/>tibial plateau, ORIF<br/>discharges tomorrow</p>
</div>

<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
<div class="text-4xl mb-1">👵</div>
<p class="font-medium text-sm">Li Xiuying</p>
<p class="text-xs opacity-70 mt-1">71, DM2 + AF + prior MI<br/>hip replacement<br/>recovery is rocky</p>
</div>

</div>

<p class="text-center text-xs opacity-70 mt-4 italic">
Same surgery. Same ward. Same day.<br/>
4 roles × 2 patients = 8 interfaces. None look alike.
</p>

</div>

</div>

<!--
"This isn't a design problem. It's a math problem.

Five dimensions multiplied together gives you tens of thousands
of combinations. No team can hand-design that many dashboards.

Wang Wei and Li Xiuying are just two of those combinations.
Same surgery, same ward, same day. But four roles times two patients
gives you eight interfaces — and not one of them looks the same."

(45 seconds. Pause on 'tens of thousands' — let it land.)

Replace the emoji with actual generated portraits before going live.
-->

---
layout: center
class: text-center
---

# Live demo

<p class="text-xl opacity-70 mt-6">Prisma · running on DeepSeek + Streamlit</p>

<div class="absolute bottom-8 right-8 text-xs opacity-50 text-left max-w-xs">
<div class="font-mono">
4 roles → Streamlit → DeepSeek V3 → DuckDB → 11 mock tables
</div>
</div>

<!--
================================================================
LIVE DEMO SCRIPT — 2:50 total
================================================================

0:00–0:20 · Doctor view × Wang Wei
   Type: "How is Wang Wei doing in the last 24 hours?"
   Say: "This is the doctor's view of Wang Wei."

0:20–0:50 · ⭐ Switch patient dropdown to Li Xiuying
   The dashboard regenerates.
   Say: "Same doctor, different patient.
        The whole dashboard just changed.
        This is what we mean by REFRACTION.
        The AI isn't rendering — it's splitting one truth
        into different views."
   Open the "Here's how I thought about it" panel.
   Read one rejected option out loud.

0:50–1:20 · Click "Time resolution → 24h"
   Say: "Watch the badges — added, changed.
        Every time the AI modifies the view, you see what changed.
        This is the Cursor accept-reject pattern, but for dashboards."

1:20–1:50 · ⭐⭐⭐ Switch to Li Xiuying × Patient view
   Type: "Will my heart be okay?"
   WAIT ONE BEAT. Let the safety card render.
   PAUSE the demo.
   Say: "The AI does not answer this. It knows this question
        is not its job. It calls a nurse instead.
        We call this GRACEFUL REFUSAL — refusal as a visible
        action in the UI, not a hidden rule in a system prompt.
        This is the most important promise we make to hospitals."

1:50–2:20 · Switch to Li Xiuying × Family view
   Say: "Same underlying fact.
        The doctor sees numbers and trend lines.
        The family sees 'Mom is stable today.'
        This isn't permission filtering — it's COGNITIVE RECASTING.
        Same truth, translated for the person reading it."

2:20–2:50 · Briefly back to a doctor view, show reasoning panel once more.
   Say: "Every dashboard has its own 'why I built this' card.
        Auditable. Explainable. Editable.
        Hand back to slides."

================================================================
The three moments judges must remember:
  0:20  patient switch       → Refraction visible
  1:20  heart question       → Graceful Refusal lands
  1:50  family view tone     → Cognitive Recasting completes
================================================================
-->

---
layout: default
---

# Three patterns we are claiming as new

<div class="grid grid-cols-3 gap-6 mt-12">

<div class="border-t-4 border-blue-500 pt-6">
  <p class="text-sm uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-3">Pattern 1</p>
  <h2 class="!text-3xl !mb-3">Refraction</h2>
  <p class="opacity-80 leading-relaxed">One truth → many UIs.</p>
  <p class="text-sm opacity-60 mt-3 leading-relaxed">The agent is a prism, not a renderer. It splits one underlying patient state into role-specific views, in real time.</p>
</div>

<div class="border-t-4 border-green-500 pt-6">
  <p class="text-sm uppercase tracking-wider text-green-600 dark:text-green-400 mb-3">Pattern 2</p>
  <h2 class="!text-3xl !mb-3">Cognitive recasting</h2>
  <p class="opacity-80 leading-relaxed">Same fact → different language.</p>
  <p class="text-sm opacity-60 mt-3 leading-relaxed">Doctors see numbers. Patients see plain words. Family sees reassurance. Not permission filtering — semantic translation.</p>
</div>

<div class="border-t-4 border-amber-500 pt-6">
  <p class="text-sm uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-3">Pattern 3</p>
  <h2 class="!text-3xl !mb-3">Graceful refusal</h2>
  <p class="opacity-80 leading-relaxed">"No" as a visible action.</p>
  <p class="text-sm opacity-60 mt-3 leading-relaxed">When the agent shouldn't act, refusal becomes a UI element — not a hidden rule in a system prompt.</p>
</div>

</div>

<div class="mt-12 pt-6 border-t border-gray-300 dark:border-gray-700 text-sm opacity-70">
<p><span class="font-medium">Today's generative UI:</span> Cursor, v0, Canvas — all <em>one user × one intent × one UI</em>.</p>
<p class="mt-1"><span class="font-medium">Prisma:</span> <em>one truth × many stakeholders × many UIs.</em></p>
</div>

<!--
"Generative UI today is one user, one intent, one UI.
Cursor gives one developer one file. v0 gives one designer one component.
Canvas gives one writer one document. All one-to-one.

We're doing one truth, many stakeholders, many UIs.
The agent isn't a renderer. It's a prism.

And the more important shift is graceful refusal.
Today's agentic UI is racing to do MORE.
We're showing an agent that knows what it shouldn't do —
and turns that refusal into a visible action in the interface,
not a hidden rule in a system prompt."

(45 seconds. Don't rush. These three words are what they remember.)
-->

---
layout: default
---

# Why now, and what's next

<div class="grid grid-cols-2 gap-12 mt-10">

<div>

<p class="text-sm uppercase tracking-wider opacity-60 mb-3">Buyer</p>
<p class="text-2xl font-medium mb-1">Hospitals</p>
<p class="text-sm opacity-70 mb-8">Orthopedic and trauma surgery wards, post-op care unit</p>

<p class="text-sm uppercase tracking-wider opacity-60 mb-3">Value</p>
<p class="text-xl mb-1">↓ Length of stay</p>
<p class="text-xl mb-1">↓ Doctor paperwork</p>
<p class="text-sm opacity-70 mt-2">Every 0.5 day saved × thousand beds = real money</p>

</div>

<div>

<p class="text-sm uppercase tracking-wider opacity-60 mb-3">Stack</p>
<p class="text-base font-medium mb-1">DeepSeek V3 + Streamlit + DuckDB</p>
<p class="text-sm opacity-70 mb-8">3 hours from zero to demo</p>

<p class="text-sm uppercase tracking-wider opacity-60 mb-3">What's next</p>
<p class="text-lg font-medium mb-2">Cross-stakeholder consistency</p>
<p class="text-sm opacity-70 leading-relaxed">When the doctor updates a discharge plan, the patient's countdown, the family's notification, and the nurse's task list all update — automatically, in sync, across views.</p>

</div>

</div>

<div class="absolute bottom-10 left-12 right-12 text-center">
<p class="text-xl italic opacity-90">
The next chapter of agentic UI isn't smarter agents.<br/>
It's more disciplined agents.
</p>
</div>

<!--
"Buyer is hospitals. Two specific value props:
shorter length of stay, less doctor paperwork.
Both are quantifiable. Both are what a CMO actually buys.

Stack is DeepSeek plus Streamlit plus DuckDB.
Three hours from zero to working demo.

What we're not showing today: cross-stakeholder consistency.
When the doctor updates a plan, every other view updates with it.
That's the next milestone.

The next chapter of agentic UI isn't smarter agents.
It's more disciplined agents — agents that know their boundaries
and coordinate across multiple humans.

That's Prisma."

(60-70 seconds. Two beats of silence at the end.
Don't say "thank you" — kills the ending.
Just say "Happy to take questions.")
-->

---
layout: center
class: text-center
---

<div class="flex flex-col items-center justify-center h-full">

<img src="/prisma-closing.png" class="max-h-[40vh] object-contain mb-8" />

<h1 class="!text-5xl !mb-3">Open to collab</h1>

<p class="text-lg opacity-70 mb-12">If you're building agentic interfaces, healthcare AI, or generative UI — let's talk.</p>

<div class="grid grid-cols-2 gap-x-16 gap-y-3 text-left">

<div class="flex items-center gap-3">
  <span class="text-sm uppercase tracking-wider opacity-50 w-20">Name</span>
  <span class="font-medium">Junyu Zhao (Andy)</span>
</div>

<div class="flex items-center gap-3">
  <span class="text-sm uppercase tracking-wider opacity-50 w-20">Email</span>
  <a href="mailto:zhaojyxs@gmail.com" class="font-medium">zhaojyxs@gmail.com</a>
</div>

<div class="flex items-center gap-3">
  <span class="text-sm uppercase tracking-wider opacity-50 w-20">WhatsApp</span>
  <span class="font-medium">+60919592</span>
</div>

<div class="flex items-center gap-3">
  <span class="text-sm uppercase tracking-wider opacity-50 w-20">X</span>
  <a href="https://x.com/realAndyZhao" class="font-medium">@realAndyZhao</a>
</div>

</div>

</div>

<!--
This stays on screen during Q&A.
Judges and audience can scan it while asking questions.

If anyone asks for a one-line summary, this is it:
"The agent is a prism, not a renderer —
and it knows what it shouldn't refract."
-->
