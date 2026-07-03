"""Generates a handful of synthetic, intentionally differently-formatted fund documents
into sample_data/ so the ingest pipeline can be exercised without needing a real Google
Drive folder full of real manager PDFs. Each one uses different layout, terminology, and
units on purpose (that's the whole point of the assessment)."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = "sample_data"
styles = getSampleStyleSheet()


def _save_pdf(path: str, flowables: list) -> None:
    doc = SimpleDocTemplate(path, pagesize=LETTER, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    doc.build(flowables)


def acme_distressed() -> None:
    flow = [
        Paragraph("ACME Distressed Opportunities Fund LP", styles["Title"]),
        Paragraph("Monthly Factsheet — January 2025 | Managed by Acme Capital Partners", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Fund Statistics", styles["Heading2"]),
        Table(
            [
                ["As of Date", "1/31/2025"],
                ["NAV per Unit", "$142.55"],
                ["AUM", "$310 million"],
                ["YTD Return", "3.1%"],
                ["Since Inception", "42.7%"],
                ["Benchmark (HFRI Distressed Index)", "1.8% (Jan)"],
            ],
            colWidths=[3 * inch, 2.5 * inch],
        ),
        Spacer(1, 16),
        Paragraph("Monthly Performance", styles["Heading2"]),
        Table(
            [["Month", "Net Return", "NAV"], ["Nov-24", "1.2%", "137.20"], ["Dec-24", "-0.4%", "138.69"], ["Jan-25", "3.1%", "142.55"]],
            colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]),
        ),
        Spacer(1, 16),
        Paragraph("Manager Commentary", styles["Heading2"]),
        Paragraph(
            "The fund continued to capitalize on dislocations in stressed credit markets, adding to positions "
            "in mid-cap industrials while trimming energy-sector exposure amid tightening spreads. We remain "
            "constructive on distressed opportunities into Q2 as refinancing walls approach for several "
            "over-levered issuers.",
            styles["Normal"],
        ),
    ]
    _save_pdf(f"{OUT}/acme_distressed_factsheet_jan2025.pdf", flow)


def blue_harbor_statement() -> None:
    flow = [
        Paragraph("Blue Harbor Capital — Quarterly Investor Statement", styles["Title"]),
        Paragraph("Blue Harbor Global Macro Fund, Ltd. | Period Ending March 31, 2025", styles["Normal"]),
        Spacer(1, 14),
        Paragraph(
            "This statement summarizes Blue Harbor Global Macro Fund's performance for the first quarter of "
            "2025. Unit Value at quarter end stood at 218.94, up from 205.30 at the start of the period, "
            "representing a Net Return of 6.6% for the quarter. Assets Under Management grew to approximately "
            "USD 1.2 billion, reflecting both performance gains and net subscriptions.",
            styles["Normal"],
        ),
        Spacer(1, 10),
        Paragraph(
            "Month-by-month, the fund returned 2.1% in January, 1.4% in February, and 2.9% in March, "
            "outperforming the Bloomberg Global Macro Peer Index, which returned 0.9%, 0.5%, and 1.1% "
            "over the same three months respectively.",
            styles["Normal"],
        ),
        Spacer(1, 10),
        Paragraph(
            "Portfolio Manager Notes: We increased duration exposure in developed-market rates ahead of "
            "anticipated central bank pivots, and maintained a modest long-USD stance against a basket of "
            "EM currencies. Since the fund's launch in June 2019, cumulative net return stands at 118.4%.",
            styles["Normal"],
        ),
    ]
    _save_pdf(f"{OUT}/blue_harbor_quarterly_statement_q1_2025.pdf", flow)


def pinecrest_factsheet() -> None:
    flow = [
        Paragraph("Pinecrest Credit Partners", styles["Title"]),
        Paragraph("Fund Update — Feb '25", styles["Normal"]),
        Spacer(1, 12),
        Table(
            [
                ["Strategy", "Senior secured direct lending"],
                ["Inception", "Mar 2021"],
                ["Unit Price (Feb '25)", "104.88"],
                ["Total Fund Size", "€480mm"],
                ["MTD", "0.7%"],
                ["YTD", "1.5%"],
                ["Since Launch", "24.9%"],
            ],
            colWidths=[2.5 * inch, 3 * inch],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]),
        ),
        Spacer(1, 16),
        Paragraph(
            "Notes: Pinecrest continues to focus on senior secured loans to European lower-middle-market "
            "sponsors, with a bias toward defensive sectors (healthcare services, business software). "
            "Portfolio yield remains attractive versus tightening public credit spreads.",
            styles["Normal"],
        ),
    ]
    _save_pdf(f"{OUT}/pinecrest_update_feb2025.pdf", flow)


def summit_ridge_csv() -> None:
    content = (
        "Report,Summit Ridge Macro Fund - Monthly Performance Export\n"
        "Manager,Summit Ridge Capital Management\n"
        "Currency,USD\n"
        "\n"
        "Month,Return (%),NAV,YTD (%)\n"
        "2024-11,1.8,156.20,\n"
        "2024-12,2.5,160.10,\n"
        "2025-01,4.4,167.15,4.4\n"
    )
    with open(f"{OUT}/summit_ridge_performance_export.csv", "w") as f:
        f.write(content)


def northstar_email() -> None:
    html = """<html><body>
<p>Hi all,</p>
<p>Please find below our January update for <b>Northstar Credit Partners Opportunities Fund</b>.</p>
<p>As of January 31, 2025, the fund's NAV per share was 98.42, representing a return of
<b>2.8%</b> for the month and <b>2.8%</b> year-to-date. AUM stands at roughly $92 million.</p>
<table border="1">
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>MTD Return</td><td>2.8%</td></tr>
<tr><td>YTD Return</td><td>2.8%</td></tr>
<tr><td>Since Inception (Jul 2022)</td><td>31.2%</td></tr>
<tr><td>NAV / Share</td><td>98.42</td></tr>
</table>
<p>Commentary: We rotated further into CLO mezzanine tranches this month as spreads widened
following broader risk-off sentiment, a move we believe positions the fund well for
spread compression into Q2. We trimmed our small allocation to unsecured consumer credit.</p>
<p>Best,<br/>Northstar IR Team</p>
</body></html>"""
    with open(f"{OUT}/northstar_january_update_email.html", "w") as f:
        f.write(html)


if __name__ == "__main__":
    import os

    os.makedirs(OUT, exist_ok=True)
    acme_distressed()
    blue_harbor_statement()
    pinecrest_factsheet()
    summit_ridge_csv()
    northstar_email()
    print("Generated sample documents in", OUT)
