"""
Generates a competition-grade 16:9 widescreen Pitch Deck (PPTX) for Smaran.
Matches the Light Technical Editorial design system:
- Palette: Warm linen background (#F7F5F2), ink black typography (#171313), Mars rust accent (#E85A18).
- Typography: Clean sans-serif and monospace hierarchy.
- Layout: Asymmetric, editorial compositions per slide (no repetitive card grids).
- Verified codebase screenshots and authentic benchmarks.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parents[1]
PPT_DIR = ROOT / "ppt"
SHOT_DIR = PPT_DIR / "screenshots"
PPTX_OUT = PPT_DIR / "Smaran_Pitch_Deck.pptx"
ROOT_PPTX_OUT = ROOT / "ppt.pptx"

# Color Palette: Premium Technical Editorial
C_BG = RGBColor(247, 245, 242)          # #F7F5F2 warm linen
C_SURFACE = RGBColor(255, 255, 255)     # #FFFFFF pure white
C_TEXT = RGBColor(23, 19, 19)           # #171313 rich ink black
C_TEXT_MUTED = RGBColor(102, 96, 91)    # #66605B editorial charcoal
C_TEXT_LIGHT = RGBColor(143, 135, 129)  # #8F8781 soft caption
C_BORDER = RGBColor(229, 224, 216)      # #E5E0D8 hairline rule
C_ACCENT = RGBColor(232, 90, 24)        # #E85A18 Mars rust
C_ACCENT_DEEP = RGBColor(185, 71, 24)   # #B94718 deep terra cotta
C_NOMINAL = RGBColor(27, 127, 75)       # #1B7F4B forest green
C_CRITICAL = RGBColor(201, 59, 43)      # #C93B2B editorial crimson
C_KRYPTA = RGBColor(107, 75, 194)       # #6B4BC2 krypta violet

FONT_TITLE = "Helvetica Neue"
FONT_BODY = "Arial"
FONT_MONO = "Consolas"


def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, tracker_text, headline_text, subhead_text=None, slide_num=None):
        # Tracker Tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8.0), Inches(0.3))
        tf = tag_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = tracker_text.upper()
        p.font.name = FONT_MONO
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = C_ACCENT

        # Headline
        head_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(10.5), Inches(0.55))
        tf = head_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = headline_text
        p.font.name = FONT_TITLE
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = C_TEXT

        # Subhead if present
        if subhead_text:
            sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.32), Inches(11.5), Inches(0.35))
            tf = sub_box.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = subhead_text
            p.font.name = FONT_BODY
            p.font.size = Pt(11.5)
            p.font.color.rgb = C_TEXT_MUTED

        # Slide Number
        if slide_num:
            num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.45), Inches(1.0), Inches(0.3))
            tf = num_box.text_frame
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = f"{slide_num:02d} / 08"
            p.alignment = PP_ALIGN.RIGHT
            p.font.name = FONT_MONO
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_TEXT_LIGHT

    def add_line(slide, left, top, width, height, color=C_BORDER):
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
        line.fill.solid()
        line.fill.fore_color.rgb = color
        line.line.fill.background()
        return line

    # =========================================================================
    # SLIDE 1: COVER
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    add_bg(slide1)

    # Top tracker
    t_box = slide1.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(5.5), Inches(0.3))
    tf = t_box.text_frame
    p = tf.paragraphs[0]
    p.text = "SMARAN // RESILIENT VECTOR MEMORY"
    p.font.name = FONT_MONO
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    # Main Brand & Title
    title_box = slide1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(5.8), Inches(2.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Smaran"
    p.font.name = FONT_TITLE
    p.font.size = Pt(46)
    p.font.bold = True
    p.font.color.rgb = C_TEXT

    p2 = tf.add_paragraph()
    p2.text = "Resilient Edge Vector Memory for Autonomous and Intermittent Systems."
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(20)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(12)

    # Description
    desc_box = slide1.shapes.add_textbox(Inches(0.8), Inches(3.6), Inches(5.5), Inches(1.2))
    tf = desc_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = (
        "Zero-cloud local vector search with cryptographic tri-shard isolation "
        "and Themis causal CRDT consensus. Memory stays alive on Mars, in mine shafts, "
        "and through catastrophic network blackouts."
    )
    p.font.name = FONT_BODY
    p.font.size = Pt(12)
    p.font.color.rgb = C_TEXT_MUTED

    # Divider line
    add_line(slide1, Inches(0.8), Inches(5.1), Inches(5.5), Inches(0.015), C_BORDER)

    # Metadata Row (3 cols)
    meta_box = slide1.shapes.add_textbox(Inches(0.8), Inches(5.3), Inches(5.5), Inches(1.5))
    tf = meta_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "CHALLENGE"
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_LIGHT

    p2 = tf.add_paragraph()
    p2.text = "Code Cubicle 6.0 &middot; Problem Statement 3"
    p2.font.name = FONT_BODY
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT

    p3 = tf.add_paragraph()
    p3.text = "VECTOR ENGINE"
    p3.font.name = FONT_MONO
    p3.font.size = Pt(8.5)
    p3.font.bold = True
    p3.font.color.rgb = C_TEXT_LIGHT
    p3.space_before = Pt(8)

    p4 = tf.add_paragraph()
    p4.text = "Qdrant Edge Embedded + ONNX Hybrid Recall"
    p4.font.name = FONT_BODY
    p4.font.size = Pt(11)
    p4.font.bold = True
    p4.font.color.rgb = C_TEXT

    p5 = tf.add_paragraph()
    p5.text = "ENGINEERING TEAM"
    p5.font.name = FONT_MONO
    p5.font.size = Pt(8.5)
    p5.font.bold = True
    p5.font.color.rgb = C_TEXT_LIGHT
    p5.space_before = Pt(8)

    p6 = tf.add_paragraph()
    p6.text = "Sanskar Tiwari &middot; Kanishka Salgude &middot; Shambhavi Patil"
    p6.font.name = FONT_BODY
    p6.font.size = Pt(11)
    p6.font.bold = True
    p6.font.color.rgb = C_TEXT

    # Right Hero Image
    shot1 = SHOT_DIR / "01_control_center.png"
    if shot1.exists():
        slide1.shapes.add_picture(str(shot1), Inches(6.8), Inches(1.1), width=Inches(5.7))

    # Caption
    c_box = slide1.shapes.add_textbox(Inches(6.8), Inches(5.9), Inches(5.7), Inches(0.4))
    tf = c_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "FIGURE 1.0 — Smaran Control Center managing real-time edge telemetry and twin-rover synchronization."
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 2: THE PROBLEM
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_bg(slide2)
    add_header(
        slide2,
        "OPERATIONAL FAILURE MODES",
        "When the network disappears, AI memory disappears with it.",
        "Conventional vector architectures rely on unbroken cloud connectivity. Under communication blackouts, existing systems suffer catastrophic failure.",
        2
    )

    # Box 1: Conventional Cloud RAG
    box1 = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(2.3))
    box1.fill.solid()
    box1.fill.fore_color.rgb = C_SURFACE
    box1.line.color.rgb = C_BORDER
    box1.line.width = Pt(1)
    add_line(slide2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(0.04), C_CRITICAL)

    tf1 = box1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = Inches(0.2)
    p = tf1.paragraphs[0]
    p.text = "CONVENTIONAL CLOUD RAG                                      FRAGILE DEPENDENCY"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_CRITICAL

    p2 = tf1.add_paragraph()
    p2.text = "Total Cloud Paralysis"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(6)

    p3 = tf1.add_paragraph()
    p3.text = "User prompts pass through remote vector APIs over continuous broadband. When connectivity drops, prompt pipelines freeze, memory writes fail, and local agents become completely unresponsive."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(10.5)
    p3.font.color.rgb = C_TEXT_MUTED
    p3.space_before = Pt(4)

    p4 = tf1.add_paragraph()
    p4.text = "FLOW: Prompt -> Cloud Vector DB -> Cloud LLM\nBLACKOUT: Connection Refused -> 0 KB local memory -> SYSTEM HALT"
    p4.font.name = FONT_MONO
    p4.font.size = Pt(8.5)
    p4.font.color.rgb = C_CRITICAL
    p4.space_before = Pt(6)

    # Box 2: Naive Offline Replication
    box2 = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.9), Inches(1.8), Inches(5.6), Inches(2.3))
    box2.fill.solid()
    box2.fill.fore_color.rgb = C_SURFACE
    box2.line.color.rgb = C_BORDER
    box2.line.width = Pt(1)
    add_line(slide2, Inches(6.9), Inches(1.8), Inches(5.6), Inches(0.04), C_ACCENT)

    tf2 = box2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = tf2.margin_top = tf2.margin_bottom = Inches(0.2)
    p = tf2.paragraphs[0]
    p.text = "NAIVE OFFLINE REPLICATION                                      DATA CORRUPTION"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    p2 = tf2.add_paragraph()
    p2.text = "Clock Skew Overwrites & Data Drift"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(6)

    p3 = tf2.add_paragraph()
    p3.text = "Disconnected units operating without causal tracking rely on Last-Write-Wins (LWW) timestamps. Clock skew silently destroys critical field telemetry, notes, and mission decisions upon reconnection."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(10.5)
    p3.font.color.rgb = C_TEXT_MUTED
    p3.space_before = Pt(4)

    p4 = tf2.add_paragraph()
    p4.text = "FLOW: Rover A + Rover B (Offline) -> LWW Wall-Clock Sync\nCORRUPTION: Skewed clock silently discards ground-truth field logs"
    p4.font.name = FONT_MONO
    p4.font.size = Pt(8.5)
    p4.font.color.rgb = C_ACCENT
    p4.space_before = Pt(6)

    # Bottom 3 Pillars
    add_line(slide2, Inches(0.8), Inches(4.5), Inches(11.7), Inches(0.015), C_BORDER)

    pils = [
        ("01 / DEPENDENCY", "Cloud Paralysis", "Existing AI assistants cannot query vectors or store decisions without an active link. Field rovers and frontline operators are stranded during RF dead-zones.", C_CRITICAL),
        ("02 / INTEGRITY", "Clock Skew Overwrites", "Independent offline edits lack causal versioning. Re-synchronization without CRDTs leads to irreversible state corruption and unflagged divergences.", C_ACCENT),
        ("03 / PRIVACY", "Unpartitioned Sync", "Single-tier memory architectures sync everything: private credentials, personal observations, and fleet data are inadvertently leaked into central cloud logs.", C_KRYPTA),
    ]

    for i, (tag, title, body, color) in enumerate(pils):
        bx = slide2.shapes.add_textbox(Inches(0.8 + i * 4.0), Inches(4.7), Inches(3.6), Inches(2.2))
        tf = bx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_MONO
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = color

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT
        p2.space_before = Pt(4)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = FONT_BODY
        p3.font.size = Pt(10.5)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.space_before = Pt(4)

    # =========================================================================
    # SLIDE 3: CORE ARCHITECTURE
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_bg(slide3)
    add_header(
        slide3,
        "ARCHITECTURE INNOVATION",
        "Smaran keeps memory alive at the edge.",
        "A resilient local runtime combining embedded vector search with cryptographic partitioning and causal convergence.",
        3
    )

    # Left Column: Connected System Structure
    # Tier 1
    add_line(slide3, Inches(0.8), Inches(1.8), Inches(0.04), Inches(0.85), C_ACCENT)
    b_t1 = slide3.shapes.add_textbox(Inches(0.95), Inches(1.8), Inches(4.8), Inches(0.9))
    tf = b_t1.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "EDGE RUNTIME"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Smaran Core &middot; Qdrant Edge Embedded"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p3 = tf.add_paragraph()
    p3.text = "Local ONNX BGE embeddings with SQLite WAL hybrid dense + BM25 reciprocal rank fusion. Runs standalone with sub-9ms latency."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(10)
    p3.font.color.rgb = C_TEXT_MUTED

    # Tier 2: Tri-shard
    add_line(slide3, Inches(0.8), Inches(2.9), Inches(5.0), Inches(0.015), C_BORDER)
    shards = [
        ("KRYPTA", "Private Vault", "AES-GCM-256 encrypted. 0 bytes leaked to cloud. Never touches LLM prompts.", C_KRYPTA),
        ("HERMES", "Operational", "High-frequency telemetry & queues. 85.3% wire savings by staying local.", C_ACCENT),
        ("AGORA", "Consensus", "Fleet knowledge synced with central Qdrant cluster on reconnect.", C_NOMINAL),
    ]
    for i, (stag, stitle, sbody, scolor) in enumerate(shards):
        sbx = slide3.shapes.add_textbox(Inches(0.8 + i * 1.7), Inches(3.05), Inches(1.55), Inches(1.4))
        tf = sbx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = stag
        p.font.name = FONT_MONO
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = scolor
        p2 = tf.add_paragraph()
        p2.text = stitle
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT
        p3 = tf.add_paragraph()
        p3.text = sbody
        p3.font.name = FONT_BODY
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = C_TEXT_MUTED
    add_line(slide3, Inches(0.8), Inches(4.55), Inches(5.0), Inches(0.015), C_BORDER)

    # Tier 3: Consensus Engine
    add_line(slide3, Inches(0.8), Inches(4.7), Inches(0.04), Inches(0.85), C_NOMINAL)
    b_t3 = slide3.shapes.add_textbox(Inches(0.95), Inches(4.7), Inches(4.8), Inches(0.9))
    tf = b_t3.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "CONSENSUS ENGINE"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL
    p2 = tf.add_paragraph()
    p2.text = "Themis Causal CRDT Engine"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p3 = tf.add_paragraph()
    p3.text = "Version vector comparison identifies concurrent divergence without relying on synchronized wall clocks."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(10)
    p3.font.color.rgb = C_TEXT_MUTED

    # Provenance box
    b_aud = slide3.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(5.0), Inches(0.5))
    tf = b_aud.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "AUDIT PRINCIPLE: Cryptographic provenance hashes accompany every stored memory point."
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.color.rgb = C_TEXT_MUTED

    # Right Column: Screenshot
    shot4 = SHOT_DIR / "04_memory_explorer.png"
    if shot4.exists():
        slide3.shapes.add_picture(str(shot4), Inches(6.1), Inches(1.8), width=Inches(6.4))
    c_box = slide3.shapes.add_textbox(Inches(6.1), Inches(6.05), Inches(6.4), Inches(0.4))
    tf = c_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "FIGURE 3.0 — Memory Explorer inspecting encrypted Krypta, operational Hermes, and synced Agora shards."
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 4: SYSTEM PIPELINE
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_bg(slide4)
    add_header(
        slide4,
        "SYSTEM PIPELINE",
        "From raw input to trusted memory.",
        "Every incoming instruction passes through deterministic edge classification, cryptographic gating, and causal reconciliation.",
        4
    )

    # 5 Horizontal Pipeline Steps
    psteps = [
        ("01 / INGESTION", "Input Stream", "Natural language instruction, document chunk, or sensor stream.", 'DATA TRACE:\n"Meeting: use PostgreSQL for Project Nova"', C_ACCENT),
        ("02 / ARGUS", "Classification", "Local PII regex scrubbing & zero-shot routing into Facts vs Decisions.", "ARGUS TRACE:\nDECISION (0.80) | phone_in rule scrub", C_ACCENT),
        ("03 / ROUTING", "Tri-Shard Gate", "Tags determine residency: Krypta (local), Hermes (cache), Agora (sync).", "GATE TRACE:\nPII -> Krypta (AES-GCM)\nFact -> Agora (Fleet)", C_KRYPTA),
        ("04 / RETRIEVAL", "Hybrid Recall", "Sub-9ms dense vector + BM25 lexical search with Reciprocal Rank Fusion.", "SEARCH TRACE:\nDense: 0.875 | BM25: 0.700\nRRF Score: 0.919", C_NOMINAL),
        ("05 / THEMIS", "Causal Resolution", "Version-vector comparison reconciles concurrent fleet drift deterministically.", "CAUSAL TRACE:\nVector: {A:7}\nProvenance Hash: [1]", C_ACCENT_DEEP),
    ]

    for i, (tag, title, body, trace, color) in enumerate(psteps):
        left_pos = Inches(0.8 + i * 2.4)
        add_line(slide4, left_pos, Inches(1.8), Inches(2.2), Inches(0.03), color)

        bx = slide4.shapes.add_textbox(left_pos, Inches(1.9), Inches(2.2), Inches(1.4))
        tf = bx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = tag
        p.font.name = FONT_MONO
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = color
        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT
        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = FONT_BODY
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.space_before = Pt(2)

        # Trace sub-box
        tbox = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_pos, Inches(3.3), Inches(2.2), Inches(0.9))
        tbox.fill.solid()
        tbox.fill.fore_color.rgb = C_SURFACE
        tbox.line.color.rgb = C_BORDER
        tbox.line.width = Pt(1)
        ttf = tbox.text_frame
        ttf.word_wrap = True
        ttf.margin_left = ttf.margin_right = ttf.margin_top = ttf.margin_bottom = Inches(0.08)
        p = ttf.paragraphs[0]
        p.text = trace
        p.font.name = FONT_MONO
        p.font.size = Pt(8)
        p.font.color.rgb = C_TEXT_MUTED

    # Bottom Two Technical Principles
    add_line(slide4, Inches(0.8), Inches(4.6), Inches(11.7), Inches(0.015), C_BORDER)

    bx_p1 = slide4.shapes.add_textbox(Inches(0.8), Inches(4.8), Inches(5.6), Inches(1.8))
    tf1 = bx_p1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0
    p = tf1.paragraphs[0]
    p.text = "Deterministic Pre-Model Guardrails"
    p.font.name = FONT_TITLE
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_TEXT
    p2 = tf1.add_paragraph()
    p2.text = (
        "Personal identifiable information (PII) and hardware credentials are stripped at the edge "
        "prior to embedding calculation. Krypta memories are sealed under device-unique AES-GCM-256 keys "
        "and cannot be transmitted to external LLM prompts."
    )
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = C_TEXT_MUTED
    p2.space_before = Pt(4)

    bx_p2 = slide4.shapes.add_textbox(Inches(6.8), Inches(4.8), Inches(5.6), Inches(1.8))
    tf2 = bx_p2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p = tf2.paragraphs[0]
    p.text = "Wire-Efficient Selective Sharding"
    p.font.name = FONT_TITLE
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_TEXT
    p2 = tf2.add_paragraph()
    p2.text = (
        "By isolating high-frequency operational state to the local Hermes shard, Smaran achieves an 85.3% "
        "reduction in wire transmission bandwidth, syncing only collaborative Agora knowledge with the "
        "central Qdrant cluster on reconnection."
    )
    p2.font.name = FONT_BODY
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = C_TEXT_MUTED
    p2.space_before = Pt(4)

    # =========================================================================
    # SLIDE 5: PRODUCT EXPERIENCE
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_bg(slide5)
    add_header(
        slide5,
        "PRODUCT EXPERIENCE",
        "One interface. Two operating modes.",
        "Seamless transitions between cloud-enhanced grounded synthesis and zero-connectivity edge execution.",
        5
    )

    # Left: Online Mode
    bx_on = slide5.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(5.6), Inches(0.4))
    tf = bx_on.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "ONLINE: GROUNDED SYNTHESIS                     GEMINI + PROVENANCE"
    p.font.name = FONT_MONO
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    shot2 = SHOT_DIR / "02_companion_online_crop.png"
    if shot2.exists():
        slide5.shapes.add_picture(str(shot2), Inches(0.8), Inches(2.2), width=Inches(5.6))

    cap_on = slide5.shapes.add_textbox(Inches(0.8), Inches(5.7), Inches(5.6), Inches(1.0))
    tf = cap_on.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Gemini synthesizes verified answers citing cryptographic source markers [1]. Operators inspect underlying memory chunks, shard origins, and 96% confidence metrics."
    p.font.name = FONT_BODY
    p.font.size = Pt(10.5)
    p.font.color.rgb = C_TEXT_MUTED

    # Right: Offline Mode
    bx_off = slide5.shapes.add_textbox(Inches(6.8), Inches(1.8), Inches(5.6), Inches(0.4))
    tf = bx_off.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "OFFLINE: SURFACE AUTONOMY                     SUB-9ms LOCAL RECALL"
    p.font.name = FONT_MONO
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL

    shot3 = SHOT_DIR / "03_companion_offline_crop.png"
    if shot3.exists():
        slide5.shapes.add_picture(str(shot3), Inches(6.8), Inches(2.2), width=Inches(5.6))

    cap_off = slide5.shapes.add_textbox(Inches(6.8), Inches(5.7), Inches(5.6), Inches(1.0))
    tf = cap_off.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Zero cloud dependency. Instant hybrid recall using embedded ONNX models. Autonomous task agent executes reminders and maintenance queues in a local outbox."
    p.font.name = FONT_BODY
    p.font.size = Pt(10.5)
    p.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 6: THE DIFFERENTIATOR
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    add_bg(slide6)
    add_header(
        slide6,
        "CORE DIFFERENTIATOR",
        "What happens when two devices disagree?",
        "Themis causal CRDT replaces arbitrary Last-Write-Wins timestamps with mathematical version-vector reconciliation.",
        6
    )

    # Left Column: Causal Sequence
    # Step 1
    add_line(slide6, Inches(0.8), Inches(1.8), Inches(0.03), Inches(0.65), C_ACCENT)
    bx_s1 = slide6.shapes.add_textbox(Inches(0.95), Inches(1.8), Inches(4.8), Inches(0.65))
    tf = bx_s1.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "ROVER A (OFFLINE)                                        VECTOR {A:1, B:0}"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Updates Solar Array calibration to 16:00 UTC"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT

    # Step 2
    add_line(slide6, Inches(0.8), Inches(2.6), Inches(0.03), Inches(0.65), C_ACCENT)
    bx_s2 = slide6.shapes.add_textbox(Inches(0.95), Inches(2.6), Inches(4.8), Inches(0.65))
    tf = bx_s2.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "ROVER B (OFFLINE)                                        VECTOR {A:0, B:1}"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT
    p2 = tf.add_paragraph()
    p2.text = "Updates Solar Array calibration to 17:00 UTC"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT

    # Step 3: Divergence Alert
    b_div = slide6.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(3.45), Inches(5.0), Inches(1.1))
    b_div.fill.solid()
    b_div.fill.fore_color.rgb = RGBColor(253, 247, 245)
    b_div.line.color.rgb = C_BORDER
    b_div.line.width = Pt(1)
    add_line(slide6, Inches(0.8), Inches(3.45), Inches(0.04), Inches(1.1), C_CRITICAL)

    tf = b_div.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.12)
    p = tf.paragraphs[0]
    p.text = "CONCURRENT DIVERGENCE DETECTED"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_CRITICAL
    p2 = tf.add_paragraph()
    p2.text = "Neither vector dominates: V_A not <= V_B and V_B not <= V_A.\nThemis marks state as Contested Fact instead of silently overwriting."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(3)

    # Step 4: Resolution
    b_res = slide6.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(4.7), Inches(5.0), Inches(1.1))
    b_res.fill.solid()
    b_res.fill.fore_color.rgb = RGBColor(244, 250, 246)
    b_res.line.color.rgb = C_BORDER
    b_res.line.width = Pt(1)
    add_line(slide6, Inches(0.8), Inches(4.7), Inches(0.04), Inches(1.1), C_NOMINAL)

    tf = b_res.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.12)
    p = tf.paragraphs[0]
    p.text = "HUMAN-IN-THE-LOOP RECONCILIATION"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL
    p2 = tf.add_paragraph()
    p2.text = "Supervisor selects authoritative version. Themis generates dominating causal vector {A:2, B:2} that deterministically converges across the entire fleet."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(3)

    # Guarantee text
    b_gt = slide6.shapes.add_textbox(Inches(0.8), Inches(6.0), Inches(5.0), Inches(0.4))
    tf = b_gt.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "GUARANTEE: 100% causal convergence verified across 100 partition merge stress simulations."
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.color.rgb = C_TEXT_MUTED

    # Right Column: Screenshot
    shot5 = SHOT_DIR / "05_conflicts_crop.png"
    if shot5.exists():
        slide6.shapes.add_picture(str(shot5), Inches(6.1), Inches(1.8), width=Inches(6.4))
    c_box = slide6.shapes.add_textbox(Inches(6.1), Inches(6.05), Inches(6.4), Inches(0.4))
    tf = c_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "FIGURE 6.0 — Conflicts console showing real Argus decision audits, PII rule matches, and causal divergence."
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 7: VERIFIED BENCHMARKS
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    add_bg(slide7)
    add_header(
        slide7,
        "VERIFIED BENCHMARKS",
        "Built to be tested, not just demonstrated.",
        None,
        7
    )

    # Top 3 Metrics
    metrics = [
        ("sub-9ms", "Local Hybrid Retrieval", "Dense ONNX embedding + BM25 Reciprocal Rank Fusion executing entirely on-device via SQLite WAL.", C_ACCENT),
        ("0 bytes", "Private Context Leaked", "Cryptographic gate blocks cloud LLM requests whenever Krypta private vault context is detected.", C_KRYPTA),
        ("100%", "Causal Convergence", "Zero silent data overwrites across 100 simulated concurrent partition merges via Themis CRDTs.", C_NOMINAL),
    ]

    for i, (stat, title, body, color) in enumerate(metrics):
        left_pos = Inches(0.8 + i * 4.0)
        add_line(slide7, left_pos, Inches(1.75), Inches(3.6), Inches(0.03), color)

        bx = slide7.shapes.add_textbox(left_pos, Inches(1.85), Inches(3.6), Inches(1.4))
        tf = bx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = stat
        p.font.name = FONT_TITLE
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = C_TEXT

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.name = FONT_TITLE
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT
        p2.space_before = Pt(4)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = FONT_BODY
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.space_before = Pt(2)

    # Lower Section: Prove It Screenshot + Explanation
    shot6 = SHOT_DIR / "06_prove_it.png"
    if shot6.exists():
        slide7.shapes.add_picture(str(shot6), Inches(0.8), Inches(3.55), width=Inches(7.2))

    bx_exp = slide7.shapes.add_textbox(Inches(8.3), Inches(4.5), Inches(4.2), Inches(2.0))
    tf = bx_exp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "CLIENT-SIDE REPRODUCIBILITY"
    p.font.name = FONT_MONO
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = C_NOMINAL

    p2 = tf.add_paragraph()
    p2.text = "Live Browser Verification"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(15)
    p2.font.bold = True
    p2.font.color.rgb = C_TEXT
    p2.space_before = Pt(4)

    p3 = tf.add_paragraph()
    p3.text = (
        "Judges do not need to take our word for it: the Prove It console runs live mathematical "
        "proofs directly inside the browser, verifying latency thresholds, privacy boundary enforcement, "
        "and causal reconciliation on demand."
    )
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = C_TEXT_MUTED
    p3.space_before = Pt(6)

    # =========================================================================
    # SLIDE 8: HERO CLOSING
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    add_bg(slide8)

    # Category Tracker
    t_box = slide8.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(8.0), Inches(0.3))
    tf = t_box.text_frame
    p = tf.paragraphs[0]
    p.text = "CODE CUBICLE 6.0 | PROBLEM STATEMENT 3"
    p.font.name = FONT_MONO
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    # Giant Closing Statement
    head_box = slide8.shapes.add_textbox(Inches(0.8), Inches(0.95), Inches(11.5), Inches(1.1))
    tf = head_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Intelligence should not disappear when connectivity does."
    p.font.name = FONT_TITLE
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = C_TEXT

    p2 = tf.add_paragraph()
    p2.text = "Smaran &middot; Continuous vector intelligence at the edge."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = C_ACCENT
    p2.space_before = Pt(4)

    # Hero Center Screen
    if shot1.exists():
        slide8.shapes.add_picture(str(shot1), Inches(0.8), Inches(2.4), width=Inches(11.7))

    # Bottom Credits
    add_line(slide8, Inches(0.8), Inches(6.8), Inches(11.7), Inches(0.015), C_BORDER)
    b_foot = slide8.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.3))
    tf = b_foot.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "TEAM: Sanskar Tiwari &middot; Kanishka Salgude &middot; Shambhavi Patil                                                                 BUILT WITH QDRANT EDGE &middot; CODE CUBICLE 6.0"
    p.font.name = FONT_MONO
    p.font.size = Pt(8.5)
    p.font.color.rgb = C_TEXT_MUTED

    # Save outputs
    PPT_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPTX_OUT))
    prs.save(str(ROOT_PPTX_OUT))
    print(f"Presentation saved successfully:")
    print(f"  - {PPTX_OUT}")
    print(f"  - {ROOT_PPTX_OUT}")


if __name__ == "__main__":
    create_deck()
