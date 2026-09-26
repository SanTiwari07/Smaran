# 01 — Hackathon Overview: Code Cubicle 6.0

← [Master index](00_MASTER_RESEARCH_INDEX.md) · Next: [02 PS3 analysis](02_PROBLEM_STATEMENT_3_ANALYSIS.md)

Research date: **26 Sep 2026**. Labels used throughout this knowledge base:

- **FACT**: read directly on an official source (HackCulture event page, the official problem-statement PDF, or the organizer's own site).
- **SOURCE-REPORTED CLAIM**: stated by a secondary source (Devpost mirror, Unstop, a listing site, press).
- **ANALYST INFERENCE**: our reading of the evidence. It is not a fact.
- **RECOMMENDATION**: what we should do.
- **NOT FOUND — REQUIRES VERIFICATION**: searched for and not found.

---

## 1. Identity

| Field | Value | Label | Source |
|---|---|---|---|
| Name | Code Cubicle 6.0 | FACT | [S1] |
| Tagline | "Where Builders ship from the Office Cubicle" | FACT | [S1] |
| Organizer | **Geek Room** (listed "By Geek Room") | FACT | [S1] |
| Platform | HackCulture (hackculture.io) | FACT | [S1] |
| Theme umbrella | "AI-Powered Intelligence for the Real World" (the label on all three themes) | FACT | [S1] |
| Mode | Hybrid: online elimination, then an offline final | FACT | [S1] |
| Final venue | **Paytm office, Noida**: One Skymark, Floors 6–22, Tower-D, Plot H-10 B, Sector 98, Noida, UP 201304 | FACT | [S1] |
| Registrations | 3,700 (counter on the page) | FACT (platform counter) | [S1] |
| Page impressions | 26,000 | FACT (platform counter) | [S1] |
| Contact | Manas Chopra, Co-Founder, Geek Room: `team.geekroom@gmail.com` | FACT | [S1] |
| Other organizer contact | `community@geekroom.in` | FACT (organizer site) | [S4] |

## 2. Timeline

| Stage | Official dates (HackCulture) | Mode | Notes | Label |
|---|---|---|---|---|
| Event span | **28 Aug 2026 – 11 Oct 2026** | — | Header of the event page | FACT [S1] |
| Registration | 29 Aug 2026 09:00 → **20 Sep 2026 22:09** | Online | Now shows "Registration Closed" | FACT [S1] |
| Team formation | 29 Aug 2026 09:00 → 20 Sep 2026 23:59 | Online | "Approval required" | FACT [S1] |
| **Project Submission (elimination round)** | **21 Sep 2026 00:00 → 30 Sep 2026 23:59** | Online | Marked **Live** on 26 Sep. See the quote below. | FACT [S1] |
| **Final Round** | **11 Oct 2026, 09:00 → 18:00** | **Offline**, Paytm Noida | "Top 3 winners will be selected." | FACT [S1] |

Exact wording of the submission stage [S1]:

> "Teams will get selected based on Github and Linkedin profiles that will present in this elimination round to compete for the final round. Around 15-20 teams will be selected for the final round."

FAQ [S1]:

> "Teams will be selected based on the overall GitHub and LinkedIn profiles of the team members."
> "The Final Round will be held offline at Paytm Office, Noida on 11 October 2026."

### ⚠ Date conflict to resolve

| Source | What it says |
|---|---|
| HackCulture event page [S1] (**most authoritative**, since it is the registration platform) | Submission 21–30 Sep; final 11 Oct |
| Official problem-statement PDF footer [S2] | "**3 OCT ONLINE · 11 OCT OFFLINE**" |
| Devpost mirror page [S3] | "The hackathon will take place from 3 October to 11 October." Team size 2–4. Lists "This hackathon has ended" (a Devpost state artefact). |

**ANALYST INFERENCE:** "3 Oct online" most likely refers to an online presentation or evaluation step for the elimination round. The HackCulture stage text says selected teams "will present in this elimination round". The 30 Sep 23:59 deadline is therefore the safe hard deadline for having the repo and submission complete. Presentation readiness is needed by 3 Oct.

**RECOMMENDATION:** Treat **30 Sep 23:59 IST** as the code-and-submission freeze. Be ready to pitch online from **1 Oct**. Email `team.geekroom@gmail.com` to confirm whether there is an online pitch on 3 Oct and its format.

## 3. Eligibility and teams (FACT [S1])

- Students, developers, engineers, AI builders and working professionals. There are no academic or professional prerequisites.
- Individuals or teams of **1–4**. Devpost says 2–4 [S3]; HackCulture is authoritative.
- One team per participant.
- Selected teams **must attend the final offline at Paytm, Noida**.

## 4. Themes and problem statements

All three share the theme label "AI-Powered Intelligence for the Real World" [S1]. Numbering follows the official PDF [S2].

| # | Title | Sponsor badge on the PDF | One-line challenge (official) |
|---|---|---|---|
| PS1 | AI-Powered Data Intelligence Platform | none shown | Natural-language request → dynamically built and executed data-collection workflow → validated, source-backed dataset with a dashboard |
| PS2 | AI-Powered Impact & Sustainability Media Platform | **Cloudinary** ("PROBLEM STATEMENT 02 · CLOUDINARY") | Media intelligence on Cloudinary for NGO/government field evidence |
| **PS3** | **AI-Powered Edge Memory & Intelligence Platform** | **Qdrant** (Qdrant logo next to "PROBLEM STATEMENT 03" on the hosted PDF) | Offline-first edge AI on **Qdrant Edge** with intelligent edge↔cloud sync |

The full PS3 text is in [02](02_PROBLEM_STATEMENT_3_ANALYSIS.md).

**Verification note:** the local copy `docs/reference/problem-statements.pdf` (3 pages) and the hosted PDF linked from "View Detailed Explanation" (1 page, PS3 only, Qdrant-branded) differ in file hash. We rendered both, and the **PS3 wording is identical**.

## 5. Prizes (FACT [S1] unless labelled)

The page headline reads "$14K prize pool with ₹1.9L in cash, $11K of Credits and $1K of other prizes".

| Prize | Amount | Count | Sponsor | Who can win |
|---|---|---|---|---|
| Cloudinary Challenge 1st | ₹1,20,000 | 1 | Cloudinary | "best overall project for Cloudinary Challenge", i.e. PS2 |
| Cloudinary Challenge 2nd | ₹40,000 | 1 | Cloudinary | PS2 |
| **CC 6.0 General 1st** | **₹12,000** | 1 | Geek Room | "general problem statement winners" |
| **CC 6.0 General 2nd** | **₹10,000** | 1 | Geek Room | general |
| **CC 6.0 General 3rd** | **₹8,000** | 1 | Geek Room | general |
| n8n Cloud Pro licenses | $60 credits | 100 | n8n | — |
| Omnidimension Voice AI credits | $50 credits | 100 | Omnidimension | — |
| Logitech wireless mouse | $100 | 5 | Logitech | "Top participants" |
| Exclusive goodies | $50 | 10 | Geek Room | — |
| Certificates | — | all | Geek Room | all participants |
| Villa stay in Goa for the winning team | — | 1 | (Wayzyy is the travel partner) | SOURCE-REPORTED CLAIM [S3][S5], also a Geek Room LinkedIn post seen in search snippets |

**ANALYST INFERENCE:** PS3 has **no dedicated sponsor cash prize**. A PS3 team competes for the **General 1st–3rd** prizes and the "Top 3" final ranking. Qdrant's influence is likely to show up as judging input and credibility, not as a prize. There is no Qdrant prize line on the page.

## 6. Partners and sponsors (FACT [S1])

| Partner | Role on page |
|---|---|
| Logitech | Experience Partner |
| Wayzyy | Travel Partner |
| **Qdrant** | **Technology Partner** (and PS3 owner) |
| Pathway | Technology Partner |
| n8n | License Partner |
| Cloudinary | Track Sponsor (PS2) |
| Eventopia | Media Partner |
| Omnidimension | Credits prize only; not in the partner grid |
| Paytm | Final venue host; not in the partner grid |

Details are in [05](05_SPONSOR_AND_PARTNER_RESEARCH.md).

## 7. Rules (FACT [S1], condensed but faithful)

1. Individual or team, at most 4. Registration information must be accurate.
2. One team per participant.
3. **Projects must be built by the team; original work.** Open-source tools, libraries, APIs and AI tools are allowed. **Third-party work must be credited.**
4. **Selection is based on the team's overall profile, including GitHub and LinkedIn.** The organizers' decision is final.
5. **The final is offline at Paytm Noida.** Teams **must present and demonstrate** the project. The jury decides "based on the evaluation criteria".
6. Code of conduct: cheating, plagiarism or harassment means disqualification.
7. The organizers may change the schedule or rules. Participants must track announcements.

Devpost mirror rules [S3] add: "Any use of third-party assets, APIs, or datasets should be properly acknowledged".

## 8. Deliverables (SOURCE-REPORTED CLAIM, Devpost mirror [S3])

- A working project developed during the hackathon
- A clear project description: problem, solution, key features
- A demo or working prototype
- Source code / repository link
- A short presentation or demo explaining the project and its implementation

The HackCulture page does not list deliverables beyond "present and demonstrate". **NOT FOUND — REQUIRES VERIFICATION:** the exact submission-form fields on HackCulture (video? deck? repo?). Check the HackCulture dashboard.

## 9. Judging criteria

| Item | Status |
|---|---|
| Elimination-round selection | **FACT:** GitHub + LinkedIn profiles of team members [S1] |
| Final-round criteria | **NOT FOUND — REQUIRES VERIFICATION.** The HackCulture page says only "based on the evaluation criteria". |
| Devpost mirror | SOURCE-REPORTED, **truncated on the source itself**: "Innovation & Creativity – Uniqueness and originality of the idea; Technical Implementation – Quality, functionality, and technical…" [S3] |
| Judges | **NOT FOUND.** Devpost lists "NA". Devpost mentions "judging by industry professionals". |
| Mentoring | SOURCE-REPORTED: "mentorship" and "hiring opportunities" [S3][S5]. No mentor schedule was found. |

Our strategic interpretation of the likely criteria is in [15](15_JUDGING_STRATEGY.md).

## 10. Hidden and secondary requirements (ANALYST INFERENCE, evidence-based)

1. **Your public GitHub is the application.** Selection reads GitHub and LinkedIn profiles, so the repo's README, commit history, tests, CI badge and demo GIF are effectively the first-round pitch.
2. **The PS3 wording names specific technologies:** "Qdrant Edge", "hybrid search", "Qdrant Server". Using `qdrant-client` local mode instead of the Qdrant Edge library, or skipping a real Qdrant Server, is a literal compliance gap. See [06](06_COMPETITOR_ANALYSIS.md) on AegisEdge.
3. **"Rather than simply running a local vector database"** is an explicit anti-requirement in PS3. Judges are told to penalise thin wrappers.
4. **The previous edition's format included an on-site build.** Code Cubicle 5.0: a 5-minute online pitch plus 2-minute Q&A, then an **8-hour on-site hackathon** for the top 15, presenting live to the jury (SOURCE-REPORTED [S6]). The CC 6.0 final runs 09:00–18:00, a nine-hour window. Be prepared for an on-site extension task or a feature request.
5. **Crediting.** The rules require crediting third-party work. Smaran's README must list Qdrant Edge, FastEmbed, the models used, scikit-learn and so on.

## Sources

| ID | Source | URL | Accessed | Info obtained | Reliability |
|---|---|---|---|---|---|
| S1 | HackCulture: Code Cubicle 6.0 event page (rendered in browser; FAQ expanded) | https://hackculture.io/hackathons/code-cubicle-6-0 | 2026-09-26 | Dates, stages, rules, prizes, partners, FAQ, contact, venue | HIGH |
| S2 | Official problem-statement PDF (hosted, 1 page, Qdrant-branded) + local 3-page copy | https://hackcultureplatform.blob.core.windows.net/event-assets/hackathons/6a9084220579dffec28137de/problem_explanation_piovxkhlbtb.pdf ; `docs/reference/problem-statements.pdf` | 2026-09-26 | Exact PS1–PS3 text, sponsor badges, "3 OCT ONLINE · 11 OCT OFFLINE" | HIGH |
| S3 | Devpost mirror: Code Cubicle 6.0 | https://code-cubicle-6-0.devpost.com/ (+ /rules) | 2026-09-26 | Requirements, villa prize, 3–11 Oct window, truncated judging criteria | MEDIUM |
| S4 | Geek Room official site, About | https://geekroom.framer.website/about-us | 2026-09-26 | Founders, milestones, contact | HIGH (self-published) |
| S5 | SheKunj listing (search snippet) | https://www.shekunj.com/hackathons/code-cubicle-6-0 | 2026-09-26 | Villa in Goa, hiring, mentorship | LOW |
| S6 | Unstop: Code Cubicle 5.0 | https://unstop.com/hackathons/code-cubicle-5-geek-room-1537583 | 2026-09-26 | Past format (online pitch + 8-hour on-site build), organizer blurbs | MEDIUM |
