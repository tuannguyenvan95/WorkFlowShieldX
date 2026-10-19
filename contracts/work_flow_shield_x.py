# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json

try:
    gl.UserError = gl.vm.UserError
except Exception:
    pass


def _addr_str(addr: Address) -> str:
    """Safely format an Address instance into a lowercase hex string."""
    try:
        return addr.as_hex.lower()
    except Exception:
        return str(addr).lower()


def _get_sender() -> Address:
    """Safely obtain transaction sender across GenVM runtime versions."""
    try:
        if hasattr(gl, "message"):
            if hasattr(gl.message, "sender"):
                return gl.message.sender
            if hasattr(gl.message, "sender_address"):
                return gl.message.sender_address
    except Exception:
        pass
    try:
        if hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
            s = gl.message_raw.get("from") or gl.message_raw.get("sender")
            if s:
                return Address(str(s))
    except Exception:
        pass
    raise gl.UserError("Cannot resolve sender address.")


def _safe_transfer(recipient: Address, amount: bigint) -> None:
    """Safely disburse native GEN to an address using official GenLayer SDK pattern."""
    if amount <= bigint(0):
        return
    gl.get_contract_at(recipient).emit_transfer(value=u256(int(amount)))


def _validate_url_security(raw_url: str) -> str:
    """Extract and validate normalized URL and prevent SSRF to local/private addresses."""
    clean = raw_url.strip()
    if clean.startswith("https://"):
        rest = clean[8:]
    elif clean.startswith("http://"):
        rest = clean[7:]
    else:
        raise gl.UserError("Submission URL must start with http:// or https://")

    clean_no_query = rest.split("?")[0].split("#")[0]
    host = clean_no_query.split("/")[0].strip().lower()
    if ":" in host:
        host = host.split(":")[0]

    blocked = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "internal",
        "metadata.google.internal",
        "169.254.169.254",
    ]
    if host in blocked or host.endswith(".local") or host.endswith(".internal"):
        raise gl.UserError("Local and private network URLs are prohibited.")

    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("172.16."):
        raise gl.UserError("Local and private network URLs are prohibited.")

    return clean


@allow_storage
@dataclass
class FreelanceProject:
    project_id: str
    client: Address
    freelancer: Address
    prd_description: str
    submission_url: str
    escrow_amount: bigint
    status: str         # "FUNDED", "SUBMITTED", "APPROVED", "REJECTED", "CANCELLED"
    score: bigint       # 0 to 100 quality score (stored as bigint)
    reason: str
    created_at: bigint
    resolved_at: bigint


class Contract(gl.Contract):
    """
    WorkFlowShieldX: Autonomous Freelance Milestone Arbiter Protocol on GenLayer.
    Resolves milestone disputes without intermediaries using Optimistic Democracy LLM Juries.
    """
    owner: Address
    project_count: bigint
    total_escrow_funded: bigint
    total_paid_freelancers: bigint
    total_refunded_clients: bigint
    projects: TreeMap[str, FreelanceProject]

    def __init__(self):
        self.owner = _get_sender()
        self.project_count = bigint(0)
        self.total_escrow_funded = bigint(0)
        self.total_paid_freelancers = bigint(0)
        self.total_refunded_clients = bigint(0)

    def _get_current_timestamp(self) -> bigint:
        try:
            from datetime import datetime
            dt_raw = getattr(gl.message, "datetime", None)
            if dt_raw is None and hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
                dt_raw = gl.message_raw.get("datetime")
            if dt_raw:
                dt_str = str(dt_raw).strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                ts = int(dt.timestamp())
                if ts > 0:
                    return bigint(ts)
        except Exception:
            pass
        try:
            if hasattr(gl, "block") and hasattr(gl.block, "timestamp"):
                ts = int(gl.block.timestamp)
                if ts > 0:
                    return bigint(ts)
        except Exception:
            pass
        return bigint(0)

    @gl.public.write.payable
    def create_project(self, freelancer: Address, prd_description: str) -> str:
        """
        Client creates a freelance milestone project and funds the escrow in GEN.
        """
        amount = bigint(gl.message.value)
        if amount <= bigint(0):
            raise gl.UserError("Escrow funding must be greater than 0 GEN.")

        clean_prd = prd_description.strip()
        if len(clean_prd) < 10:
            raise gl.UserError("PRD description is too short (min 10 characters).")

        sender = _get_sender()
        if _addr_str(freelancer) == _addr_str(sender):
            raise gl.UserError("Client and freelancer cannot be the same address.")

        self.project_count += bigint(1)
        pid = str(self.project_count)
        now_ts = self._get_current_timestamp()

        self.projects[pid] = FreelanceProject(
            project_id=pid,
            client=sender,
            freelancer=freelancer,
            prd_description=clean_prd,
            submission_url="",
            escrow_amount=amount,
            status="FUNDED",
            score=bigint(0),
            reason="Project funded. Awaiting freelancer work submission.",
            created_at=now_ts if now_ts > bigint(0) else self.project_count,
            resolved_at=bigint(0)
        )
        self.total_escrow_funded += amount
        return pid

    @gl.public.write
    def submit_work(self, project_id: str, submission_url: str) -> None:
        """
        Freelancer submits the deliverable link (GitHub PR, Figma, Live demo).
        """
        if project_id not in self.projects:
            raise gl.UserError("Project not found.")

        proj = self.projects[project_id]
        sender = _get_sender()
        if _addr_str(sender) != _addr_str(proj.freelancer):
            raise gl.UserError("Only designated freelancer can submit work.")

        if proj.status != "FUNDED" and proj.status != "SUBMITTED":
            raise gl.UserError(f"Project cannot accept submissions in '{proj.status}' state.")

        clean_url = _validate_url_security(submission_url)

        proj.submission_url = clean_url
        proj.status = "SUBMITTED"
        proj.reason = "Work submitted. Ready for AI jury adjudication."
        self.projects[project_id] = proj

    @gl.public.write
    def adjudicate_milestone(self, project_id: str) -> None:
        """
        Validators scrape the submission deliverable URL on-chain and use GenLayer Optimistic Democracy
        LLM jury consensus to evaluate the deliverable against the PRD requirements.
        """
        if project_id not in self.projects:
            raise gl.UserError("Project not found.")

        proj = self.projects[project_id]
        if proj.status != "SUBMITTED":
            raise gl.UserError(f"Project must be in SUBMITTED state to adjudicate (current: {proj.status}).")

        prd_local = str(proj.prd_description)
        url_local = str(proj.submission_url)

        def leader_fn():
            web_content = ""
            try:
                res = gl.nondet.web.render(url_local, mode="text")
                if hasattr(res, "content"):
                    web_content = res.content
                elif isinstance(res, dict) and "body" in res:
                    web_content = res["body"]
                else:
                    web_content = str(res)
            except Exception:
                web_content = ""

            lower_web = web_content[:500].lower() if web_content else ""
            if (
                len(web_content.strip()) < 15
                or "404 not found" in lower_web
                or "error 404" in lower_web
                or "page not found" in lower_web
            ):
                return {
                    "score": 0,
                    "status": "EVIDENCE_UNAVAILABLE",
                    "reason": "Submission URL is offline, blank, or returned 404/page not found."
                }

            snippet = web_content[:4000]

            prompt = f"""You are an expert Autonomous Freelance Project Arbiter and Tech Lead on GenLayer.
Evaluate the submitted work deliverable against the original Project Requirements Document (PRD).

PRD REQUIREMENTS:
\"\"\"
{prd_local}
\"\"\"

SUBMITTED WORK CONTENT (Scraped from URL):
\"\"\"
{snippet}
\"\"\"

EVALUATION RULES:
- Score from 0 to 100 based on completion and quality.
- Status must be "APPROVED" if the work fully or satisfactorily satisfies the PRD (score >= 70).
- Status must be "REJECTED" if the work fails to meet requirements or is incomplete (score < 70).
- Status must be "EVIDENCE_UNAVAILABLE" if the content is unparsable, irrelevant, or broken.

OUTPUT FORMAT:
Respond ONLY with a VALID JSON object (no markdown, no backticks):
{{
  "score": <integer 0-100>,
  "status": "APPROVED" | "REJECTED" | "EVIDENCE_UNAVAILABLE",
  "reason": "<concise explanation max 220 characters>"
}}"""

            try:
                raw_res = gl.nondet.exec_prompt(prompt, response_format="json")
                parsed = None
                if isinstance(raw_res, dict):
                    parsed = raw_res
                elif hasattr(raw_res, "content") and isinstance(raw_res.content, dict):
                    parsed = raw_res.content
                else:
                    text = raw_res.content if hasattr(raw_res, "content") else str(raw_res)
                    cleaned = str(text).strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    elif cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    parsed = json.loads(cleaned.strip())

                score = int(parsed.get("score", 0))
                score = max(0, min(100, score))
                status = str(parsed.get("status", "REJECTED")).strip().upper()
                if status not in ("APPROVED", "REJECTED", "EVIDENCE_UNAVAILABLE"):
                    status = "APPROVED" if score >= 70 else "REJECTED"
                reason = str(parsed.get("reason", "Audited by GenLayer Jury."))[:220]

                return {
                    "score": score,
                    "status": status,
                    "reason": reason
                }
            except Exception as e:
                return {
                    "score": 0,
                    "status": "EVIDENCE_UNAVAILABLE",
                    "reason": f"Evaluation error: {str(e)[:100]}"
                }

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

        adjudication_res = gl.vm.run_nondet(leader_fn, validator_fn)
        if isinstance(adjudication_res, dict):
            final_res = adjudication_res
        else:
            try:
                final_res = json.loads(str(adjudication_res))
            except Exception:
                final_res = {"score": 0, "status": "EVIDENCE_UNAVAILABLE", "reason": "Consensus parse failed."}

        score = int(final_res.get("score", 0))
        status = str(final_res.get("status", "EVIDENCE_UNAVAILABLE")).strip().upper()
        reason = str(final_res.get("reason", "Resolved."))

        now_ts = self._get_current_timestamp()
        resolved_time = now_ts if now_ts > bigint(0) else self.project_count

        # Economic Disbursement:
        # If APPROVED -> release escrow to freelancer.
        # If REJECTED -> refund client.
        # If EVIDENCE_UNAVAILABLE -> preserve project in SUBMITTED state (safe retry).
        if status == "APPROVED":
            proj.score = bigint(score)
            proj.status = "APPROVED"
            proj.reason = reason
            proj.resolved_at = resolved_time
            self.projects[project_id] = proj
            self.total_paid_freelancers += proj.escrow_amount
            _safe_transfer(proj.freelancer, proj.escrow_amount)

        elif status == "REJECTED":
            proj.score = bigint(score)
            proj.status = "REJECTED"
            proj.reason = reason
            proj.resolved_at = resolved_time
            self.projects[project_id] = proj
            self.total_refunded_clients += proj.escrow_amount
            _safe_transfer(proj.client, proj.escrow_amount)

        else:
            # Evidence unavailable: preserve escrow and allow freelancer to resubmit or client to cancel
            proj.score = bigint(0)
            proj.status = "SUBMITTED"
            proj.reason = f"Evidence unavailable: {reason}. Escrow preserved for retry."
            self.projects[project_id] = proj

    @gl.public.write
    def cancel_project(self, project_id: str) -> None:
        """
        Client can cancel the project and refund the escrow if the freelancer has not yet submitted work,
        or if work submission remains in an unresolvable offline/broken state.
        """
        if project_id not in self.projects:
            raise gl.UserError("Project not found.")

        proj = self.projects[project_id]
        sender = _get_sender()
        if _addr_str(sender) != _addr_str(proj.client):
            raise gl.UserError("Only project client can cancel and refund project.")

        if proj.status not in ("FUNDED", "SUBMITTED"):
            raise gl.UserError(f"Cannot cancel project in status '{proj.status}'.")

        refund_amount = proj.escrow_amount
        proj.status = "CANCELLED"
        proj.reason = "Project cancelled by client. Full escrow refunded."
        now_ts = self._get_current_timestamp()
        proj.resolved_at = now_ts if now_ts > bigint(0) else self.project_count
        self.projects[project_id] = proj

        self.total_refunded_clients += refund_amount
        _safe_transfer(proj.client, refund_amount)

    @gl.public.view
    def get_project(self, project_id: str) -> str:
        if project_id not in self.projects:
            raise gl.UserError("Project not found.")
        p = self.projects[project_id]
        return json.dumps({
            "project_id": p.project_id,
            "client": _addr_str(p.client),
            "freelancer": _addr_str(p.freelancer),
            "prd_description": p.prd_description,
            "submission_url": p.submission_url,
            "escrow_amount": str(p.escrow_amount),
            "status": p.status,
            "score": int(p.score),
            "reason": p.reason,
            "created_at": str(p.created_at),
            "resolved_at": str(p.resolved_at)
        })

    @gl.public.view
    def get_project_count(self) -> int:
        return int(self.project_count)

    @gl.public.view
    def get_owner(self) -> str:
        return _addr_str(self.owner)

    @gl.public.view
    def get_stats(self) -> str:
        return json.dumps({
            "total_projects": int(self.project_count),
            "total_escrow_funded": str(self.total_escrow_funded),
            "total_paid_freelancers": str(self.total_paid_freelancers),
            "total_refunded_clients": str(self.total_refunded_clients)
        })
