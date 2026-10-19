# WorkFlowShieldX — Autonomous Freelance Milestone Arbiter Protocol

> **Track:** Subjective Consensus / AI Governance / Future of Work / Agentic Economy  
> **Network:** GenLayer studionet (Chain ID: `61999` / `0xF1EF`)  
> **Target Environment:** [GenLayer Studio](https://studio.genlayer.com)  
> **Execution Engine:** GenVM / Optimistic Democracy Semantic Consensus  
> **Contract Source:** [`contracts/work_flow_shield_x.py`](contracts/work_flow_shield_x.py)  

---

## 1. Live Deployment & On-Chain Verification

The **WorkFlowShieldX** Intelligent Contract is deployed, finalized, and verified on GenLayer **studionet**:

- **CONTRACT_ADDRESS:** `0x62F5F48A60040e88c1Ea5A8909c220CBCb41EE48`
- **DEPLOYER_ADDRESS:** `0xf2949c471F6116042807772dd788D6fA0905DC97`
- **NETWORK:** `studionet` (Chain ID: `61999` / `0xF1EF`)
- **RPC_URL:** `https://studio.genlayer.com/api`
- **RECEIPT_STATUS:** `5` (FINALIZED)
- **RESULT:** `6` (SUCCESS)
- **CONSENSUS_VOTES:** 5/5 Validators Agreed (`agree`)
- **Deployment Details:** [`deployment.json`](deployment.json)

---

## 2. Core Problem & The 1-Line Pitch

### The Core Problem
Freelance platforms (Upwork, Fiverr) intermediate over \$5B annually, extracting 10–20% in fees and running centralized dispute mediation prone to delays, opaque human biases, and unfair chargebacks:
1. **Centralized Platform Monopoly:** Intermediaries hold absolute custody of milestone escrow, often taking weeks to resolve basic disputes without technical inspection of code deliverables.
2. **Asymmetric Risk for Freelancers & Clients:** Freelancers risk non-payment after hours of legitimate engineering work; clients risk paying for broken, non-functional, or plagiarized submissions.
3. **Legacy Blockchain Blindness:** Solidity and EVM contracts can lock escrow, but cannot view external deliverables (GitHub PRs, Figma, live URLs) or assess natural-language requirements (PRD).

### Why This Primitive DIES Without GenLayer (The 1-Line Pitch)
> *"Legacy blockchains cannot read external deliverables or reason over natural-language project requirements; without GenLayer's native web rendering (`gl.nondet.web.render`) and LLM validator jury consensus (`gl.vm.run_nondet`), an autonomous, decentralized freelance milestone arbiter protocol is fundamentally impossible."*

---

## 3. Architecture & System Flow

```mermaid
flowchart TD
    subgraph Client["1. Client Creation & Escrow"]
        C["Client"] -->|"create_project(freelancer, prd) + GEN escrow"| Contract["WorkFlowShieldX Contract"]
        Contract -->|"State: FUNDED"| Escrow["Locked On-Chain Escrow"]
    end

    subgraph Freelancer["2. Freelancer Deliverable Submission"]
        F["Freelancer"] -->|"submit_work(project_id, submission_url)"| Contract
        Contract -->|"Anti-SSRF & Scheme Check"| ValidURL{"Valid Web URL?"}
        ValidURL -- Yes -->|"State: SUBMITTED"| SubState["Ready for Adjudication"]
        ValidURL -- No --> Revert["Revert UserError"]
    end

    subgraph Consensus["3. GenLayer Optimistic Democracy Consensus"]
        Keeper["Any Keeper / Freelancer / Client"] -->|"adjudicate_milestone(project_id)"| Jury["GenLayer Validator Jury"]
        Jury -->|"gl.nondet.web.render(url)"| Scrape["Scrape Deliverable Evidence"]
        Jury -->|"gl.nondet.exec_prompt(PRD vs Deliverable)"| LLM["LLM Evaluation"]
        LLM --> Discrete{"Discrete Status Consensus"}
    end

    subgraph Settlement["4. Economic Settlement & Capital Safety"]
        Discrete -->|"APPROVED (Score >= 70)"| PayFreelancer["Disburse Escrow 100% to Freelancer"]
        Discrete -->|"REJECTED (Score < 70)"| RefundClient["Refund Escrow 100% to Client"]
        Discrete -->|"EVIDENCE_UNAVAILABLE (404/Error)"| Preserve["Escrow Preserved in SUBMITTED (Retry)"]
        Client -->|"cancel_project(project_id)"| Cancel["Client Graceful Refund if Inactive"]
    end
```

---

## 4. Key Protocol Innovations

### 1. Direct Web Rendering & Anti-SSRF Protection
Validators fetch live evidence directly from the deliverable URL on-chain via `gl.nondet.web.render(submission_url, mode="text")`. The contract enforces strict URL sanitization (`_validate_url_security`) preventing SSRF attacks against internal network metadata services (`169.254.169.254`, `localhost`, `10.*`, `192.168.*`).

### 2. Discrete Equivalence on Milestone Verdict
LLM explanations naturally differ slightly between validators. To prevent non-deterministic consensus splits while keeping rich explanatory feedback, **WorkFlowShieldX** enforces discrete equivalence on the categorical adjudication status:

```python
def validator_fn(leader_res) -> bool:
    if not isinstance(leader_res, gl.vm.Return):
        return False
    leader = leader_res.calldata
    if not isinstance(leader, dict) or "status" not in leader:
        return False

    l_status = str(leader.get("status", "")).strip().upper()
    mine = leader_fn()
    m_status = str(mine.get("status", "")).strip().upper()
    return l_status == m_status
```

### 3. Economic Safety & Dispute Preservation
- **APPROVED:** Deliverable fulfills requirements (score $\ge 70$); escrow is disbursed to the freelancer (`_safe_transfer(proj.freelancer, escrow)`).
- **REJECTED:** Deliverable is missing or incomplete (score $< 70$); escrow is refunded to the client (`_safe_transfer(proj.client, escrow)`).
- **EVIDENCE_UNAVAILABLE:** If the URL is offline, returns 404, or is unparsable, the contract **never burns or traps funds**; it preserves the milestone in `SUBMITTED` state, allowing the freelancer to submit a corrected link or the client to cancel.
- **Graceful Client Cancellation:** `cancel_project(project_id)` allows the client to reclaim unspent escrow if the freelancer fails to deliver.

### 4. Full GenVM Storage & Type Compatibility
Compliant with GenVM storage rules:
- Custom struct `@allow_storage @dataclass` `FreelanceProject`.
- Uses `bigint` for financial amounts, timestamps, and scores.
- Clean star-import `from genlayer import *`.

---

## 5. Directory Structure

```
WorkFlowShieldX/
├── contracts/
│   └── work_flow_shield_x.py      # Core Intelligent Contract
├── scripts/
│   └── deploy_studionet.py        # Studionet automated deployment script
├── tests/
│   ├── conftest.py                # gltest simulator mock helpers
│   └── test_work_flow_shield_x.py # 10 Comprehensive unit tests
├── deployment.json                # Verified Studionet on-chain receipt
├── gltest.config.yaml             # gltest network and contract mapping
├── requirements-dev.txt           # Testing dependencies
├── submission.md                  # Portal submission draft for reviewers
└── README.md                      # Architecture and protocol documentation
```

---

## 6. How to Run & Verify

### Running Unit Tests (10/10 Passing)
```bash
pytest tests -v
```

### Deploying to Studionet
```bash
python scripts/deploy_studionet.py
```
