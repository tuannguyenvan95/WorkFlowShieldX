# Portal Submission Draft — WorkFlowShieldX

**Portal Track:** Builder  
**Contribution Type:** Intelligent Contracts  
**Network:** studionet (Chain ID: 61999)  
**Contract Address:** `0xAF99ABE439A84a64fBba2d5107d89075f110b995`  
**Deployer Address:** `0xf2949c471F6116042807772dd788D6fA0905DC97`  
**Transaction Hash:** `0xca8dc7820fab3ca755f623440e34d649330f9690f16ce589cc4da36bca25da42`  
**Evidence URL 1:** `https://github.com/tuannguyenvan95/WorkFlowShieldX`  
**Evidence URL 2:** `https://explorer-studio.genlayer.com/address/0xAF99ABE439A84a64fBba2d5107d89075f110b995`  

---

### Title
```
WorkFlowShieldX — Autonomous Freelance Milestone Arbiter Protocol
```

### Notes / Description (<1000 characters)
```
WorkFlowShieldX is an autonomous freelance milestone arbiter protocol built on GenLayer that resolves disputes between clients and freelancers without centralized intermediaries (e.g. Upwork, Fiverr).

Clients fund escrow with GEN and attach a Project Requirements Document (PRD). Freelancers submit work deliverables via live URLs (GitHub PRs, Figma, deployed demos). GenLayer validator juries autonomously scrape submission content via gl.nondet.web.render with anti-SSRF protections, and adjudicate milestone deliverables against PRD specifications using Optimistic Democracy LLM consensus via gl.vm.run_nondet enforcing discrete semantic status equivalence:

- APPROVED (score >= 70): 100% escrow disbursed to freelancer.
- REJECTED (score < 70): 100% escrow refunded to client.
- EVIDENCE_UNAVAILABLE (404/broken link): 0 disbursement, state preserved in SUBMITTED for retry.
- Bounded Recovery: Client can cancel unfulfilled projects via cancel_project().

Status: 10/10 unit tests passing. Fully deployed and verified on Studionet.
```

### Steward Response (Joaquin)
```
Dear Joaquin,

We are pleased to submit WorkFlowShieldX for the GenLayer Builder Track:
1. Core Decision on GenVM: Milestone inspection, PRD conformance grading, and escrow disbursement execute autonomously inside the Intelligent Contract via gl.nondet.web.render and gl.vm.run_nondet consensus.
2. Robust Edge-Case Handling: When deliverables return 404, offline pages, or unparsable content, the consensus jury marks EVIDENCE_UNAVAILABLE, preserving 100% of the escrow without risk of loss. In addition, clients have a bounded safe cancellation path (cancel_project).
3. Strict Storage Compliance: Full conformance with GenVM storage rules using @allow_storage @dataclass with bigint fields for scores, timestamps, and escrow accounting.
4. Comprehensive Testing & Verification: 10/10 gltest unit tests passing across all lifecycle stages. Contract is finalized and verified on Studionet at address 0xAF99ABE439A84a64fBba2d5107d89075f110b995.
```
