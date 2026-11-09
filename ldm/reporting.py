"""Portable HTML and CSV reports without third-party assets or services."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .common import atomic_text, decimal_money


def esc(value):
    return html.escape(str(value))


def table(rows, columns):
    if not rows:
        return '<p class="muted">No records.</p>'
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{esc(label)}</th>' for _, label in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{esc(row.get(key, ""))}</td>' for key, _ in columns) + '</tr>' for row in rows) + '</tbody></table></div>'


STYLE = """
:root{color-scheme:dark;--bg:#0b1020;--panel:#141d32;--line:#2a3852;--text:#edf2fc;--muted:#acbad1;--accent:#71d8c1;--red:#ff949d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.65 system-ui,-apple-system,sans-serif}main{max-width:1200px;margin:auto;padding:48px 28px}header{padding:20px 0 30px;border-bottom:1px solid var(--line)}h1{font-size:clamp(30px,5vw,48px);line-height:1.15;margin:12px 0}h2{font-size:23px;margin-top:0}h3{color:var(--accent)}.eyebrow{color:var(--accent);letter-spacing:.16em;font-size:12px;font-weight:700}.muted,small{color:var(--muted)}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:4px 12px;margin:4px 6px 4px 0;font-size:12px}.blocked{color:var(--red)}.pass{color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin:24px 0}.card,section{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px}section{margin-top:24px}.number{font-size:32px;font-weight:750}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:12px 10px;vertical-align:top}th{color:var(--accent);white-space:nowrap}td{max-width:480px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b1020;padding:16px;border-radius:8px;font-size:12px}details{border-top:1px solid var(--line);padding:14px 0}summary{cursor:pointer;font-weight:600}.flow{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}.flow span{background:#203047;padding:8px 12px;border-radius:8px}a{color:var(--accent)}button{background:var(--accent);color:var(--bg);border:0;padding:10px 16px;border-radius:8px;cursor:pointer}footer{padding:30px 0;color:var(--muted)}@media print{body{background:white;color:black}section,.card{background:white;border:1px solid #ccc;break-inside:avoid}.muted,small{color:#444}th,h3,a{color:#14584b}main{padding:10px}button{display:none}pre{background:#eee;color:black}}
"""


def render_report(path: Path, summary, profiles, result, matching, changes):
    status = summary["release_status"]
    issues = result["issues"]
    cards = [("Policies", summary["policy_count"]), ("Critical issues", summary["critical_count"]), ("Reviewed corrections", len(changes)), ("Endorsement variance", "R$ " + decimal_money(sum(i["evidence"].get("variance_cents") or 0 for i in issues if i["rule"] == "ENDORSEMENT_RECONCILIATION")))]
    cards_html = ''.join(f'<div class="card"><div class="muted">{esc(label)}</div><div class="number">{esc(value)}</div></div>' for label, value in cards)
    details = ''.join(f'<details><summary><span class="blocked">{esc(i["rule"])}</span> · {esc(i["entity"])}</summary><p>{esc(i["message"])}</p><pre>{esc(json.dumps(i["evidence"],indent=2,ensure_ascii=False))}</pre></details>' for i in issues)
    reconciliations = [{**row, **{k: "—" if row[k] is None else decimal_money(row[k]) for k in ("expected_premium_cents", "scheduled_total_cents", "paid_cents", "remaining_cents", "variance_cents")}} for row in result["reconciliations"]]
    content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LDM | Synthetic accounting close</title><style>{STYLE}</style></head><body><main>
<header><div class="eyebrow">LDM FRAMEWORK / INSURANCE LAB</div><h1>An accounting close<br>must explain the numbers.</h1><p class="muted">Diagnosis, endorsements, reconciliation and human review at a fictional insurer.</p><span class="badge">100% SYNTHETIC DATA</span><span class="badge {'pass' if status == 'APPROVED' else 'blocked'}">{esc(status)}</span><span class="badge">{esc(summary['as_of'])} · BRL</span><span class="badge">AI: not executed in this validation</span>
<div class="flow"><span>01 Diagnosis</span><span>02 Integration</span><span>03 AI-Assisted Quality</span><span>04 Validation</span><span>05 Knowledge Transfer</span></div></header>
<div class="grid">{cards_html}</div>
<section><h2>Release decision</h2><p>{'Deterministic checks passed. The accounting close was published for this demonstration.' if status == 'APPROVED' else 'Release blocked. Totals are provisional; resolve the exceptions and run the pipeline again.'}</p><p class="muted">Technical approval in this example is not compliance certification. Simulated reviews: {summary['simulated_review_count']}. Reviewer identity is self-declared locally, without authentication.</p><small>Run: {esc(summary['run_id'])} · Rule: {esc(summary['rule_version'])}</small></section>
<section><h2>The endorsement scenario</h2><p>Original premium R$1,200 · four paid installments of R$100 · R$240 increase · eight remaining installments.</p><p><strong>Expected: 8 × R$130 = R$1,040.</strong> Inserted error: 8 × R$120 = R$960. A mathematical rule detects the R$80 difference; the optional model only proposes an investigation.</p><p class="muted">No interest, taxes, pro-rata or refunds. Laboratory rule: equal_remaining. Corrections never modify the original CSVs.</p></section>
<section><h2>Exceptions blocking release</h2>{details or '<p class="pass">No critical issues in this run.</p>'}</section>
<section><h2>Reconciliation by policy</h2><p class="muted">Amounts in BRL. Balance includes all unsettled installments, including overdue amounts. Invalid sources make results provisional.</p>{table(reconciliations, [('policy_id','Policy'),('product','Product'),('expected_premium_cents','Updated premium'),('scheduled_total_cents','Scheduled total'),('paid_cents','Paid'),('remaining_cents','Balance'),('variance_cents','Variance'),('status','Status')])}</section>
<section><h2>Potential duplicate customer review</h2><p class="muted">Heuristic baseline: name similarity within shared addresses. This is neither AI nor a probability. Approvals create analytical associations; they do not merge source records or change financial amounts.</p>{table(matching,[('id','ID'),('left','Source A'),('right','Source B'),('score','Heuristic score'),('status','Decision'),('simulated','Simulated')])}</section>
<section><h2>Corrections applied after review</h2>{table(changes,[('request_id','Request'),('key','Record'),('field','Field'),('before','Before'),('after','After'),('simulated','Simulated')])}</section>
<section><h2>Source inventory</h2>{table(profiles,[('table','Source'),('rows','Records'),('grain','Key / grain'),('missing_by_column','Missing values')])}</section>
<section><h2>AI-assisted investigation</h2><p>The live integration is optional and requires an operator-configured key and model. No AI response has been fabricated. Run <code>python -m ldm assist --help</code> to produce a separate hypothesis file with evidence references.</p></section>
<footer>Reproducible educational experiment · no real customer information · no claim of deployment at Caixa/Youse · <button onclick="window.print()">Print report</button></footer>
</main></body></html>'''
    atomic_text(path, content)


def overview(path: Path, before, after, evaluation):
    a, b = before["summary"], after["summary"]
    atomic_text(path, f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LDM | Before and after</title><style>{STYLE}</style></head><body><main><header><div class="eyebrow">LDM FRAMEWORK / DEMO V0.1.1</div><h1>From error to evidence.</h1><p class="muted">An executable demonstration of insurance data modernization.</p><span class="badge">100% SYNTHETIC</span><span class="badge">SIMULATED APPROVALS</span></header><div class="grid"><div class="card"><h2>Before</h2><div class="number blocked">{a['critical_count']} issues</div><p>Close blocked. R$80 endorsement variance, duplicate payment, unmatched payment, missing amount and invalid date.</p><a href="runs/{esc(a['run_id'])}/report.html">Open diagnosis →</a></div><div class="card"><h2>After</h2><div class="number pass">{b['release_status']}</div><p>{b['applied_correction_count']} corrections approved in the simulation, preserving original sources. Future installments are R$130 and the variance is zero.</p><a href="runs/{esc(b['run_id'])}/report.html">Open result →</a></div><div class="card"><h2>Detected</h2><div class="number">{evaluation['defect_detection']['detected']} / {evaluation['defect_detection']['expected']}</div><p>Inserted scenarios detected against the evaluation reference.</p><small>This small fixture does not represent production performance.</small></div></div><section><h2>The demonstrated workflow</h2><div class="flow"><span>Generate sources</span><span>Detect discrepancies</span><span>Review proposals</span><span>Apply correction overlays</span><span>Revalidate and publish</span></div><h3>R$1,440 ≠ R$400 + R$960</h3><p>The simulated legacy system divided the R$240 increase across the original 12 installments but changed only the eight future installments. LDM detects an R$80 shortfall. The example rule requires allocating the increase across the eight remaining installments.</p><p class="muted">The mathematical analysis is deterministic. The optional AI module generates separate hypotheses subject to human review. The default demo does not call a model.</p></section><section><h2>How to interpret this result</h2><p>The demo command uses known experimental answers to simulate decisions. It does not establish real human review, regulatory compliance or measured improvements at a real insurer. Use generate, run and review to operate the workflow manually.</p></section><footer>See README.md and docs/RUNBOOK.md · Python 3.11+ · no external dependencies for the local workflow.</footer></main></body></html>''')
