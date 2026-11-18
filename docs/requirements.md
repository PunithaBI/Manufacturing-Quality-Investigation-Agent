# Manufacturing Quality Investigation Agent

## Phase 1 — Requirements Specification

**Project:** Manufacturing Quality Investigation Agent  
**Company:** NordWind Energy Systems *(synthetic)*  
**Product:** NW-250 Wind Turbine  
**Primary User:** QA Engineer  
**Methodology:** 8D / Root Cause Analysis  
**Phase:** 1 — Business Problem + Requirements  
**Status:** Draft for Phase 1 Review

---

# 1. Requirement Philosophy

The system is an **AI-assisted investigation system**, not an autonomous quality-decision system.

Its primary responsibility is to help a QA Engineer:

1. Understand the NCR.
2. Plan the investigation.
3. Find relevant evidence.
4. Find similar historical cases.
5. Identify what is known and unknown.
6. Generate potential RCA hypotheses.
7. Recommend evidence-gathering actions.
8. Produce a traceable investigation report.

The system must clearly separate:

**Facts → Evidence → Hypotheses → Recommendations → Human Decisions**

# 2. Functional Requirements

## FR-01 — NCR Intake

The system shall accept an NCR investigation case containing available information such as NCR identifier, NCR type, date, product, assembly, component, failure description, observations, severity, initial action, status, and supporting information.

The system shall support both internal and external NCRs.

## FR-02 — NCR Understanding

The system shall analyze the NCR and extract:

- Reported problem
- Observed symptom
- Product
- Assembly
- Component
- Operating condition
- Failure mode
- Customer/internal observation
- Initial actions
- Known facts
- Unknown information

The system shall identify ambiguity rather than silently resolving it.

## FR-03 — Investigation Planning

The system shall create an investigation plan based on the NCR.

The plan may include evidence to search, historical cases to investigate, technical documentation, manufacturing data, inspection/test data, maintenance/service information, supplier information, and questions requiring human investigation.

## FR-04 — Evidence Retrieval

The system shall retrieve relevant investigation evidence from authorized enterprise sources, including where available:

- NCR repository
- Product information
- BOM
- Production data
- Work-order data
- Inspection results
- Test results
- Maintenance records
- Supplier information
- Historical NCRs
- Technical documents
- Customer complaints
- Previous 8D reports
- Corrective/preventive actions

The source of retrieved evidence must be preserved.

## FR-05 — Historical Investigation

The system shall identify potentially relevant historical NCRs and previous investigations.

Historical matching may consider product, assembly, component, failure mode, symptom, operating condition, supplier, technical characteristics, and previous root-cause findings.

Historical similarity does not prove that the current NCR has the same root cause.

## FR-06 — Evidence Assessment

The system shall assess evidence against investigation hypotheses and claims.

### Evidence statuses

| Status | Meaning |
|---|---|
| SUPPORTED | Evidence supports the claim/hypothesis |
| CONTRADICTING | Evidence conflicts with the claim/hypothesis |
| PARTIAL | Evidence provides incomplete support |
| MISSING | Required evidence was not found |
| IRRELEVANT | Evidence does not materially support the investigation |

Each important evidence item should include its source and relevance.

## FR-07 — RCA Hypothesis Generation

The system shall generate potential root-cause hypotheses.

Each hypothesis should include:

- Potential cause
- Reason for consideration
- Supporting evidence
- Contradicting evidence
- Missing evidence
- Confidence/strength indicator
- Recommended investigation action

The system must not convert a hypothesis into a confirmed RCA.

## FR-08 — Evidence Gap Detection

The system shall identify information required to strengthen or reject investigation hypotheses.

Examples:

- Missing inspection result
- Missing vibration measurement
- Missing temperature measurement
- Missing production batch information
- Missing supplier lot information
- Missing maintenance history
- Missing previous repair information

The system must explicitly distinguish evidence found from evidence required but missing.

## FR-09 — Investigation Recommendations

The system shall recommend next investigation actions, such as:

- Inspect a component
- Retrieve a test result
- Check a production batch
- Review a work order
- Review supplier records
- Compare measurements
- Review maintenance history
- Search similar NCRs
- Consult Service Engineering
- Obtain customer information

Recommendations are advisory and require human review before consequential execution.

## FR-10 — Traceable Investigation Report

The system shall produce a structured investigation package containing:

1. NCR Summary
2. Product / Component
3. Known Facts
4. Historical Evidence
5. Technical Evidence
6. Potential Causes
7. Evidence for Each Cause
8. Evidence Gaps
9. Recommended Next Steps
10. Corrective-Action Candidates
11. Human Review

## FR-11 — Evidence-Grounded Reasoning

The system shall distinguish between:

- Retrieved fact
- Derived observation
- Historical analogy
- Hypothesis
- Recommendation
- Human decision

Generated information must not be represented as retrieved evidence.

## FR-12 — Uncertainty Handling

The system shall explicitly communicate uncertainty.

Examples:

- "Insufficient evidence to determine root cause."
- "Two potential causes remain plausible."
- "Historical case is similar but does not establish the current root cause."
- "Required inspection evidence was not available."
- "The available evidence is contradictory."

The system should prefer escalation over unsupported certainty.

## FR-13 — Human Review Gate

The system shall provide a human review point before consequential quality decisions.

Human review is required for:

- Final RCA
- NCR closure
- Product release
- Quarantine release
- Corrective-action approval
- Production parameter changes
- Supplier decisions
- Customer communication

## FR-14 — Product Improvement Signal

The system may identify potential product-improvement signals, including:

- Recurring failure modes
- Repeated component failure
- High warranty impact
- Repeated customer complaints
- Similar NCRs across products
- Supplier-related recurring failures

These are signals for Product Owner review, not autonomous product changes.

# 3. Non-Functional Requirements

## NFR-01 — Traceability

Important outputs must be traceable to supporting evidence.

## NFR-02 — Auditability

Investigation activity should record:

- Information retrieved
- Sources used
- Hypotheses generated
- Evidence supporting them
- Recommendations produced
- Human decisions

## NFR-03 — Human Oversight

The system must not autonomously execute consequential quality decisions.

## NFR-04 — Fail-Safe Behavior

When evidence is insufficient, the system shall:

1. State that evidence is insufficient.
2. Identify what is missing.
3. Explain why it matters.
4. Recommend an appropriate next step.
5. Escalate when necessary.

## NFR-05 — Reliability

The system should handle:

- Missing documents
- Empty search results
- Tool failures
- Duplicate evidence
- Conflicting evidence
- Malformed NCR input
- Incomplete records

without fabricating information.

## NFR-06 — Security

Enterprise investigation data must only be accessed through authorized interfaces and permissions.

Detailed security controls will be defined in Phase 8.

## NFR-07 — Reproducibility

An investigation should be reproducible from:

- NCR input
- Retrieved evidence
- System reasoning/output
- Configuration
- Human decisions

## NFR-08 — Performance

The system should reduce manual evidence-search effort where practical.

Actual performance targets will be established after a baseline is available. No unsupported time-reduction target will be invented.

# 4. AI Decision Boundaries

## AI MAY

- Read authorized NCR information.
- Search authorized enterprise information.
- Retrieve relevant technical documents.
- Find historical NCRs.
- Summarize evidence.
- Identify patterns.
- Identify evidence gaps.
- Generate RCA hypotheses.
- Compare competing hypotheses.
- Recommend next investigation steps.
- Draft an investigation report.
- Identify potential product-improvement signals.

## AI MAY NOT ACT AUTONOMOUSLY

The AI shall not:

- Declare final root cause.
- Close an NCR.
- Release quarantined product.
- Change production parameters.
- Change product/BOM specifications.
- Approve corrective actions.
- Approve suppliers.
- Make final supplier decisions.
- Communicate final quality decisions to customers.
- Approve customer compensation.

# 5. KPI Framework

## 5.1 AI/System KPIs

### Evidence Retrieval Relevance
Percentage of retrieved evidence judged relevant.

### Citation/Evidence Accuracy
Percentage of evidence references that correctly support their associated claims.

### Evidence-Gap Detection
Ability to identify important missing evidence.

### Historical Case Relevance
Quality of retrieved similar NCRs.

### RCA Hypothesis Quality
Human assessment of whether generated hypotheses are technically useful and evidence-grounded.

### Unsupported Claim Rate
Percentage of generated claims that are unsupported by available evidence. This should be minimized.

### Investigation Report Completeness
Whether required investigation sections are present.

### Human Acceptance / Usefulness
QA reviewer assessment of whether the output is useful.

## 5.2 Business KPIs

Potential measures include:

- QA investigation effort
- Evidence-search effort
- Investigation consistency
- Repeated investigations
- Visibility of recurring failure modes
- Warranty impact
- Customer complaints
- Supplier-related issues
- Product-improvement opportunities identified

Actual business impact should only be measured after a baseline is established.

# 6. KPI Measurement Principle

### Prototype metrics

Metrics measurable with synthetic data:

- Retrieval relevance
- Citation accuracy
- Evidence-gap detection
- Hypothesis quality
- Unsupported claim rate
- Report completeness

### Real business metrics

Metrics requiring real organizational data:

- Warranty-cost reduction
- Customer-complaint reduction
- Actual QA investigation time
- Reduction in repeated failures
- Actual product-improvement impact

The prototype must not claim real-world business improvement without evidence.

# 7. Known Unknowns

The following require validation in a real manufacturing environment:

1. Exact QA investigation workflow
2. Exact SharePoint structure
3. Exact metadata available
4. Exact 8D template
5. Required evidence for different failure modes
6. Exact Service Engineering RCA workflow
7. Historical NCR search methodology
8. Exact rules for product-improvement escalation
9. Baseline investigation effort
10. Baseline evidence-search effort
11. Baseline warranty impact
12. Actual recurrence rates

For the capstone, these will be represented using clearly documented synthetic assumptions.

# 8. Phase 1 Acceptance Criteria

Phase 1 requirements are acceptable when the system can be described as:

> **Given an internal or external manufacturing NCR, the system shall help a QA Engineer understand the issue, retrieve relevant evidence and historical cases, identify missing or conflicting evidence, generate evidence-backed RCA hypotheses, recommend investigation actions, and produce a traceable investigation package for human review.**

And:

> **The system shall not autonomously make final quality decisions.**

# 9. Phase 1 Requirement Summary

| Area | Requirement |
|---|---|
| Primary User | QA Engineer |
| Secondary User | Product Owner |
| Supporting Role | Service Engineering |
| NCR Types | Internal + External |
| Investigation Method | 8D / RCA |
| Core Problem | Manual, fragmented evidence-driven investigation |
| Core AI Role | Investigation assistant |
| Evidence | Structured + unstructured |
| Historical Analysis | Historical NCRs / previous investigations |
| RCA | Hypothesis generation, not autonomous RCA approval |
| Missing Evidence | Explicitly identified |
| Output | Traceable investigation package |
| Human Approval | Required for consequential decisions |
| Product Improvement | Signal detection, not autonomous action |
| Primary Quality Principle | Evidence before conclusion |
| Safety Principle | No unsupported root-cause claims |

# 10. Phase 1 Exit Gate

Before moving to Phase 2:

- [x] Business problem
- [x] Business objective
- [x] Primary user
- [x] Secondary stakeholders
- [x] Internal/external NCR distinction
- [x] Business scope
- [x] Functional requirements
- [x] Non-functional requirements
- [x] AI decision boundaries
- [x] Evidence-grounding principle
- [x] Human approval boundaries
- [x] KPI framework
- [x] Known unknowns
- [x] Synthetic-data assumption

**Phase 1 status: READY FOR PHASE 2 REVIEW**

**Next phase:** Phase 2 — Manufacturing Data Model
