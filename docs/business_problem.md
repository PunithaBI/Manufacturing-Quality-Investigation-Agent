# Manufacturing Quality Investigation Agent

## Phase 1 — Business Problem & Business Requirements

**Project:** Manufacturing Quality Investigation Agent  
**Company:** NordWind Energy Systems *(synthetic company for the capstone)*  
**Product:** NW-250 Wind Turbine  
**Primary Quality Process:** Non-Conformance Report (NCR) Investigation  
**Phase:** 1 — Business Problem + Requirements  
**Status:** Draft for Phase 1 Review

---

# 1. Business Context

Manufacturing organizations investigate Non-Conformance Reports (NCRs) raised when a product or component does not meet expected quality, performance, reliability, or customer requirements.

NCRs may be:

- **Internal NCRs** — identified within the manufacturing organization.
- **External NCRs** — reported by a customer and transferred through the Repair & Warranty (RW) function to the Quality Assurance (QA) department.

The investigation process involves collecting information from multiple enterprise sources, understanding the reported problem, searching historical NCRs and technical documentation, determining what evidence is available, investigating possible causes, and preparing an investigation/8D report.

For the capstone, the organization and data are synthetic. The business requirements are based on Product Owner input, while operational details that have not been directly validated with QA or Service Engineering are explicitly treated as assumptions.

# 2. Current Investigation Process

The current NCR process contains five major stages:

1. **NCR Creation / Registration**
2. **Coordination / Assignment**
3. **Case Handling / Investigation**
4. **Evaluation / Closure Review**
5. **Closed NCR**

The greatest investigation effort occurs during:

- Case Handling / Investigation
- Evaluation / Closure Review

Root Cause Analysis (RCA) is particularly difficult for cases where:

- The NCR description is vague.
- The customer claim is unclear.
- Supporting information is missing.
- The technical problem is unfamiliar.
- Relevant evidence is distributed across different SharePoint locations.
- Similar historical NCRs are difficult to identify.
- Available evidence is incomplete or contradictory.

The current investigation process is largely manual.

# 3. Business Problem

The primary business problem is **not simply that NCRs take too long**.

The deeper problem is that NCR investigation and Root Cause Analysis depend heavily on manual evidence discovery and human investigation effort.

Relevant information may exist across:

- NCR records
- Product information
- Bills of Material (BOM)
- Production and work-order information
- Inspection and test results
- Maintenance records
- Supplier information
- Historical NCRs
- Technical documentation
- Customer complaints
- Previous corrective/preventive actions
- Previous 8D reports

Investigators currently need to manually search these sources and determine which information is relevant to the current NCR.

This creates several risks:

### 3.1 Evidence Discovery Effort
Investigators can spend significant effort locating relevant historical NCRs, technical documents, service information, and manufacturing evidence.

### 3.2 Incomplete Investigations
If important evidence is unavailable or difficult to find, investigators may have difficulty determining the actual cause of a failure.

### 3.3 Inconsistent Investigation Quality
Different investigators may search different sources, identify different historical cases, or document evidence differently.

### 3.4 Difficult RCA
Root Cause Analysis can become particularly difficult when several causes are technically plausible, evidence is incomplete, evidence contradicts another source, the reported symptom is vague, or the investigator does not have deep technical knowledge of the failure.

### 3.5 Repeated Failure Visibility
Individual NCRs may be resolved without identifying broader recurring failure patterns.

This can make it harder for Product Owners to identify opportunities for product improvement.

### 3.6 Business Impact
Quality failures can contribute to:

- Warranty cost
- Customer complaints
- Repeated failures
- Production downtime
- Scrap and rework
- Supplier issues
- Unnecessary quarantine

The Product Owner identified **warranty cost, customer complaints, and repeated failures** as particularly important business outcomes.

# 4. Business Opportunity

The opportunity is to build an AI-assisted investigation system that acts as an **investigation assistant for QA engineers**.

The system should help the investigator answer:

> "What do we know about this NCR, what evidence supports it, what similar cases have occurred, what information is missing, what possible causes should be investigated, and what should the investigator do next?"

The system should not replace the Quality Engineer.

Instead, it should reduce the manual effort required to gather and organize evidence while improving traceability and consistency.

# 5. Business Objective

> **To assist QA engineers in investigating manufacturing NCRs by automatically organizing the case, retrieving relevant evidence, identifying historical similarities, detecting evidence gaps, generating evidence-backed RCA hypotheses, and producing a traceable investigation package for human review.**

The system should make investigation more:

- Evidence-driven
- Traceable
- Consistent
- Efficient
- Repeatable
- Transparent

# 6. Primary User

## QA Engineer

The QA Engineer is the primary user.

The QA Engineer:

- Receives or owns the NCR investigation.
- Reviews the reported problem.
- Searches for evidence.
- Investigates possible causes.
- Performs or coordinates RCA.
- Creates the 8D/investigation report.
- Makes the final quality decision.
- Closes the NCR.

The AI system therefore acts primarily as an **investigation assistant to the QA Engineer**.

# 7. Secondary Stakeholders

## Product Owner

The Product Owner is responsible for product improvement and may use investigation results to identify recurring failure modes, significant warranty problems, customer-impacting issues, and product-improvement opportunities.

Not every NCR should automatically become a product-improvement initiative. The system should therefore identify potential product-improvement signals rather than automatically initiating product changes.

## Service Engineering

Service Engineering provides technical expertise for difficult or complex RCA cases.

## Repair & Warranty

Repair & Warranty participates in the external NCR process by receiving customer issues and transferring relevant cases to QA.

# 8. NCR Process Scope

## External NCR

```text
Customer
   ↓
Repair & Warranty
   ↓
QA
   ↓
NCR Investigation
   ↓
RCA / 8D
   ↓
Human Review
   ↓
NCR Closure
```

## Internal NCR

```text
Internal Quality Issue
   ↓
QA
   ↓
NCR Investigation
   ↓
RCA / 8D
   ↓
Human Review
   ↓
NCR Closure
```

# 9. Example Business Scenario

**NCR:** NCR-2026-0042  
**Type:** External  
**Product:** NW-250 Wind Turbine  
**Assembly:** GBX-250 Gearbox  
**Reported issue:** Abnormal vibration/noise during operation  
**Customer observation:** Vibration increases during high-load operation  
**Initial action:** Customer stopped turbine and requested inspection  
**Status:** Open

The investigator may need to determine:

- What exactly failed?
- Which component is involved?
- Have similar gearbox failures occurred?
- What technical documents are relevant?
- What manufacturing evidence exists?
- What service evidence exists?
- Is bearing failure plausible?
- Is gear alignment plausible?
- Is the vibration sensor itself producing a false signal?
- What evidence supports each possibility?
- What evidence is missing?
- What should be inspected next?

The AI system should organize this investigation without claiming that a hypothesis is the confirmed root cause.

# 10. Expected Business Outcome

The intended business outcome is **better-supported and more traceable NCR investigations**.

The system should help achieve:

- Reduced investigation effort
- Faster evidence discovery
- Better investigation traceability
- More consistent investigation reports
- Better visibility of historical failure patterns
- Better identification of evidence gaps
- Better support for RCA
- Improved visibility of recurring quality problems
- Better identification of potential product-improvement opportunities

Actual reductions in warranty cost, customer complaints, downtime, or repeated failures must be validated using real production data and must not be claimed from the prototype alone.

# 11. Project Scope

## In Scope

1. NCR intake
2. NCR understanding
3. Investigation planning
4. Evidence discovery
5. Historical NCR search
6. Technical-document retrieval
7. Evidence classification
8. Evidence-gap identification
9. RCA hypothesis generation
10. Investigation recommendations
11. Traceable investigation reporting
12. Human review

## Out of Scope

The AI system will not autonomously:

- Close an NCR
- Approve the final Root Cause
- Release quarantined products
- Change production parameters
- Change a BOM
- Approve corrective actions
- Make supplier decisions
- Communicate final quality decisions to customers
- Approve customer compensation
- Replace QA or Service Engineering judgment

# 12. Core Design Principle

> **AI assists investigation; humans make quality decisions.**

The system may propose an evidence-backed hypothesis, but it must not state that a hypothesis is the confirmed root cause unless the available evidence and human investigation have established that conclusion.

# 13. Evidence-First Principle

Every important investigation conclusion should be connected to evidence.

The system should distinguish between:

- **SUPPORTED**
- **PARTIAL**
- **CONTRADICTING**
- **MISSING**
- **IRRELEVANT**

Missing evidence must never be silently converted into an assumption.

# 14. Phase 1 Boundary

Phase 1 defines what problem the system solves and what the system is allowed to do.

The following are intentionally deferred to later phases:

- Manufacturing database schema
- Synthetic database implementation
- API design
- RAG implementation
- Vector database
- LLM selection
- Prompt engineering
- Agent orchestration
- Multi-agent architecture
- Evaluation implementation
- Security implementation
- Production deployment

# 15. Confirmed vs Assumed Information

## Confirmed from Product Owner

- Two NCR types exist: internal and external.
- External NCRs originate from customers through Repair & Warranty.
- QA owns investigation and closure.
- QA uses 8D for RCA.
- RCA is one of the most difficult parts of the process.
- Investigators search internal SharePoint sources.
- NCR, product, BOM, production/work-order, supplier, historical NCR, technical-document, and customer-complaint information may exist.
- Human approval is required for final quality decisions.
- Warranty cost, customer complaints, and repeated failures are important business outcomes.

## Assumptions for the Capstone

Because QA and Service Engineering interviews are not available, the following will be represented using realistic synthetic data:

- Exact SharePoint structure
- Exact metadata structure
- Exact QA search workflow
- Exact 8D report format
- Exact investigation evidence requirements
- Exact Service Engineering workflow
- Historical NCR similarity methodology
- Evidence availability by failure mode
- Investigation effort measurements
- Baseline business metrics

No real company metrics will be invented.

# 16. Phase 1 Success Definition

Phase 1 is complete when:

- The business problem is clearly defined.
- Primary and secondary users are identified.
- Internal and external NCR workflows are defined at a business level.
- Scope and boundaries are documented.
- AI decision boundaries are documented.
- Functional requirements are defined.
- Non-functional requirements are defined.
- KPIs are identified.
- Unknown operational details are explicitly documented as assumptions.
- Requirements are stable enough to design the data model in Phase 2.

# 17. Phase 1 Decision

### Core problem
**Manual, fragmented, evidence-intensive NCR investigation and RCA.**

### Core user
**QA Engineer.**

### Core AI role
**Investigation assistant.**

### Core output
**Traceable, evidence-backed investigation package with RCA hypotheses, evidence gaps, and recommended next steps.**

### Human responsibility
**Final RCA, corrective actions, product/quality decisions, and NCR closure remain with humans.**
