"""Seed the vectorstep_demo database with realistic fictional run history.

Purpose: stage the VectorStep UI for the marketing-site screenshots (hero carousel)
without touching the real `vectorstep` database or spending LLM tokens. Everything the
UI renders — trust panels, calibration bins, readiness card, dashboards — is
computed from these rows by the real service code.

Run with the VectorStep service venv, against the demo instance's DB:

    cd /Users/adalton/Development/github/VectorStep/service
    .venv/bin/python /Users/adalton/Development/github/VectorStep-Website/scripts/seed-demo-data.py

Prereqs: `createdb vectorstep_demo`, then start the service once against it (creates
tables) using the demo CONFIG_PATH (see the website repo README).

The story the data tells (deliberate, mirrors the landing page):
- alert-triage-critical (production): 90+ runs. The sre-investigation step's
  90-100% confidence band is measurably overconfident (~62% actual accuracy).
  Once the band accumulates n_min=20 marked outcomes, enforced calibration
  starts replacing the raw score — recent high-confidence runs escalate.
- checkout-refund-agent (testing): building its readiness evidence — some
  tiers pass, accuracy/calibration still short of the bar.
- payment-intake (production): boring and healthy, for dashboard variety.
"""

import asyncio
import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import yaml

SERVICE_DIR = Path("/Users/adalton/Development/github/VectorStep/service")
sys.path.insert(0, str(SERVICE_DIR))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from src.db.models import (  # noqa: E402
    PipelineRun, PipelineStep, RunFeedback, StepFeedback, StepPromptVersion,
)
from src.pipeline.versioning import prompt_hash  # noqa: E402

DB_URL = "postgresql+asyncpg://adalton@localhost:5432/vectorstep_demo"
DEMO_PIPELINE_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None

random.seed(1912)
NOW = datetime.utcnow()

MODEL = "claude-sonnet-4-5"
MODEL_FAST = "claude-haiku-4-5"
PROVIDER = "anthropic"

AGENT_VERSIONS = {
    "triage-agent": "4b82d0f1c9a3",
    "sre-agent": "9f31c7a2e5d8",
    "principal-sre": "c60d94ab12fe",
    "refund-assessor": "77aa31e0b5c4",
    "refund-processor": "d1490cf37b28",
    "refund-verifier": "3e5b8a92d604",
    "order-intake": "b2c748f0a1d9",
}

SERVICES = [
    ("checkout-api", "production", "payments"),
    ("payment-gateway", "production", "payments"),
    ("inventory-sync", "production", "platform"),
    ("search-indexer", "production", "platform"),
    ("notification-hub", "production", "platform"),
    ("auth-service", "production", "identity"),
]

ALERT_SUMMARIES = {
    "checkout-api": "P99 latency above 2.5s for 10m (SLO 800ms)",
    "payment-gateway": "5xx error rate 4.2% over 15m (threshold 1%)",
    "inventory-sync": "Consumer lag above 50k messages and climbing",
    "search-indexer": "Indexing queue saturation — 92% for 20m",
    "notification-hub": "Delivery failures to APNS above 6% over 10m",
    "auth-service": "Token issuance p95 above 1.2s (SLO 300ms)",
}

CAUSES = {
    "checkout-api": ("Connection-pool exhaustion against the orders DB after the 14:10 deploy doubled per-request queries",
                     "Rate steady at 210 rps; p99 2.9s vs 780ms baseline; DB pool at 100% with 41 waiters; errors flat"),
    "payment-gateway": ("Upstream acquirer returning intermittent 503s; retries amplifying load",
                        "5xx concentrated on /v2/charge; acquirer latency 8x baseline; retry volume tripled"),
    "inventory-sync": ("Partition rebalance storm after broker-3 restart left two consumers stalled",
                       "Lag growth 1.2k msg/s on partitions 7 and 11; other partitions draining normally"),
    "search-indexer": ("Bulk reindex job scheduled during peak overlapping with organic write load",
                       "Queue depth 92% and flat; bulk job writing 4k docs/s; organic writes 1.1k docs/s"),
    "notification-hub": ("Expired APNS auth key on one of three senders",
                         "Failures pinned to sender-2 at 100%; sender-1/3 nominal; error 403 InvalidProviderToken"),
    "auth-service": ("JWKS cache stampede after signing-key rotation",
                     "Issuance p95 1.4s; JWKS fetches 300x baseline; CPU nominal — latency is lock contention"),
}


def load_templates() -> dict[str, str]:
    """step_name -> prompt_template from the demo pipeline YAMLs."""
    out = {}
    for f in DEMO_PIPELINE_DIR.glob("*.yaml"):
        cfg = yaml.safe_load(f.read_text())
        for step in cfg.get("steps", []):
            if "name" in step and "prompt_template" in step:
                out[step["name"]] = step["prompt_template"]
    return out


TEMPLATES: dict[str, str] = {}
HASHES: dict[str, str] = {}


def iso(ts: datetime) -> str:
    return ts.isoformat(timespec="milliseconds") + "Z"


def log_event(log: list, ts: datetime, level: str, event: str, msg: str, **extra):
    log.append({"ts": iso(ts), "level": level, "event": event, "msg": msg, **extra})


def trust_report(*, S, V, S_after_V, mode, strategy, veto_floor, G, grounding_rep,
                 det_results, calib_rep, combined, threshold, on_low):
    det_passed = all(r["passed"] for r in det_results) if det_results else None
    return {
        "version": 5,
        "mode": "enforced",
        "signals": {
            "S": S, "S_after_V": S_after_V, "V": V, "V_mode": mode,
            "V_combination_strategy": strategy, "V_veto_floor": veto_floor,
            "G": G, "C": None, "D": det_passed,
        },
        "combined_trust": combined,
        "grounding": grounding_rep,
        "deterministic_checks": det_results,
        "calibration": calib_rep,
        "gate": {"policy": "trust_vector", "confidence_threshold": threshold,
                 "on_low_confidence": on_low},
    }


def grounding_report(score, service, n_claims=6, enforce=True, featured=False):
    cause, findings = CAUSES[service]
    claim_pool = [
        (f"The alerting metric is still breaching: {ALERT_SUMMARIES[service].split('(')[0].strip()}", True,
         "Metrics query at T+2m returned the breaching series"),
        (f"Probable cause: {cause.split(';')[0]}", True, "Supported by the comparison query in the trace"),
        ("Error budget for the 30d window is 61% consumed", True, "Budget query result present in trace"),
        ("The 14:10 deploy introduced the regression", False,
         "No deploy-diff or changelog evidence appears in the trace"),
        ("Rollback would restore baseline latency within 5 minutes", False,
         "Assertion about future behaviour — no evidence can support it"),
        ("Two similar incidents occurred in the last quarter", False,
         "No incident-history lookup appears in the trace"),
        ("Downstream consumers are unaffected", True, "Downstream RED query in trace shows nominal rates"),
        ("The on-call runbook's mitigation applies to this failure mode", True,
         "Runbook page was fetched; relevant section quoted"),
    ]
    n_supported = round(score * n_claims)
    supported = [c for c in claim_pool if c[1]][:n_supported]
    unsupported = [c for c in claim_pool if not c[1]][: n_claims - n_supported]
    claims = [{"claim": c, "supported": s, "evidence": e} for c, s, e in supported + unsupported]
    random.shuffle(claims)
    return {
        "computed": True, "agent": "grounding-judge", "model": MODEL, "provider": PROVIDER,
        "enforce": enforce, "score": score,
        "summary": f"{len(supported)} of {n_claims} load-bearing claims are supported by tool-call evidence in the step's own trace.",
        "claims": claims, "prompt": None, "raw_output": None,
    }


def det_result(ts_ms, passed=True, service="checkout-api"):
    return [{
        "name": "alert-still-firing", "type": "shell", "passed": passed,
        "detail": ("exit 0 — alert still firing for " + service) if passed
        else ("exit 1 — alert no longer firing for " + service),
        "duration_ms": ts_ms,
    }]


async def main():
    global TEMPLATES, HASHES
    TEMPLATES = load_templates()
    HASHES = {name: prompt_hash(t) for name, t in TEMPLATES.items()}

    engine = create_async_engine(DB_URL)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with sf() as s:
        for table in (StepFeedback, RunFeedback, StepPromptVersion, PipelineStep, PipelineRun):
            await s.execute(delete(table))
        await s.commit()

    runs, steps, run_fb, step_fb = [], [], [], []

    # ---------------- alert-triage-critical (production) ----------------
    # Chronological; calibration band 0.9-1.0 becomes validated (n>=20 marks)
    # partway through, after which high-confidence runs get replaced->escalated.
    marks_by_band = {9: [], 8: [], 7: [], 0: []}   # band -> list of label values
    n_runs = 92
    for i in range(n_runs):
        age_days = 30 * (1 - (i / n_runs)) ** 1.15  # denser recently
        t0 = NOW - timedelta(days=age_days, minutes=random.randint(0, 180))
        service, env, team = random.choice(SERVICES)
        run_id = str(uuid.uuid4())
        summary = ALERT_SUMMARIES[service]
        cause, findings = CAUSES[service]

        # first-line triage step
        fl_conf = round(random.uniform(0.74, 0.96), 2)
        fl_dur = random.randint(18_000, 55_000)
        fl_out = {
            "confidence": fl_conf,
            "summary": f"{service}: {summary.split('(')[0].strip().lower()} — credible, runbook found, ticket raised",
            "ticket": f"OPS-{random.randint(4100, 4900)}",
            "next_step_context": f"Focus on {findings.split(';')[0].lower()}",
        }

        # sre investigation step — the trust-vector star
        r = random.random()
        if r < 0.42: band = 9
        elif r < 0.72: band = 8
        elif r < 0.88: band = 7
        else: band = 0
        eff = {9: random.uniform(0.90, 0.98), 8: random.uniform(0.80, 0.895),
               7: random.uniform(0.70, 0.795), 0: random.uniform(0.42, 0.68)}[band]
        eff = round(eff, 2)
        S = min(0.99, round(eff + random.choice([0, 0, 0.01]), 2))
        V = round(max(0.35, eff - random.uniform(0.0, 0.18)), 2)
        vetoed = V < 0.60
        S_after_V = V if vetoed else S
        G = round(random.uniform(0.58, 0.97), 2)
        band_marks = marks_by_band[band]
        validated = len(band_marks) >= 20
        band_mean = round(sum(band_marks) / len(band_marks), 2) if band_marks else None

        calib_rep = {
            "bucket": {"step_name": "sre-investigation", "agent": "gateway:sre-agent",
                       "model": MODEL, "provider": PROVIDER},
            "bin": {"lo": band / 10 if band else 0.4, "hi": band / 10 + 0.1 if band else 0.7},
            "n": len(band_marks), "n_min": 20, "validated": validated,
            "raw": S_after_V,
            "calibrated": band_mean if validated else None,
            "on_uncalibrated": "proceed",
        }
        det_failed = random.random() < 0.03
        base = band_mean if validated else S_after_V
        combined = 0.0 if det_failed else round(min(base, G), 2)
        sre_status = "completed" if combined >= 0.75 else "escalated"
        if random.random() < 0.03:
            sre_status = "failed"
        run_status = sre_status if sre_status != "failed" else "failed"

        sre_dur = random.randint(110_000, 480_000)
        t_fl = t0 + timedelta(milliseconds=fl_dur)
        t_sre = t_fl + timedelta(milliseconds=sre_dur)
        sre_out = {
            "confidence": S, "proceed": True,
            "summary": f"{findings.split(';')[0]}",
            "findings": findings,
            "probable_cause": cause,
            "next_step_context": "Bounded mitigation per runbook; do not restart the primary",
        }
        ver_out = {
            "confidence": V,
            "summary": ("Reasoning holds; metric claims match the trace evidence" if V >= 0.75 else
                        "Partial agreement — the causal link to the deploy is asserted, not evidenced"),
        }

        log = []
        log_event(log, t0, "info", "run_started", f"Run started: alert-triage-critical ({service})")
        log_event(log, t0, "info", "step_started", "Step started: first-line-triage", step="first-line-triage")
        log_event(log, t_fl, "info", "step_completed",
                  f"Step completed: first-line-triage — confidence {fl_conf:.0%}", step="first-line-triage")
        log_event(log, t_fl, "info", "step_started", "Step started: sre-investigation", step="sre-investigation")
        log_event(log, t_sre, "info", "verifier_ran",
                  f"Verifier (critic): sre-investigation — V {V:.0%} vs self-report {S:.0%}"
                  + (" — VETO applied" if vetoed else ""), step="sre-investigation")
        log_event(log, t_sre, "info", "grounding_ran",
                  f"Grounding: sre-investigation — G {G:.0%} vs self-report {S:.0%}", step="sre-investigation")
        if validated:
            log_event(log, t_sre, "info", "calibration_applied",
                      f"Calibration (validated, n={len(band_marks)}): {S_after_V:.0%} replaced by measured {band_mean:.0%}",
                      step="sre-investigation")
        log_event(log, t_sre, "info" if not det_failed else "warn", "deterministic_check_ran",
                  f"Deterministic check {'passed' if not det_failed else 'FAILED'}: alert-still-firing (shell)",
                  step="sre-investigation")
        if sre_status == "escalated":
            log_event(log, t_sre, "warn", "step_escalated",
                      f"Step escalated: sre-investigation — trust {combined:.0%} < threshold 75%"
                      f" (self-report was {S:.0%})", step="sre-investigation")
        else:
            log_event(log, t_sre, "info", "step_completed",
                      f"Step completed: sre-investigation — trust {combined:.0%}", step="sre-investigation")
        log_event(log, t_sre, "info", "run_finished", f"Run finished: {run_status}")

        runs.append(PipelineRun(
            id=run_id, pipeline_name="alert-triage-critical", source="alertmanager",
            triggered_at=t0, status=run_status,
            normalised_context=json.dumps({
                "source": "alertmanager", "pipeline": "alert-triage-critical",
                "severity": "critical",
                "labels": {"service": service, "environment": env},
                "summary": summary, "team": team,
                "fingerprint": f"{service}:{summary[:24]}",
            }),
            raw_payload=json.dumps({"alerts": [{"labels": {"alertname": summary.split(" ")[0],
                                                           "service": service, "severity": "critical"},
                                                "annotations": {"summary": summary}}]}),
            completed_at=t_sre, logs=json.dumps(log),
            fingerprint=f"{service}:{summary[:24]}", team=team, stage="production",
        ))

        fl_step_id = str(uuid.uuid4())
        steps.append(PipelineStep(
            id=fl_step_id, run_id=run_id, step_name="first-line-triage", step_index=0,
            executor="gateway", agent="gateway:triage-agent", model=MODEL_FAST, provider=PROVIDER,
            prompt_hash=HASHES["first-line-triage"], agent_version=AGENT_VERSIONS["triage-agent"],
            prompt=TEMPLATES["first-line-triage"],
            raw_output=json.dumps({"response_text": json.dumps(fl_out)}),
            parsed_output=json.dumps(fl_out), status="completed",
            primary_confidence=fl_conf, effective_confidence=fl_conf,
            duration_ms=fl_dur, executed_at=t_fl,
            input_tokens=random.randint(1800, 3200), output_tokens=random.randint(300, 700),
        ))

        sre_step_id = str(uuid.uuid4())
        grounding_rep = grounding_report(G, service)
        steps.append(PipelineStep(
            id=sre_step_id, run_id=run_id, step_name="sre-investigation", step_index=1,
            executor="gateway", agent="gateway:sre-agent", model=MODEL, provider=PROVIDER,
            prompt_hash=HASHES["sre-investigation"], agent_version=AGENT_VERSIONS["sre-agent"],
            prompt=TEMPLATES["sre-investigation"],
            raw_output=json.dumps({"response_text": json.dumps(sre_out)}),
            parsed_output=json.dumps(sre_out),
            verifier_output=json.dumps(ver_out), verifier_mode="critic",
            verifier_agent="gateway:principal-sre", verifier_model=MODEL, verifier_provider=PROVIDER,
            status=sre_status,
            primary_confidence=S, verifier_confidence=V, effective_confidence=S_after_V,
            grounding_score=G,
            trust_report=json.dumps(trust_report(
                S=S, V=V, S_after_V=S_after_V, mode="critic", strategy="veto", veto_floor=0.60,
                G=G, grounding_rep=grounding_rep,
                det_results=det_result(random.randint(300, 1400), passed=not det_failed, service=service),
                calib_rep=calib_rep, combined=combined, threshold=0.75, on_low="escalate")),
            deterministic_passed=not det_failed,
            duration_ms=sre_dur, executed_at=t_sre,
            input_tokens=random.randint(4200, 9500), output_tokens=random.randint(900, 2100),
        ))

        # Human marks — the fuel for calibration. Overconfident at the top band.
        mark_p = {9: 0.94, 8: 0.92, 7: 0.85, 0: 0.5}[band]
        if random.random() < mark_p and i < n_runs - 3:  # newest runs unmarked
            if band == 9:
                outcome = random.choices(["correct", "partial", "incorrect"], [0.50, 0.24, 0.26])[0]
            elif band == 8:
                outcome = random.choices(["correct", "partial", "incorrect"], [0.75, 0.18, 0.07])[0]
            elif band == 7:
                outcome = random.choices(["correct", "partial", "incorrect"], [0.62, 0.23, 0.15])[0]
            else:
                outcome = random.choices(["correct", "partial", "incorrect"], [0.25, 0.25, 0.50])[0]
            marks_by_band[band].append({"correct": 1.0, "partial": 0.5, "incorrect": 0.0}[outcome])
            step_fb.append(StepFeedback(
                step_id=sre_step_id, run_id=run_id, pipeline_name="alert-triage-critical",
                step_name="sre-investigation", outcome=outcome,
                notes=random.choice([None, None, "Cause confirmed in the incident review",
                                     "Right metrics, wrong causal story", None]),
                submitted_at=t_sre + timedelta(hours=random.randint(2, 40)),
            ))

    # ---------------- checkout-refund-agent (testing) ----------------
    for i in range(26):
        age = 21 * (1 - i / 26)
        t0 = NOW - timedelta(days=age, minutes=random.randint(0, 240))
        run_id = str(uuid.uuid4())
        order = f"ORD-{random.randint(53000, 59000)}"
        amount = f"£{random.randint(18, 240)}.{random.choice(['00', '50', '99'])}"
        assess_conf = round(random.uniform(0.78, 0.96), 2)
        within = random.random() < 0.8
        a_dur = random.randint(25_000, 70_000)
        t_a = t0 + timedelta(milliseconds=a_dur)
        assess_out = {
            "confidence": assess_conf,
            "summary": f"{order}: {'within policy — item returned undamaged' if within else 'outside policy — exceeds 30-day window'}",
            "within_policy": within,
            "recommended_action": "refund_full" if within else "deny",
        }
        run_status = "completed"
        log = []
        log_event(log, t0, "info", "run_started", "Run started: checkout-refund-agent")
        log_event(log, t0, "info", "step_started", "Step started: assess-refund", step="assess-refund")
        log_event(log, t_a, "info", "step_completed",
                  f"Step completed: assess-refund — confidence {assess_conf:.0%}", step="assess-refund")

        assess_id = str(uuid.uuid4())
        steps.append(PipelineStep(
            id=assess_id, run_id=run_id, step_name="assess-refund", step_index=0,
            executor="gateway", agent="gateway:refund-assessor", model=MODEL, provider=PROVIDER,
            prompt_hash=HASHES["assess-refund"], agent_version=AGENT_VERSIONS["refund-assessor"],
            prompt=TEMPLATES["assess-refund"],
            raw_output=json.dumps({"response_text": json.dumps(assess_out)}),
            parsed_output=json.dumps(assess_out), status="completed",
            primary_confidence=assess_conf, effective_confidence=assess_conf,
            duration_ms=a_dur, executed_at=t_a,
            input_tokens=random.randint(1500, 2600), output_tokens=random.randint(200, 450),
        ))
        if random.random() < 0.85 and i < 24:
            step_fb.append(StepFeedback(
                step_id=assess_id, run_id=run_id, pipeline_name="checkout-refund-agent",
                step_name="assess-refund",
                outcome=random.choices(["correct", "partial", "incorrect"], [0.8, 0.14, 0.06])[0],
                notes=None, submitted_at=t_a + timedelta(hours=random.randint(1, 30)),
            ))

        t_end = t_a
        if within:
            i_conf = round(random.uniform(0.82, 0.97), 2)
            v_conf = round(max(0.6, i_conf - random.uniform(0.0, 0.15)), 2)
            eff = min(i_conf, v_conf)
            i_dur = random.randint(30_000, 90_000)
            t_i = t_a + timedelta(milliseconds=i_dur)
            t_end = t_i
            issue_status = "completed" if eff >= 0.85 else "escalated"
            if issue_status == "escalated":
                run_status = "escalated"
            issue_out = {
                "confidence": i_conf,
                "summary": f"Refunded {amount} for {order} — full refund per policy",
                "transaction_id": f"txn_{uuid.uuid4().hex[:10]}",
            }
            issue_id = str(uuid.uuid4())
            calib_rep = {
                "bucket": {"step_name": "issue-refund", "agent": "gateway:refund-processor",
                           "model": MODEL, "provider": PROVIDER},
                "bin": {"lo": int(eff * 10) / 10, "hi": int(eff * 10) / 10 + 0.1},
                "n": random.randint(2, 9), "n_min": 20, "validated": False,
                "raw": eff, "calibrated": None, "on_uncalibrated": "proceed",
            }
            steps.append(PipelineStep(
                id=issue_id, run_id=run_id, step_name="issue-refund", step_index=1,
                executor="gateway", agent="gateway:refund-processor", model=MODEL, provider=PROVIDER,
                prompt_hash=HASHES["issue-refund"], agent_version=AGENT_VERSIONS["refund-processor"],
                prompt=TEMPLATES["issue-refund"],
                raw_output=json.dumps({"response_text": json.dumps(issue_out)}),
                parsed_output=json.dumps(issue_out),
                verifier_output=json.dumps({"confidence": v_conf,
                                            "summary": "Independent re-assessment agrees with the refund decision"}),
                verifier_mode="independent", verifier_agent="gateway:refund-verifier",
                verifier_model=MODEL, verifier_provider=PROVIDER,
                status=issue_status,
                primary_confidence=i_conf, verifier_confidence=v_conf, effective_confidence=eff,
                trust_report=json.dumps(trust_report(
                    S=i_conf, V=v_conf, S_after_V=eff, mode="independent", strategy="minimum",
                    veto_floor=None, G=None, grounding_rep=None, det_results=None,
                    calib_rep=calib_rep, combined=eff, threshold=0.85, on_low="escalate")),
                duration_ms=i_dur, executed_at=t_i,
                input_tokens=random.randint(1200, 2200), output_tokens=random.randint(150, 350),
            ))
            log_event(log, t_a, "info", "step_started", "Step started: issue-refund", step="issue-refund")
            log_event(log, t_i, "info", "verifier_ran",
                      f"Verifier (independent): issue-refund — V {v_conf:.0%} vs self-report {i_conf:.0%}",
                      step="issue-refund")
            if issue_status == "escalated":
                log_event(log, t_i, "warn", "step_escalated",
                          f"Step escalated: issue-refund — trust {eff:.0%} < threshold 85%", step="issue-refund")
            else:
                log_event(log, t_i, "info", "step_completed",
                          f"Step completed: issue-refund — trust {eff:.0%}", step="issue-refund")
            if random.random() < 0.6 and i < 22:
                step_fb.append(StepFeedback(
                    step_id=issue_id, run_id=run_id, pipeline_name="checkout-refund-agent",
                    step_name="issue-refund",
                    outcome=random.choices(["correct", "partial"], [0.9, 0.1])[0],
                    notes=None, submitted_at=t_i + timedelta(hours=random.randint(1, 30)),
                ))
        else:
            log_event(log, t_a, "info", "step_skipped",
                      "Step skipped: issue-refund — when: condition false", step="issue-refund")
        log_event(log, t_end, "info", "run_finished", f"Run finished: {run_status}")

        runs.append(PipelineRun(
            id=run_id, pipeline_name="checkout-refund-agent", source="generic",
            triggered_at=t0, status=run_status,
            normalised_context=json.dumps({
                "source": "generic", "pipeline": "checkout-refund-agent",
                "labels": {"channel": "web"}, "summary": f"Refund requested: {order} ({amount})",
                "raw": {"event_type": "refund_requested", "order_id": order, "amount": amount,
                        "reason": "Item arrived damaged"},
            }),
            raw_payload=json.dumps({"event_type": "refund_requested", "order_id": order,
                                    "amount": amount, "reason": "Item arrived damaged"}),
            completed_at=t_end, logs=json.dumps(log), team="payments", stage="testing",
        ))

    # ---------------- payment-intake (production, healthy) ----------------
    for i in range(45):
        age = 30 * (1 - i / 45)
        t0 = NOW - timedelta(days=age, minutes=random.randint(0, 400))
        run_id = str(uuid.uuid4())
        conf = round(random.uniform(0.86, 0.99), 2)
        dur = random.randint(9_000, 28_000)
        t1 = t0 + timedelta(milliseconds=dur)
        order = f"ORD-{random.randint(53000, 59000)}"
        out = {"confidence": conf, "summary": f"Filed {order} from web checkout — validated and enriched",
               "order_ref": order}
        log = []
        log_event(log, t0, "info", "run_started", "Run started: payment-intake")
        log_event(log, t0, "info", "step_started", "Step started: order-intake", step="order-intake")
        log_event(log, t1, "info", "step_completed",
                  f"Step completed: order-intake — confidence {conf:.0%}", step="order-intake")
        log_event(log, t1, "info", "run_finished", "Run finished: completed")
        runs.append(PipelineRun(
            id=run_id, pipeline_name="payment-intake", source="generic",
            triggered_at=t0, status="completed",
            normalised_context=json.dumps({
                "source": "generic", "pipeline": "payment-intake",
                "labels": {"channel": "web"}, "summary": f"Order created: {order}",
                "raw": {"event_type": "order_created", "order_id": order, "channel": "web"},
            }),
            raw_payload=json.dumps({"event_type": "order_created", "order_id": order, "channel": "web"}),
            completed_at=t1, logs=json.dumps(log), team="payments", stage="production",
        ))
        steps.append(PipelineStep(
            id=str(uuid.uuid4()), run_id=run_id, step_name="order-intake", step_index=0,
            executor="gateway", agent="gateway:order-intake", model=MODEL_FAST, provider=PROVIDER,
            prompt_hash=HASHES["order-intake"], agent_version=AGENT_VERSIONS["order-intake"],
            prompt=TEMPLATES["order-intake"],
            raw_output=json.dumps({"response_text": json.dumps(out)}),
            parsed_output=json.dumps(out), status="completed",
            primary_confidence=conf, effective_confidence=conf,
            duration_ms=dur, executed_at=t1,
            input_tokens=random.randint(700, 1400), output_tokens=random.randint(90, 220),
        ))
        if random.random() < 0.45:
            run_fb.append(RunFeedback(
                run_id=run_id, pipeline_name="payment-intake",
                outcome=random.choices(["correct", "partial"], [0.9, 0.1])[0],
                notes=None, submitted_at=t1 + timedelta(hours=random.randint(1, 48)),
            ))

    # ---------------- The FEATURED run: the landing-page story ----------------
    t0 = NOW - timedelta(hours=3, minutes=17)
    run_id = str(uuid.uuid4())
    service, env, team = "checkout-api", "production", "payments"
    summary = ALERT_SUMMARIES[service]
    cause, findings = CAUSES[service]
    fl_conf = 0.91
    fl_dur, sre_dur = 34_000, 214_000
    t_fl = t0 + timedelta(milliseconds=fl_dur)
    t_sre = t_fl + timedelta(milliseconds=sre_dur)
    S, V, S_after_V, band_mean, G, combined = 0.95, 0.85, 0.95, 0.62, 0.50, 0.50
    fl_out = {"confidence": fl_conf,
              "summary": "checkout-api p99 latency breach — credible, runbook found, OPS-4831 raised",
              "ticket": "OPS-4831",
              "next_step_context": "Focus on DB connection-pool saturation visible since 14:10"}
    sre_out = {"confidence": S, "proceed": True,
               "summary": findings.split(";")[0],
               "findings": findings, "probable_cause": cause,
               "next_step_context": "Scale the pool and revert the 14:10 deploy behind a flag"}
    ver_out = {"confidence": V,
               "summary": "Metric claims check out against the trace; causal link to the deploy is thinner than the prose suggests"}
    calib_rep = {
        "bucket": {"step_name": "sre-investigation", "agent": "gateway:sre-agent",
                   "model": MODEL, "provider": PROVIDER},
        "bin": {"lo": 0.9, "hi": 1.0}, "n": 34, "n_min": 20, "validated": True,
        "raw": S_after_V, "calibrated": band_mean, "on_uncalibrated": "proceed",
    }
    grounding_rep = grounding_report(G, service, featured=True)
    log = []
    log_event(log, t0, "info", "run_started", "Run started: alert-triage-critical (checkout-api)")
    log_event(log, t0, "info", "step_started", "Step started: first-line-triage", step="first-line-triage")
    log_event(log, t_fl, "info", "step_completed",
              "Step completed: first-line-triage — confidence 91%", step="first-line-triage")
    log_event(log, t_fl, "info", "step_started", "Step started: sre-investigation", step="sre-investigation")
    log_event(log, t_sre, "info", "verifier_ran",
              "Verifier (critic): sre-investigation — V 85% vs self-report 95% — above veto floor, no change",
              step="sre-investigation")
    log_event(log, t_sre, "info", "calibration_applied",
              "Calibration (validated, n=34): 95% replaced by measured 62% for this agent/model at 90-100%",
              step="sre-investigation")
    log_event(log, t_sre, "info", "grounding_ran",
              "Grounding (enforced): sre-investigation — G 50% caps combined trust", step="sre-investigation")
    log_event(log, t_sre, "info", "deterministic_check_ran",
              "Deterministic check passed: alert-still-firing (shell)", step="sre-investigation")
    log_event(log, t_sre, "warn", "step_escalated",
              "Step escalated: sre-investigation — trust 50% < threshold 75% (self-report was 95%)",
              step="sre-investigation")
    log_event(log, t_sre, "info", "notification_sent", "Escalation notification sent (telegram)")
    log_event(log, t_sre, "info", "run_finished", "Run finished: escalated")
    runs.append(PipelineRun(
        id=run_id, pipeline_name="alert-triage-critical", source="alertmanager",
        triggered_at=t0, status="escalated",
        normalised_context=json.dumps({
            "source": "alertmanager", "pipeline": "alert-triage-critical", "severity": "critical",
            "labels": {"service": service, "environment": env}, "summary": summary, "team": team,
            "fingerprint": f"{service}:latency-p99",
        }),
        raw_payload=json.dumps({"alerts": [{"labels": {"alertname": "CheckoutLatencyP99",
                                                       "service": service, "severity": "critical"},
                                            "annotations": {"summary": summary}}]}),
        completed_at=t_sre, logs=json.dumps(log),
        fingerprint=f"{service}:latency-p99", team=team, stage="production",
    ))
    steps.append(PipelineStep(
        id=str(uuid.uuid4()), run_id=run_id, step_name="first-line-triage", step_index=0,
        executor="gateway", agent="gateway:triage-agent", model=MODEL_FAST, provider=PROVIDER,
        prompt_hash=HASHES["first-line-triage"], agent_version=AGENT_VERSIONS["triage-agent"],
        prompt=TEMPLATES["first-line-triage"],
        raw_output=json.dumps({"response_text": json.dumps(fl_out)}),
        parsed_output=json.dumps(fl_out), status="completed",
        primary_confidence=fl_conf, effective_confidence=fl_conf,
        duration_ms=fl_dur, executed_at=t_fl, input_tokens=2412, output_tokens=486,
    ))
    steps.append(PipelineStep(
        id=str(uuid.uuid4()), run_id=run_id, step_name="sre-investigation", step_index=1,
        executor="gateway", agent="gateway:sre-agent", model=MODEL, provider=PROVIDER,
        prompt_hash=HASHES["sre-investigation"], agent_version=AGENT_VERSIONS["sre-agent"],
        prompt=TEMPLATES["sre-investigation"],
        raw_output=json.dumps({"response_text": json.dumps(sre_out)}),
        parsed_output=json.dumps(sre_out),
        verifier_output=json.dumps(ver_out), verifier_mode="critic",
        verifier_agent="gateway:principal-sre", verifier_model=MODEL, verifier_provider=PROVIDER,
        status="escalated",
        primary_confidence=S, verifier_confidence=V, effective_confidence=S_after_V,
        grounding_score=G,
        trust_report=json.dumps(trust_report(
            S=S, V=V, S_after_V=S_after_V, mode="critic", strategy="veto", veto_floor=0.60,
            G=G, grounding_rep=grounding_rep,
            det_results=det_result(842, passed=True, service=service),
            calib_rep=calib_rep, combined=combined, threshold=0.75, on_low="escalate")),
        deterministic_passed=True,
        duration_ms=sre_dur, executed_at=t_sre, input_tokens=7204, output_tokens=1655,
    ))

    # ---------------- prompt version registry ----------------
    versions = []
    for name, template in TEMPLATES.items():
        h = HASHES[name]
        if h:
            versions.append(StepPromptVersion(
                prompt_hash=h, step_name=name, template=template,
                first_seen_at=NOW - timedelta(days=30), last_seen_at=NOW,
            ))

    async with sf() as s:
        s.add_all(runs)
        s.add_all(versions)
        await s.commit()
    async with sf() as s:
        s.add_all(steps)
        await s.commit()
    async with sf() as s:
        s.add_all(step_fb)
        s.add_all(run_fb)
        await s.commit()

    print(f"Seeded: {len(runs)} runs, {len(steps)} steps, "
          f"{len(step_fb)} step marks, {len(run_fb)} run marks")
    band9 = marks_by_band[9]
    if band9:
        print(f"0.9-1.0 band: n={len(band9)}, mean_label={sum(band9)/len(band9):.2f}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
