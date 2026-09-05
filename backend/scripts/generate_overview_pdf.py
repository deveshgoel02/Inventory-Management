# -*- coding: utf-8 -*-
"""Generates docs/System-Overview.pdf: a plain-language explanation of the
whole Shoe Xpress Inventory Intelligence system - architecture, hosting,
how the ledger works, how the forecasting/"AI" actually works, and the
important internal mechanics a non-developer owner should understand.

Deliberately ASCII-only in every string literal below: reportlab's base-14
fonts (Helvetica etc.) don't reliably render em-dashes, curly quotes, or
currency symbols outside the Latin-1 range, so plain hyphens/straight quotes/
"Rs." are used everywhere instead of the fancier Unicode equivalents.

Requires `pip install reportlab` - deliberately NOT added to requirements.txt
since it's a one-off documentation tool, not something the running app needs
in production.

Usage (from backend/, with the venv active):
    python scripts/generate_overview_pdf.py
"""
import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    ListFlowable,
    ListItem,
    HRFlowable,
)

# backend/scripts/generate_overview_pdf.py -> repo_root/docs/System-Overview.pdf
OUT_PATH = str(Path(__file__).resolve().parents[2] / "docs" / "System-Overview.pdf")

NAVY = colors.HexColor("#111827")
INDIGO = colors.HexColor("#4f46e5")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#f6f7f9")
GREEN = colors.HexColor("#059669")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=26, textColor=NAVY, spaceAfter=6)
subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=13, textColor=SLATE, spaceAfter=4)
meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#94a3b8"))

h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=17, textColor=NAVY, spaceBefore=18, spaceAfter=8)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=INDIGO, spaceBefore=12, spaceAfter=6)
body = ParagraphStyle("BodyText2", parent=styles["BodyText"], fontSize=10.3, leading=15, textColor=colors.HexColor("#1e293b"), spaceAfter=8)
bullet = ParagraphStyle("Bullet", parent=body, leftIndent=0, spaceAfter=4)
note = ParagraphStyle("Note", parent=body, backColor=colors.HexColor("#fffbeb"), borderColor=colors.HexColor("#fbbf24"), borderWidth=0.75, borderPadding=8, spaceAfter=10)
codebox = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=9, textColor=NAVY, backColor=LIGHT, borderPadding=6, spaceAfter=8)


def flow_box(text, width=6.6 * inch, fill=colors.white, border=NAVY, text_color=NAVY, bold=True):
    style = ParagraphStyle(
        "Box", parent=body, alignment=1, textColor=text_color,
        fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=10.5, leading=14,
    )
    t = Table([[Paragraph(text, style)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, border),
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


def arrow_down(label=""):
    style = ParagraphStyle("Arrow", parent=body, alignment=1, fontSize=9.5, textColor=SLATE, spaceAfter=0, spaceBefore=0, leading=11)
    text = "|<br/>v" + (("  " + label) if label else "")
    return Paragraph(text, style)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(i, bullet), bulletColor=INDIGO) for i in items],
        bulletType="bullet", start="circle", leftIndent=16, spaceBefore=2, spaceAfter=10,
    )


def kv_table(rows, col_widths=(1.7 * inch, 4.9 * inch)):
    data = [[Paragraph("<b>" + k + "</b>", body), Paragraph(v, body)] for k, v in rows]
    t = Table(data, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(0.75 * inch, 0.5 * inch, "Shoe Xpress Inventory Intelligence - System Overview")
    canvas.drawRightString(letter_width - 0.75 * inch, 0.5 * inch, "Page " + str(doc.page))
    canvas.restoreState()


letter_width, letter_height = LETTER

doc = SimpleDocTemplate(
    OUT_PATH, pagesize=LETTER,
    topMargin=0.85 * inch, bottomMargin=0.85 * inch,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    title="Shoe Xpress Inventory Intelligence - System Overview",
    author="Shoe Xpress",
)

story = []

# ---------------------------------------------------------------- Title page
story.append(Spacer(1, 0.6 * inch))
story.append(Paragraph("SHOE XPRESS", ParagraphStyle("Brand", parent=styles["Normal"], fontSize=14, textColor=SLATE, alignment=1)))
story.append(Paragraph("Inventory Intelligence", title_style.clone("TitleCenter", alignment=1)))
story.append(Paragraph("How the whole system works, in plain language", subtitle_style.clone("SubCenter", alignment=1)))
story.append(Spacer(1, 0.15 * inch))
story.append(Paragraph("Generated " + datetime.date.today().strftime("%d %B %Y"), meta_style.clone("MetaCenter", alignment=1)))
story.append(Spacer(1, 0.5 * inch))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
story.append(Spacer(1, 0.3 * inch))

story.append(Paragraph(
    "This document explains - without assuming you're a programmer - where every piece of this system "
    "physically lives on the internet, how a click on your screen turns into a database update, how the "
    "'AI' forecasting actually works under the hood, and the handful of internal rules that matter most "
    "if something ever looks wrong.",
    body,
))
story.append(Paragraph(
    "Nothing here is marketing language. Where something is a limitation or a cost you should know about, "
    "it's called out plainly.",
    body,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 1. Big picture
story.append(Paragraph("1. The Big Picture", h1))
story.append(Paragraph(
    "The system is split into three independent pieces, each hosted on a different specialist platform, "
    "talking to each other over the internet. This is completely standard practice for modern web software - "
    "each platform does the one job it's best at.",
    body,
))

story.append(flow_box("YOUR BROWSER<br/>(phone, laptop, tablet - anywhere)", fill=LIGHT, border=SLATE, text_color=NAVY))
story.append(arrow_down("loads the app, then talks to it over the internet"))
story.append(flow_box("FRONTEND - what you see and click<br/>Hosted on Vercel", fill=colors.white, border=INDIGO))
story.append(arrow_down("every button click sends a request here"))
story.append(flow_box("BACKEND - the brain: rules, calculations, security<br/>Hosted on Render", fill=colors.white, border=INDIGO))
story.append(arrow_down("reads and writes the actual data"))
story.append(flow_box("DATABASE - every product, sale, purchase, user<br/>Hosted on Neon", fill=colors.white, border=GREEN))

story.append(Spacer(1, 0.15 * inch))
story.append(Paragraph(
    "The important idea to take away: <b>your browser never talks to the database directly.</b> Every single "
    "number you see on screen was calculated by the backend, from data in the database, at the moment you "
    "asked for it. There is no separate 'report generator' or spreadsheet lurking somewhere with different "
    "numbers - there is exactly one source of truth.",
    body,
))

story.append(Paragraph("Where each piece actually lives", h2))
story.append(kv_table([
    ("Frontend (what you see)", "React app, hosted on <b>Vercel</b>, at "
     "inventory-management-wheat-two.vercel.app. This is just the visual interface - buttons, tables, charts. "
     "It has no logic of its own; it asks the backend for everything."),
    ("Backend (the brain)", "FastAPI (Python), hosted on <b>Render</b>, at shoexpress-api.onrender.com. Every "
     "calculation - stock levels, forecasts, recommendations, permissions - happens here, never in your browser."),
    ("Database (the data)", "PostgreSQL, hosted on <b>Neon</b> (a managed Postgres provider). This is a plain, "
     "industry-standard relational database - the same kind of technology banks and e-commerce sites use. "
     "It is <i>not</i> a spreadsheet and not editable by hand; only the backend writes to it."),
    ("Source code", "Stored on <b>GitHub</b> (deveshgoel02/Inventory-Management), privately. Every change "
     "either of us makes goes there first, and both Vercel and Render watch that repository and "
     "<b>automatically redeploy</b> within about a minute of any update - no manual 'publish' step."),
], col_widths=(1.6 * inch, 5.0 * inch)))

story.append(PageBreak())

# ---------------------------------------------------------------- 2. Request flow
story.append(Paragraph("2. What Actually Happens When You Click a Button", h1))
story.append(Paragraph(
    "Take a concrete example: you open the Inventory page. Here is the literal chain of events, in order:",
    body,
))
story.append(bullets([
    "Your browser fetches the page's code from <b>Vercel</b> - this happens once, fast, and is just files (HTML/JS/CSS), no business data.",
    "The page immediately makes a request to the <b>Render</b> backend: 'give me the current stock list.' "
    "This request includes a security token proving who you are (see Section 5).",
    "The backend checks that token, checks your role has permission to view inventory, then runs a query "
    "against the <b>Neon</b> database.",
    "Critically, the backend does <b>not</b> just read a stored 'current stock' number. It adds up every "
    "single stock transaction ever recorded for each product - every purchase, every sale, every return, every "
    "manual adjustment - to compute the true current quantity, live, every time. This is explained fully in "
    "Section 4.",
    "The backend sends the computed numbers back as data (JSON). The frontend then draws the table and charts "
    "you see. No calculation happens in the browser - it only displays what the backend already worked out.",
]))
story.append(Paragraph(
    "The same pattern repeats for literally every page: dashboard, sales, purchasing, forecasting, "
    "recommendations. The frontend is a display layer; the backend is authoritative.",
    body,
))

story.append(Paragraph("Why it's built this way", h2))
story.append(Paragraph(
    "If financial and inventory numbers were calculated in the browser (in JavaScript), two different people "
    "could see two different 'correct' answers depending on their device, or a user could tamper with the "
    "page to see fake numbers. Keeping all authoritative math on the server closes that door entirely - the "
    "backend is the only thing that can be trusted, and it's the only thing that touches the database.",
    body,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 3. Hosting/cost detail
story.append(Paragraph("3. Hosting Details - What's Free, What Isn't, and the One Catch", h1))
story.append(kv_table([
    ("Vercel (frontend)", "Free tier. Effectively unlimited for this scale of use. No known limitations for "
     "how this app uses it."),
    ("Render (backend)", "Free tier. <b>The one real catch:</b> a free Render service goes to sleep after about "
     "15 minutes of no traffic. The next request after that has to wait 30-60 seconds while it wakes back up "
     "- you'll see a slightly longer delay than usual on the first click of the day. After that it's fast until "
     "it goes idle again. Upgrading to a paid Render plan (a small monthly fee) removes this delay entirely if "
     "it becomes annoying."),
    ("Neon (database)", "Free tier: 0.5 GB storage, which comfortably covers years of a business at this scale "
     "before it becomes a concern. It also 'scales to zero' when unused, which can add a similar brief "
     "wake-up delay, same as Render."),
    ("GitHub (code storage)", "Free, private repository. This is not customer-facing at all - it's where the "
     "actual program code is kept and version-tracked."),
], col_widths=(1.5 * inch, 5.1 * inch)))
story.append(Paragraph(
    "Total running cost today: <b>Rs. 0/month.</b> The trade-off for that is the wake-up delay described above "
    "- acceptable for a small team checking the system a handful of times a day, worth revisiting if usage "
    "grows heavily or becomes customer-facing.",
    note,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 4. Ledger
story.append(Paragraph("4. The Core Idea: Stock Is Never Just 'A Number'", h1))
story.append(Paragraph(
    "This is the single most important internal rule in the whole system, and the one most worth understanding "
    "even if nothing else in this document sticks.",
    body,
))
story.append(Paragraph(
    "There is no field anywhere in the database called 'current stock' that gets edited directly. Instead, "
    "every single event that changes stock - a purchase received, a sale made, a customer return, a manual "
    "correction - is written down permanently as one row in something like a bank statement (internally called "
    "the <b>inventory ledger</b>). Current stock for any product is always: <i>add up every one of those rows "
    "for that product, right now.</i>",
    body,
))
story.append(Paragraph("The nine kinds of events that can move stock", h2))
story.append(bullets([
    "<b>Opening Balance</b> - the starting quantity when a SKU first enters the system (e.g. from an import).",
    "<b>Purchase</b> - stock received from a supplier (adds).",
    "<b>Sale</b> - stock sold to a customer (subtracts).",
    "<b>Sale Return</b> - a customer sent something back (adds).",
    "<b>Purchase Return</b> - stock sent back to a supplier (subtracts).",
    "<b>Stock Adjustment In / Out</b> - manual corrections, e.g. damaged goods found, or a stock-take "
    "correction (adds or subtracts, always with a required note explaining why).",
    "<b>Transfer In / Out</b> - stock moved between warehouses.",
]))
story.append(Paragraph(
    "The practical benefit: every unit of stock can always be traced back to exactly which transaction put it "
    "there or took it away. If a number ever looks wrong, the fix is never 'overwrite the number' - it's "
    "'look at the ledger for that SKU and find the transaction that's wrong,' which is always possible because "
    "nothing is ever silently deleted.",
    body,
))
story.append(Paragraph(
    "One safety rule enforced by the backend: the system will refuse to record a sale that would push stock "
    "below zero (unless it's explicitly flagged as historical data being imported, where old records "
    "sometimes have gaps). This is a real, tested guardrail, not just a suggestion.",
    body,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 5. Auth
story.append(Paragraph("5. Logging In and Permissions - How Security Works", h1))
story.append(Paragraph(
    "When you log in, the backend checks your email and password, and if correct, hands your browser a "
    "signed, tamper-proof digital token (a JWT - 'JSON Web Token'). Your browser stores that token and "
    "attaches it to every request it makes afterwards, like a stamped ID card. The backend checks that stamp "
    "on every single request - nobody can ask for data or make a change without a valid one, and it expires "
    "automatically after 8 hours, at which point you'd need to log in again.",
    body,
))
story.append(Paragraph("Four roles, and what each can do", h2))
story.append(kv_table([
    ("ADMIN", "Everything, including creating/editing other users and changing anyone's role."),
    ("MANAGER", "Everything operational - sales, purchasing, inventory, imports, AI settings - except "
     "managing other users' accounts."),
    ("INVENTORY_STAFF", "Can view and adjust stock, record sales and receipts, run imports - day-to-day "
     "warehouse work, no configuration access."),
    ("VIEWER", "Read-only access to everything, plus the ability to export reports. Can't change anything."),
], col_widths=(1.5 * inch, 5.1 * inch)))
story.append(Paragraph(
    "Important: these checks happen on the backend, not just by hiding buttons in the interface. Even if "
    "someone found a way to make a request directly (bypassing the visible app entirely), the backend would "
    "still refuse it if their role doesn't have permission. There's also a specific safeguard preventing the "
    "very last remaining ADMIN account from being demoted or deactivated by anyone - including themselves - "
    "so the system can never end up with nobody able to manage users.",
    body,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 6. AI
story.append(Paragraph("6. The 'AI' - What It Actually Is (and Isn't)", h1))
story.append(Paragraph(
    "This is worth being very precise about, because 'AI' gets used loosely everywhere. There is "
    "<b>no ChatGPT-style language model</b> involved in any number this system produces, and no neural network "
    "making purchase decisions. What it actually uses is real, well-established statistics - the same kind "
    "of forecasting math used in supply-chain and demand-planning software for decades. That's a deliberate "
    "choice: statistical models are transparent and explainable, which matters enormously when the output "
    "influences real purchasing decisions.",
    note,
))

story.append(Paragraph("Where the forecasting model runs", h2))
story.append(Paragraph(
    "There is no separate 'AI server.' The forecasting math is plain Python code that runs as part of the "
    "same backend described in Section 1 - on Render, alongside everything else. When you open the AI "
    "Forecasting or Purchase Recommendations page, the backend runs these calculations on the spot and returns "
    "the result. Nothing is pre-trained or hosted separately.",
    body,
))

story.append(Paragraph("How it actually decides what to forecast", h2))
story.append(Paragraph(
    "For each product, the system first asks: <i>how much real sales history do we actually have for this "
    "exact SKU?</i> The model used depends entirely on the answer - it never applies the same method blindly "
    "to a SKU with three days of history and one with three years:",
    body,
))
story.append(bullets([
    "<b>Fewer than 6 days of history</b> - the system explicitly says 'not enough data yet' and shows a "
    "zero forecast rather than inventing a number. This is a deliberate refusal to fabricate.",
    "<b>6-89 days</b> - uses a <i>simple moving average</i> (a plain recent-sales average). Too little "
    "history to trust anything fancier without overfitting noise.",
    "<b>90 days to 12 months</b> - uses a <i>weighted moving average</i>, which leans more heavily on the "
    "most recent weeks than older ones.",
    "<b>12+ months</b> - uses <i>Holt's linear trend method</i>, a well-known technique that can project a "
    "rising or falling trend forward - deliberately capped so a single unusual hot streak can't be "
    "extrapolated into an absurd number.",
]))
story.append(Paragraph("How the system checks its own accuracy", h2))
story.append(Paragraph(
    "Every forecast is <b>backtested</b> before being shown: the model is temporarily hidden from the most "
    "recent couple of weeks of real sales, asked to predict them anyway, and then graded against what actually "
    "happened, using standard accuracy measures (MAE, RMSE, MAPE - different ways of measuring 'how far off "
    "was the guess'). That grade becomes the displayed <b>Risk Level</b> (Low/Medium/High). This is separate "
    "from <b>Confidence</b> (High/Medium/Low), which only reflects how much history exists. A SKU can have High "
    "confidence (lots of data) but Medium or High risk (that data happens to be volatile and hard to predict) "
    "- the two are shown independently on purpose, instead of collapsing them into one misleading score.",
    body,
))

story.append(Paragraph("How a purchase quantity is actually calculated", h2))
story.append(Paragraph(
    "The suggested order quantity for a SKU comes from one explicit, documented formula - never a hidden "
    "black box:",
    body,
))
story.append(Paragraph(
    "Suggested Order = max( 0 , Forecast Demand During Lead Time + Safety Stock "
    "- Current Stock - Incoming Stock )",
    codebox,
))
story.append(bullets([
    "<b>Forecast Demand During Lead Time</b> = the SKU's forecast daily sales rate x the supplier's lead time "
    "(how many days it takes them to deliver, pulled from that supplier's own record, or a configurable default).",
    "<b>Safety Stock</b> = a buffer, calculated as the daily sales rate x a configurable number of 'safety' "
    "days (defaults to 14, adjustable in Settings).",
    "<b>Current Stock</b> = the live ledger total from Section 4.",
    "<b>Incoming Stock</b> = quantity already on order from open purchase orders for that SKU.",
]))
story.append(Paragraph(
    "The result is then rounded up to the nearest multiple of that SKU's minimum order quantity, if one is set. "
    "Every recommendation stores every one of these numbers alongside itself, so 'why 200 units?' always has "
    "a concrete, inspectable answer on screen - never just a bare number to trust blindly.",
    body,
))
story.append(Paragraph(
    "<b>Nothing here ever places an order automatically.</b> Every recommendation sits as 'Pending' until a "
    "person explicitly accepts or dismisses it. The AI's job stops at decision support.",
    note,
))

story.append(PageBreak())

# ---------------------------------------------------------------- 7. Import pipeline
story.append(Paragraph("7. How Importing a Spreadsheet Actually Works", h1))
story.append(Paragraph(
    "When a sales or purchases file is uploaded, the backend first reads only its column headers and compares "
    "them against known patterns for each record type - a file with a price/rate column and no cost column "
    "scores as 'Sales'; one with a cost/supplier column scores as 'Purchases,' and so on. This is why no "
    "manual 'what kind of file is this' step is needed anymore.",
    body,
))
story.append(Paragraph(
    "Every row is then individually validated - missing SKU, invalid date, negative quantity, a SKU that "
    "doesn't exist yet, a duplicate row within the same file - before anything touches the database. If "
    "every row checks out clean, the import commits immediately with no extra click. If anything is wrong, it "
    "stops and shows exactly which rows and why, and only the valid rows get imported once you confirm - "
    "invalid rows are always skipped, never guessed at or silently corrected.",
    body,
))

# ---------------------------------------------------------------- 8. Cheat sheet
story.append(Paragraph("8. Quick Reference", h1))
story.append(kv_table([
    ("Live site", "inventory-management-wheat-two.vercel.app"),
    ("Backend health check", "shoexpress-api.onrender.com/api/health - loading this should show "
     "{\"status\":\"ok\"}. Useful first check if something seems down."),
    ("Source code", "github.com/deveshgoel02/Inventory-Management (private repository)"),
    ("Full technical docs", "Inside the repository: README.md (setup/deployment) and "
     "docs/business-rules.md (the exact formula behind every number the app shows)."),
    ("If the site feels slow on first load", "Almost certainly the Render free-tier wake-up delay (Section 3) "
     "- wait ~30-60 seconds; it will be fast again afterward."),
    ("If a stock number looks wrong", "Open that SKU's page and read its ledger (Section 4) - it will show "
     "every transaction that built up to the current number."),
    ("Changing your password / profile", "Sidebar - Profile. Any user can update their own name, email, and "
     "password; only an ADMIN account can change roles."),
], col_widths=(1.7 * inch, 4.9 * inch)))

story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph(
    "Prepared as a plain-language companion to the technical documentation already in the project repository.",
    meta_style,
))

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("Wrote " + OUT_PATH)
