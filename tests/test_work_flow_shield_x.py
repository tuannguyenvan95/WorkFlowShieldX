import pytest
import json
from gltest import *
from conftest import sim_installMocks


@pytest.fixture
def contract(direct_deploy):
    return direct_deploy("contracts/work_flow_shield_x.py")


def test_initial_state(contract, direct_vm, direct_alice, direct_bob):
    assert contract.get_project_count() == 0
    owner_str = contract.get_owner().lower()
    expected_sender = direct_vm.sender.hex().lower() if isinstance(direct_vm.sender, bytes) else str(direct_vm.sender).lower()
    if not expected_sender.startswith("0x"):
        expected_sender = "0x" + expected_sender
    assert owner_str == expected_sender

    stats = json.loads(contract.get_stats())
    assert stats["total_projects"] == 0
    assert stats["total_escrow_funded"] == "0"
    assert stats["total_paid_freelancers"] == "0"
    assert stats["total_refunded_clients"] == "0"


def test_create_project_success(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 5000  # 5000 GEN

    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Build a responsive React landing page with Tailwind CSS, dark mode support, and contact form."
    )

    assert pid == "1"
    assert contract.get_project_count() == 1

    proj = json.loads(contract.get_project("1"))
    assert proj["project_id"] == "1"
    assert proj["client"] == direct_alice.as_hex.lower()
    assert proj["freelancer"] == direct_bob.as_hex.lower()
    assert "React landing page" in proj["prd_description"]
    assert proj["escrow_amount"] == "5000"
    assert proj["status"] == "FUNDED"
    assert proj["score"] == 0
    assert proj["submission_url"] == ""

    stats = json.loads(contract.get_stats())
    assert stats["total_projects"] == 1
    assert stats["total_escrow_funded"] == "5000"


def test_create_project_validations(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice

    # 1. Zero funding
    direct_vm.value = 0
    with pytest.raises(Exception, match="Escrow funding must be greater than 0 GEN"):
        contract.create_project(
            freelancer=direct_bob,
            prd_description="Build a responsive React landing page with Tailwind CSS."
        )

    # 2. Short PRD (< 10 chars)
    direct_vm.value = 1000
    with pytest.raises(Exception, match="PRD description is too short"):
        contract.create_project(
            freelancer=direct_bob,
            prd_description="Too short"
        )

    # 3. Client and freelancer same address
    with pytest.raises(Exception, match="Client and freelancer cannot be the same address"):
        contract.create_project(
            freelancer=direct_alice,
            prd_description="Build a responsive React landing page with Tailwind CSS."
        )


def test_submit_work_success(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 3000
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Develop a Python FastAPI REST API with JWT authentication and SQLite storage."
    )

    # Submitting work as freelancer (direct_bob)
    direct_vm.sender = direct_bob
    contract.submit_work(
        project_id=pid,
        submission_url="https://github.com/developer/fastapi-jwt-boilerplate"
    )

    proj = json.loads(contract.get_project(pid))
    assert proj["status"] == "SUBMITTED"
    assert proj["submission_url"] == "https://github.com/developer/fastapi-jwt-boilerplate"


def test_submit_work_validations(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 3000
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Develop a Python FastAPI REST API with JWT authentication and SQLite storage."
    )

    # 1. Non-freelancer tries to submit
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Only designated freelancer can submit work"):
        contract.submit_work(
            project_id=pid,
            submission_url="https://github.com/developer/project"
        )

    # 2. Invalid URL format
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Submission URL must start with http:// or https://"):
        contract.submit_work(
            project_id=pid,
            submission_url="ftp://files.example.com/repo"
        )

    # 3. Prohibited local / SSRF URL
    with pytest.raises(Exception, match="Local and private network URLs are prohibited"):
        contract.submit_work(
            project_id=pid,
            submission_url="http://127.0.0.1:8000/internal"
        )


def test_adjudicate_milestone_approved(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 4000
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Implement a complete authentication module with JWT tokens and OAuth2 login."
    )

    direct_vm.sender = direct_bob
    contract.submit_work(
        project_id=pid,
        submission_url="https://github.com/freelancer/auth-service"
    )

    evidence_text = """
    FastAPI Auth Service Implementation:
    - JWT token generation and RS256 signing
    - OAuth2 password flow with refresh token rotation
    - SQLite database model for User with bcrypt hashed passwords
    - Unit tests covering login, token renewal, and authorization middleware (100% pass)
    """

    sim_installMocks({
        "web_mocks": {
            "https://github.com/freelancer/auth-service": evidence_text
        },
        "llm_mocks": {
            ".*": {
                "score": 95,
                "status": "APPROVED",
                "reason": "Deliverable satisfies all PRD requirements including JWT, OAuth2 flow, and tests."
            }
        }
    }, vm=direct_vm)

    # Any party or keeper can trigger adjudication
    contract.adjudicate_milestone(pid)

    proj = json.loads(contract.get_project(pid))
    assert proj["status"] == "APPROVED"
    assert proj["score"] == 95
    assert "satisfies all PRD" in proj["reason"]

    stats = json.loads(contract.get_stats())
    assert stats["total_paid_freelancers"] == "4000"
    assert stats["total_refunded_clients"] == "0"


def test_adjudicate_milestone_rejected(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 2500
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Develop an enterprise microservice with Redis caching and Kubernetes Helm charts."
    )

    direct_vm.sender = direct_bob
    contract.submit_work(
        project_id=pid,
        submission_url="https://github.com/freelancer/empty-demo"
    )

    evidence_text = "Hello World basic script. No microservices or Redis implemented yet."

    sim_installMocks({
        "web_mocks": {
            "https://github.com/freelancer/empty-demo": evidence_text
        },
        "llm_mocks": {
            ".*": {
                "score": 25,
                "status": "REJECTED",
                "reason": "Missing Redis caching, microservices architecture, and Helm charts."
            }
        }
    }, vm=direct_vm)

    contract.adjudicate_milestone(pid)

    proj = json.loads(contract.get_project(pid))
    assert proj["status"] == "REJECTED"
    assert proj["score"] == 25
    assert "Missing Redis caching" in proj["reason"]

    stats = json.loads(contract.get_stats())
    assert stats["total_paid_freelancers"] == "0"
    assert stats["total_refunded_clients"] == "2500"


def test_adjudicate_milestone_evidence_unavailable(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 1500
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Design high fidelity dashboard mockups in Figma."
    )

    direct_vm.sender = direct_bob
    contract.submit_work(
        project_id=pid,
        submission_url="https://figma.com/file/broken-link-404"
    )

    sim_installMocks({
        "web_mocks": {
            "https://figma.com/file/broken-link-404": "404 Not Found. The requested page was not found."
        }
    }, vm=direct_vm)

    contract.adjudicate_milestone(pid)

    proj = json.loads(contract.get_project(pid))
    # State preserved in SUBMITTED to allow retry/recovery, escrow NOT lost
    assert proj["status"] == "SUBMITTED"
    assert "Evidence unavailable" in proj["reason"]

    stats = json.loads(contract.get_stats())
    assert stats["total_paid_freelancers"] == "0"
    assert stats["total_refunded_clients"] == "0"


def test_cancel_project_success(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 6000
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Develop a Solidity smart contract audit test suite with Slither."
    )

    # Client cancels before work submission or after offline link
    contract.cancel_project(pid)

    proj = json.loads(contract.get_project(pid))
    assert proj["status"] == "CANCELLED"
    assert "Full escrow refunded" in proj["reason"]

    stats = json.loads(contract.get_stats())
    assert stats["total_refunded_clients"] == "6000"


def test_cancel_project_validations(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 2000
    pid = contract.create_project(
        freelancer=direct_bob,
        prd_description="Create social media marketing graphics banner pack."
    )

    # 1. Non-client cannot cancel
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only project client can cancel and refund project"):
        contract.cancel_project(pid)

    # 2. Cannot cancel already approved project
    direct_vm.sender = direct_bob
    contract.submit_work(pid, "https://github.com/freelancer/banners")

    sim_installMocks({
        "web_mocks": {
            "https://github.com/freelancer/banners": "Complete 10 graphic banner sets in Figma and PNG."
        },
        "llm_mocks": {
            ".*": {
                "score": 90,
                "status": "APPROVED",
                "reason": "All marketing assets successfully created."
            }
        }
    }, vm=direct_vm)

    contract.adjudicate_milestone(pid)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Cannot cancel project in status 'APPROVED'"):
        contract.cancel_project(pid)
