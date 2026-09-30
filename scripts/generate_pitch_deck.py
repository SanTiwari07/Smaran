"""
Generates a competition-grade 16:9 widescreen Pitch Deck (PPTX) for Smaran.
Uses python-pptx with authentic screenshots, the Red Horizon color system,
and verified metrics from the codebase.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parents[1]
PPT_DIR = ROOT / "ppt"
SHOT_DIR = PPT_DIR / "screenshots"
PPTX_OUT = PPT_DIR / "Smaran_Pitch_Deck.pptx"
ROOT_PPTX_OUT = ROOT / "ppt.pptx"

# Color Palette: Red Horizon
C_VOID = RGBColor(11, 7, 9)          # #0B0709
C_BASALT = RGBColor(21, 13, 16)      # #150D10
C_REGOLITH = RGBColor(31, 19, 22)    # #1F1316
C_BORDER = RGBColor(58, 36, 39)      # #3A2427
C_RUST = RGBColor(193, 68, 14)       # #C1440E
C_RUST_HOT = RGBColor(232, 89, 12)   # #E8590C
C_TELEMETRY = RGBColor(61, 224, 230) # #3DE0E6 (Cyan)
C_NOMINAL = RGBColor(91, 227, 154)   # #5BE39A (Green)
C_CAUTION = RGBColor(255, 176, 32)   # #FFB020 (Amber)
C_CRITICAL = RGBColor(255, 77, 94)   # #FF4D5E (Red)
C_KRYPTA = RGBColor(183, 156, 255)   # #B79CFF (Violet)
C_TEXT_MAIN = RGBColor(245, 241, 234)# #F5F1EA
C_TEXT_MUTED = RGBColor(185, 175, 166)# #B9AFA6
C_TEXT_DIM = RGBColor(124, 113, 107) # #7C716B

FONT_TITLE = "Space Grotesk"
FONT_BODY = "Inter"
FONT_MONO = "JetBrains Mono"


def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_bg(slide):
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_VOID
        bg.line.fill.background()
        return bg

    def add_header(slide, tag_text, title_text, slide_num):
        # Category Tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8), Inches(0.35))
        tf = tag_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = tag_text.upper()
        p.font.name = FONT_MONO
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_RUST_HOT

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(10), Inches(0.6))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = FONT_TITLE
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN

        # Slide Number
        num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.45), Inches(1.0), Inches(0.35))
        tf = num_box.text_frame
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = f"{slide_num:02d} / 08"
        p.alignment = PP_ALIGN.RIGHT
        p.font.name = FONT_MONO
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT_DIM

    def add_card(slide, left, top, width, height, bg_color=C_BASALT, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    # =========================================================================
    # SLIDE 1: COVER
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1)

    # Left Column: Brand & Value Proposition
    # Mission Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.0), Inches(3.2), Inches(0.36))
    badge.fill.solid()
    badge.fill.fore_color.rgb = C_BASALT
    badge.line.color.rgb = C_RUST
    badge.line.width = Pt(1)
    tf = badge.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = "CODE CUBICLE 6.0  |  PROBLEM STATEMENT 3"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_TELEMETRY

    # Main Project Name
    title_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(5.8), Inches(1.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Smaran"
    p.font.name = FONT_TITLE
    p.font.size = Pt(54)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN
    
    # Sub-tag
    p2 = tf.add_paragraph()
    p2.text = "Resilient Edge Vector Memory"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(24)
    p2.font.bold = True
    p2.font.color.rgb = C_RUST_HOT

    # Description Paragraph
    desc_box = s1.shapes.add_textbox(Inches(0.8), Inches(3.4), Inches(5.4), Inches(1.6))
    tf = desc_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = (
        "An offline-first, continuous-intelligence vector memory system built on "
        "Qdrant Edge. Features hardware-isolated Tri-Shard storage, sub-11ms on-device "
        "retrieval, and Themis causal CRDT conflict resolution for communication blackouts."
    )
    p.font.name = FONT_BODY
    p.font.size = Pt(13)
    p.font.color.rgb = C_TEXT_MUTED

    # Highlights Row
    hl_card = add_card(s1, Inches(0.8), Inches(5.2), Inches(5.4), Inches(1.5))
    hl_box = s1.shapes.add_textbox(Inches(1.0), Inches(5.35), Inches(5.0), Inches(1.2))
    tf = hl_box.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "CORE PILLARS IMPLEMENTED:"
    p.font.name = FONT_MONO
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_TELEMETRY

    items = [
        "Tri-Shard Architecture: Krypta (Vault), Hermes (State), Agora (Consensus)",
        "Themis Causal CRDT: Version-vector conflict detection & human resolution",
        "Dual Retrieval: Online Gemini synthesis + offline sub-11ms local hybrid search"
    ]
    for item in items:
        pi = tf.add_paragraph()
        pi.text = f"- {item}"
        pi.font.name = FONT_BODY
        pi.font.size = Pt(10)
        pi.font.color.rgb = C_TEXT_MAIN

    # Right Column: Hero Screenshot
    shot_path = SHOT_DIR / "01_control_center.png"
    if shot_path.exists():
        # Frame Card
        add_card(s1, Inches(6.5), Inches(1.0), Inches(6.1), Inches(4.8), bg_color=C_BASALT, border_color=C_RUST)
        # Screenshot Image
        s1.shapes.add_picture(str(shot_path), Inches(6.6), Inches(1.1), Inches(5.9), Inches(3.8))
        # Caption Box
        cap_box = s1.shapes.add_textbox(Inches(6.6), Inches(5.0), Inches(5.9), Inches(0.7))
        tf = cap_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "LIVE SYSTEM DEMONSTRATION"
        p.font.name = FONT_MONO
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = C_NOMINAL
        p2 = tf.add_paragraph()
        p2.text = "Mission Control Center running live on Qdrant Edge with real-time shard telemetry."
        p2.font.name = FONT_BODY
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_TEXT_MUTED

    # Team Attribution Footer
    team_box = s1.shapes.add_textbox(Inches(6.5), Inches(6.2), Inches(6.1), Inches(0.6))
    tf = team_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TEAM: Sanskar Tiwari  |  Kanishka Salgude  |  Shambhavi Patil"
    p.font.name = FONT_MONO
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DIM

    # =========================================================================
    # SLIDE 2: THE PROBLEM
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_bg(s2)
    add_header(s2, "Operational Failure Modes", "Why Cloud-Tethered AI Assistants Fail at the Edge", 2)

    # 3 Problem Cards
    col_w = Inches(3.64)
    gap = Inches(0.4)
    top_pos = Inches(1.7)
    card_h = Inches(4.8)

    # Card 1: Disconnection Failure
    c1 = add_card(s2, Inches(0.8), top_pos, col_w, card_h)
    tb1 = s2.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.2), col_w - Inches(0.4), card_h - Inches(0.4))
    tf = tb1.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "01 / CLOUD FRAGILITY"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_CRITICAL
    p2 = tf.add_paragraph()
    p2.text = "Total System Paralysis"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT_MAIN
    p3 = tf.add_paragraph()
    p3.text = (
        "\nTraditional RAG assistants rely on cloud API endpoints for every retrieval "
        "and generation step. When field robots, rovers, or emergency teams enter a radio "
        "blackout or network dead zone, memory retrieval drops to zero.\n\n"
        "- 100% cloud round-trip failure\n"
        "- Infinite loading spinners on disconnect\n"
        "- Operators lose access to critical manuals and local logs"
    )
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = C_TEXT_MUTED

    # Card 2: Silent Data Loss
    c2 = add_card(s2, Inches(0.8) + col_w + gap, top_pos, col_w, card_h)
    tb2 = s2.shapes.add_textbox(Inches(1.0) + col_w + gap, top_pos + Inches(0.2), col_w - Inches(0.4), card_h - Inches(0.4))
    tf = tb2.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "02 / SILENT CORRUPTION"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_CAUTION
    p2 = tf.add_paragraph()
    p2.text = "Clock Drift Overwrites"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT_MAIN
    p3 = tf.add_paragraph()
    p3.text = (
        "\nWhen two disconnected edge devices independently update operational state "
        "(e.g., Rover A sets valve torque at 4 PM, Rover B changes spec at 5 PM), typical "
        "databases resolve the conflict using Last-Write-Wins (LWW).\n\n"
        "- Clock skew destroys causal order\n"
        "- Critical safety decisions silently erased\n"
        "- No record that a conflict ever occurred"
    )
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = C_TEXT_MUTED

    # Card 3: Privacy & Bandwidth
    c3 = add_card(s2, Inches(0.8) + (col_w + gap) * 2, top_pos, col_w, card_h)
    tb3 = s2.shapes.add_textbox(Inches(1.0) + (col_w + gap) * 2, top_pos + Inches(0.2), col_w - Inches(0.4), card_h - Inches(0.4))
    tf = tb3.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "03 / DATA LEAKAGE"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_KRYPTA
    p2 = tf.add_paragraph()
    p2.text = "Unconstrained Cloud Sync"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT_MAIN
    p3 = tf.add_paragraph()
    p3.text = (
        "\nExisting architectures treat all memories identically. Sensitive personal "
        "identifiers (PII), device passwords, and tactical credentials leak into central "
        "cloud vector indexes and vendor prompt logs.\n\n"
        "- Zero cryptographic hardware boundary\n"
        "- Massive bandwidth waste syncing high-frequency state\n"
        "- Regulatory non-compliance on private user notes"
    )
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 3: OUR SOLUTION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_bg(s3)
    add_header(s3, "Architecture Innovation", "Smaran: Tri-Shard Resilience with Causal Consensus", 3)

    # Left Column: Architectural Pillars
    left_w = Inches(5.6)
    add_card(s3, Inches(0.8), Inches(1.6), left_w, Inches(5.1))
    stb = s3.shapes.add_textbox(Inches(1.1), Inches(1.8), left_w - Inches(0.6), Inches(4.7))
    tf = stb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "TRI-SHARD HARDWARE SEGREGATION"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_TELEMETRY

    shards = [
        ("KRYPTA (Private Vault)", C_KRYPTA, "AES-GCM-256 encrypted local partition. Strict cryptographic gate: memories NEVER leave the physical device. Cloud LLM calls are blocked if Krypta context is present."),
        ("HERMES (Operational State)", C_CAUTION, "High-frequency operational state & sensor telemetry. Local-first, ephemeral, synced to cloud only upon alert threshold or manual push. Saves 85% wire bandwidth."),
        ("AGORA (Fleet Consensus)", C_NOMINAL, "Shared collaborative knowledge base. Bidirectionally synced with central Qdrant server using Themis causal CRDTs and cryptographic provenance hashes.")
    ]

    for title, col, desc in shards:
        p_t = tf.add_paragraph()
        p_t.text = f"\n{title}"
        p_t.font.name = FONT_TITLE
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = C_TEXT_MUTED

    # Right Column: Memory Explorer Screenshot
    shot_path = SHOT_DIR / "04_memory_explorer.png"
    if shot_path.exists():
        add_card(s3, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.1), bg_color=C_BASALT, border_color=C_BORDER)
        s3.shapes.add_picture(str(shot_path), Inches(6.95), Inches(1.75), Inches(5.4), Inches(3.9))
        
        cap_box = s3.shapes.add_textbox(Inches(6.95), Inches(5.8), Inches(5.4), Inches(0.8))
        tf = cap_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "AUTHENTIC UI: MEMORY EXPLORER"
        p.font.name = FONT_MONO
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = C_NOMINAL
        p2 = tf.add_paragraph()
        p2.text = "Real-time inspection of encrypted Krypta, operational Hermes, and synced Agora shards."
        p2.font.name = FONT_BODY
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 4: HOW IT WORKS (TECHNICAL ARCHITECTURE)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_bg(s4)
    add_header(s4, "System Engineering", "Edge-Native Pipeline: From Ingestion to Causal Sync", 4)

    # 4 Flow Steps
    step_w = Inches(2.7)
    gap_s = Inches(0.3)
    top_s = Inches(1.7)
    card_hs = Inches(5.0)

    steps = [
        ("01 / INGESTION", "Argus Decomposition", C_TELEMETRY, [
            "Operator input or sensor stream parsed into atomic facts, decisions, and constraints.",
            "Deterministic PII regex & entity scanner runs BEFORE any model ingestion.",
            "Decisions carry residency, criticality, confidence, author, and rationale metadata."
        ]),
        ("02 / ENCRYPTION", "Tri-Shard Routing", C_KRYPTA, [
            "Classified residency determines physical partition placement.",
            "Krypta shard encrypted with device-unique AES-GCM-256 key.",
            "Zero plaintext persistence of credentials or private operator logs on disk."
        ]),
        ("03 / LOCAL RETRIEVAL", "Sub-11ms Edge Recall", C_RUST_HOT, [
            "Embedded vector retrieval using qdrant-edge-py and bge-small-en-v1.5-onnx-Q.",
            "Hybrid dense + BM25 reciprocal rank fusion (RRF) on local SQLite WAL.",
            "Offline task agent autonomously executes reminder queues and local outbox."
        ]),
        ("04 / CONSENSUS", "Themis Causal CRDT", C_NOMINAL, [
            "Logical Lamport clocks & explicit Version Vectors {A:v_A, B:v_B}.",
            "Reconnection triggers causal comparison: flags concurrent forks as contested.",
            "Human supervisor resolves conflicts; dominating vector synchronizes fleet."
        ])
    ]

    for i, (tag, stitle, color, bullets) in enumerate(steps):
        x = Inches(0.8) + i * (step_w + gap_s)
        add_card(s4, x, top_s, step_w, card_hs)
        
        tb = s4.shapes.add_textbox(x + Inches(0.2), top_s + Inches(0.2), step_w - Inches(0.4), card_hs - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_MONO
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = color
        
        p2 = tf.add_paragraph()
        p2.text = stitle
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(14)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN
        
        for b in bullets:
            pb = tf.add_paragraph()
            pb.text = f"\n- {b}"
            pb.font.name = FONT_BODY
            pb.font.size = Pt(10)
            pb.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 5: CORE PRODUCT EXPERIENCE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_bg(s5)
    add_header(s5, "User Experience & Companion", "Natural Interaction with Provenance & Offline Parity", 5)

    # Left: Online Grounded Synthesis
    shot_online = SHOT_DIR / "02_companion_grounded.png"
    add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    if shot_online.exists():
        s5.shapes.add_picture(str(shot_online), Inches(0.95), Inches(1.75), Inches(5.3), Inches(3.6))
    
    tb_on = s5.shapes.add_textbox(Inches(0.95), Inches(5.45), Inches(5.3), Inches(1.1))
    tf = tb_on.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "MODE A: ONLINE GROUNDED SYNTHESIS (GEMINI)"
    p.font.name = FONT_MONO
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_TELEMETRY
    p2 = tf.add_paragraph()
    p2.text = "Cites exact cryptographic source hashes [1]. Operators can click 'Why did Smaran say this?' to inspect the retrieved memory slice, shard type, and confidence score."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10)
    p2.font.color.rgb = C_TEXT_MUTED

    # Right: Offline Local Recall
    shot_offline = SHOT_DIR / "03_companion_offline.png"
    add_card(s5, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.1))
    if shot_offline.exists():
        s5.shapes.add_picture(str(shot_offline), Inches(7.05), Inches(1.75), Inches(5.3), Inches(3.6))
    
    tb_off = s5.shapes.add_textbox(Inches(7.05), Inches(5.45), Inches(5.3), Inches(1.1))
    tf = tb_off.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "MODE B: SURFACE MODE (OFFLINE AUTONOMY)"
    p.font.name = FONT_MONO
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL
    p2 = tf.add_paragraph()
    p2.text = "Zero cloud connectivity required. Sub-11ms local retrieval via ONNX embeddings. Autonomous agent queues maintenance actions and reminders into local outbox."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10)
    p2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 6: THE DIFFERENTIATOR (THEMIS CRDT)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_bg(s6)
    add_header(s6, "Core Differentiator", "Themis Engine: Eliminating Silent Overwrites via Causal CRDTs", 6)

    # Left: Explanation & Math
    left_w = Inches(5.4)
    add_card(s6, Inches(0.8), Inches(1.6), left_w, Inches(5.1))
    tb_th = s6.shapes.add_textbox(Inches(1.05), Inches(1.8), left_w - Inches(0.5), Inches(4.7))
    tf = tb_th.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "MATHEMATICALLY GUARANTEED INTEGRITY"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_CAUTION

    diff_points = [
        ("The Distributed Dilemma", "While disconnected, Rover A schedules Array Calibration for 16:00 UTC (Version Vector {A:1, B:0}). Concurrently, Rover B updates spec to 17:00 UTC ({A:0, B:1}). Traditional LWW databases silently overwrite Rover A."),
        ("Vector Clock Comparison", "Themis compares vectors upon reconnection. Since neither vector dominates (V_A not <= V_B and V_B not <= V_A), the state is flagged as CONTESTED rather than guessed."),
        ("Human-in-the-Loop Resolution", "The mission operator selects the authoritative version with a single click. Themis produces a dominating causal vector {A:2, B:2} that deterministically converges across the entire fleet.")
    ]

    for title, desc in diff_points:
        pt = tf.add_paragraph()
        pt.text = f"\n{title}"
        pt.font.name = FONT_TITLE
        pt.font.size = Pt(13)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_MAIN

        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.name = FONT_BODY
        pd.font.size = Pt(10)
        pd.font.color.rgb = C_TEXT_MUTED

    # Right: Conflicts UI Screenshot
    shot_conf = SHOT_DIR / "05_conflicts_themis.png"
    add_card(s6, Inches(6.6), Inches(1.6), Inches(5.9), Inches(5.1), bg_color=C_BASALT, border_color=C_BORDER)
    if shot_conf.exists():
        s6.shapes.add_picture(str(shot_conf), Inches(6.75), Inches(1.75), Inches(5.6), Inches(3.9))
    
    tb_c_cap = s6.shapes.add_textbox(Inches(6.75), Inches(5.8), Inches(5.6), Inches(0.8))
    tf = tb_c_cap.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "AUTHENTIC UI: CONFLICT RESOLUTION CONSOLE"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL
    p2 = tf.add_paragraph()
    p2.text = "Side-by-side vector inspection with one-click causal reconciliation."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10)
    p2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 7: VERIFIED BENCHMARKS ("PROVE IT")
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_bg(s7)
    add_header(s7, "Mathematical Proofs & Metrics", "Verified Benchmarks: Sub-9ms Recall, 0 Leaks, 100% Convergence", 7)

    # 4 Metric Cards Across Top
    m_w = Inches(2.7)
    m_gap = Inches(0.3)
    m_top = Inches(1.6)
    m_h = Inches(1.5)

    metrics = [
        ("SUB-9ms", "Edge Hybrid Search", C_TELEMETRY, "Local ONNX + SQLite RRF latency"),
        ("0 LEAKS", "Hardware Isolation", C_KRYPTA, "100% boundary on Krypta vault"),
        ("100%", "Causal Convergence", C_NOMINAL, "Zero silent data overwrites"),
        ("85.3%", "Bandwidth Savings", C_RUST_HOT, "Selective wire synchronization")
    ]

    for i, (val, label, col, sub) in enumerate(metrics):
        x = Inches(0.8) + i * (m_w + m_gap)
        add_card(s7, x, m_top, m_w, m_h)
        tb = s7.shapes.add_textbox(x + Inches(0.15), m_top + Inches(0.15), m_w - Inches(0.3), m_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = val
        p.font.name = FONT_TITLE
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = col
        
        p2 = tf.add_paragraph()
        p2.text = label
        p2.font.name = FONT_MONO
        p2.font.size = Pt(10)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN

        p3 = tf.add_paragraph()
        p3.text = sub
        p3.font.name = FONT_BODY
        p3.font.size = Pt(9)
        p3.font.color.rgb = C_TEXT_MUTED

    # Bottom Area: Live Benchmark Suite Screenshot
    shot_prove = SHOT_DIR / "06_prove_it_benchmarks.png"
    add_card(s7, Inches(0.8), Inches(3.3), Inches(11.7), Inches(3.6), bg_color=C_BASALT, border_color=C_BORDER)
    if shot_prove.exists():
        s7.shapes.add_picture(str(shot_prove), Inches(0.95), Inches(3.45), Inches(7.5), Inches(3.3))
    
    tb_pr = s7.shapes.add_textbox(Inches(8.65), Inches(3.45), Inches(3.6), Inches(3.3))
    tf = tb_pr.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "REPRODUCIBLE TEST SUITE"
    p.font.name = FONT_MONO
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL
    p2 = tf.add_paragraph()
    p2.text = (
        "\nJudges do not need to take our word for it: the 'Prove It' console runs live "
        "reproducible mathematical proofs directly from the browser:\n\n"
        "1. Latency Proof: Measures dense embedding + BM25 RRF across golden queries.\n\n"
        "2. Privacy Leak Test: Attempts to force private phone notes into cloud LLM prompts; "
        "cryptographic gate verifies 0 bytes sent.\n\n"
        "3. Convergence Test: Simulates 100 concurrent partition edits; verifies 100% causal resolution."
    )
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10)
    p2.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 8: IMPACT & ROADMAP
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_bg(s8)
    add_header(s8, "Production Reality & Future Scope", "From Code Cubicle 6.0 Prototype to Field Deployment", 8)

    # 3 Evolution Columns
    c_w = Inches(3.64)
    c_gap = Inches(0.4)
    c_top = Inches(1.7)
    c_h = Inches(4.4)

    phases = [
        ("PHASE 01 / BUILT TODAY", "Hackathon Delivery", C_NOMINAL, [
            "Fully functional Qdrant Edge device replica.",
            "Tri-Shard storage with AES-GCM-256 encryption.",
            "Sub-11ms dense + BM25 local hybrid search.",
            "Grounded Google Gemini online RAG with provenance citations.",
            "Themis causal CRDT conflict resolution engine.",
            "Prove It browser-executable benchmark verification suite."
        ]),
        ("PHASE 02 / DEPLOYMENT TARGETS", "Operational Horizons", C_TELEMETRY, [
            "Field Robotics: Autonomous rovers and drones operating in radio dead zones.",
            "Disaster Response: First-responder squads in collapsed cell network environments.",
            "Underground & Defense: Subterranean infrastructure, mining, and secure naval fleets.",
            "Remote Industrial: Offshore energy rigs with high-latency satellite uplinks."
        ]),
        ("PHASE 03 / FUTURE EXPANSION", "Next Milestones", C_RUST_HOT, [
            "Peer-to-Peer Mesh Gossip: Direct device-to-device vector exchange without gateway.",
            "Hardware Enclave Integration: TPM and Apple Secure Enclave key sealing.",
            "Dynamic Vector Quantization: On-the-fly scalar quantization to fit low-RAM microcontrollers.",
            "Cross-Modal Edge Embeddings: Audio and sensor waveform vector indexing."
        ])
    ]

    for i, (tag, ptitle, col, items) in enumerate(phases):
        x = Inches(0.8) + i * (c_w + c_gap)
        add_card(s8, x, c_top, c_w, c_h)
        tb = s8.shapes.add_textbox(x + Inches(0.2), c_top + Inches(0.2), c_w - Inches(0.4), c_h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_MONO
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col
        
        p2 = tf.add_paragraph()
        p2.text = ptitle
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(15)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN
        
        for item in items:
            pi = tf.add_paragraph()
            pi.text = f"\n- {item}"
            pi.font.name = FONT_BODY
            pi.font.size = Pt(10)
            pi.font.color.rgb = C_TEXT_MUTED

    # Bottom Closing Banner
    bot_card = add_card(s8, Inches(0.8), Inches(6.3), Inches(11.7), Inches(0.8), bg_color=C_BASALT, border_color=C_RUST)
    bot_tb = s8.shapes.add_textbox(Inches(1.0), Inches(6.4), Inches(11.3), Inches(0.6))
    tf = bot_tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "SMARAN: Continuous vector intelligence when the network is gone."
    p.font.name = FONT_TITLE
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_RUST_HOT
    p2 = tf.add_paragraph()
    p2.text = "Built by Sanskar Tiwari, Kanishka Salgude, and Shambhavi Patil for Code Cubicle 6.0."
    p2.font.name = FONT_MONO
    p2.font.size = Pt(10)
    p2.font.color.rgb = C_TEXT_MUTED

    # Save outputs
    PPT_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPTX_OUT))
    prs.save(str(ROOT_PPTX_OUT))
    print(f"PPTX successfully created at:\n  - {PPTX_OUT}\n  - {ROOT_PPTX_OUT}")


if __name__ == "__main__":
    create_deck()
