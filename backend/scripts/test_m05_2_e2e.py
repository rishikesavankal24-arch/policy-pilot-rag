"""
PolicyPilot — M05.2 End-to-End Acceptance Test
Real Customer -> FastAPI -> PostgreSQL -> FastAPI -> Employee Workflow

Verifies:
1. Customer creates loan application (Education Loan, ₹8,00,000)
2. Customer uploads attached document
3. Customer submits application -> status becomes SUBMITTED
4. Verification that database status is SUBMITTED
5. Employee opens Application Queue -> the same application appears with exact matching data
6. Employee opens application detail -> backend transitions SUBMITTED to UNDER_REVIEW in PostgreSQL
7. Customer opens My Applications & Application Detail -> verifies status reflects UNDER_REVIEW
8. Confirmation that both portals are operating on the exact same PostgreSQL database record
"""

import sys
import uuid
import io
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus,
    Notification, Session as DBSession
)
from app.core.security import create_user_session

def run_e2e_test():
    print("=" * 70)
    print("POLICYPILOT M05.2 — REAL CUSTOMER -> EMPLOYEE E2E ACCEPTANCE TEST")
    print("=" * 70)
    
    db = SessionLocal()
    clean_uids = []
    
    try:
        # -------------------------------------------------------------
        # SETUP: Create Synthetic Customer and Employee
        # -------------------------------------------------------------
        print("\n[SETUP] Creating synthetic customer and verified employee accounts...")
        
        # 1. Customer
        cust_id = uuid.uuid4()
        clean_uids.append(cust_id)
        cust_email = f"e2e_cust_{cust_id.hex[:6]}@policypilot.local"
        customer = User(
            id=cust_id,
            email=cust_email,
            full_name="Rajesh Kumar Verma",
            role=Role.CUSTOMER.value,
            requested_role=Role.CUSTOMER.value,
            onboarding_status=OnboardingStatus.COMPLETED.value,
            authentication_provider="local",
            provider_subject_id=cust_email,
            phone_number="+919876543210",
            date_of_birth="1995-08-20",
            address="Flat 402, Lotus Enclave, HSR Layout",
            city="Bengaluru",
            state="Karnataka",
            pincode="560102"
        )
        db.add(customer)
        db.commit()
        cust_token = create_user_session(db, customer.id)
        cust_client = TestClient(app, cookies={"session_id": cust_token})
        print(f"  [OK] Customer created: {customer.full_name} ({cust_email})")
        
        # 2. Verified Employee
        emp_id = uuid.uuid4()
        clean_uids.append(emp_id)
        emp_email = f"e2e_emp_{emp_id.hex[:6]}@policypilot.local"
        employee = User(
            id=emp_id,
            email=emp_email,
            full_name="Officer Priya Sundaram",
            role=Role.EMPLOYEE.value,
            requested_role=Role.EMPLOYEE.value,
            onboarding_status=OnboardingStatus.COMPLETED.value,
            authentication_provider="local",
            provider_subject_id=emp_email
        )
        db.add(employee)
        db.commit()
        
        emp_req = EmployeeRequest(
            user_id=employee.id,
            organization="PolicyPilot National Bank",
            department="Retail Credit & Underwriting Desk",
            employee_id="EMP-PP-BLR-042",
            designation="Senior Credit Underwriter",
            work_email=f"work_{emp_email}",
            status=EmployeeRequestStatus.APPROVED.value
        )
        db.add(emp_req)
        db.commit()
        emp_token = create_user_session(db, employee.id)
        emp_client = TestClient(app, cookies={"session_id": emp_token})
        print(f"  [OK] Employee verified: {employee.full_name} ({emp_email})")
        
        # -------------------------------------------------------------
        # STEP 1: Customer creates Education Loan
        # -------------------------------------------------------------
        print("\n[STEP 1] Customer creates loan application...")
        app_payload = {
            "loan_type": "Education Loan",
            "requested_amount": 800000,
            "tenure": 60,
            "purpose": "Master of Science tuition and living expenses",
            "employment_info": "Senior Analyst at Fintech Corp",
            "income_info": "950000",
            "existing_liabilities": "None"
        }
        res_create = cust_client.post("/api/applications/", json=app_payload)
        assert res_create.status_code == 200, f"Failed creation: {res_create.text}"
        app_data = res_create.json()
        app_id = app_data["id"]
        print(f"  [OK] Application created: ID = {app_id}")
        print(f"    Product: {app_data['loan_type']}, Amount: INR {app_data['requested_amount']:,}, Status: {app_data['status']}")
        assert app_data["status"] == "DRAFT"
        
        # -------------------------------------------------------------
        # STEP 2: Customer uploads documents
        # -------------------------------------------------------------
        print("\n[STEP 2] Customer uploads supporting documents...")
        dummy_file = b"%PDF-1.4 Mock University Admission Letter & Fee Structure"
        res_doc = cust_client.post(
            "/api/documents/",
            data={"document_type": "ADMISSION_LETTER", "application_id": app_id},
            files={"file": ("university_admission.pdf", io.BytesIO(dummy_file), "application/pdf")}
        )
        assert res_doc.status_code == 200, f"Failed document upload: {res_doc.text}"
        doc_data = res_doc.json()
        print(f"  [OK] Document attached: {doc_data['document_type']} (ID: {doc_data['id']})")
        
        # -------------------------------------------------------------
        # STEP 3 & 4: Customer submits application
        # -------------------------------------------------------------
        print("\n[STEP 3 & 4] Customer clicks SUBMIT APPLICATION -> Backend validates & transitions...")
        res_submit = cust_client.post(f"/api/applications/{app_id}/submit")
        assert res_submit.status_code == 200, f"Failed submission: {res_submit.text}"
        submitted_data = res_submit.json()
        print(f"  [OK] Backend updated status: {submitted_data['status']}")
        assert submitted_data["status"] == "SUBMITTED"
        
        # Verify in PostgreSQL
        db.expire_all()
        db_app = db.query(Application).filter(Application.id == uuid.UUID(app_id)).first()
        assert db_app is not None
        assert db_app.status == ApplicationStatus.SUBMITTED.value
        print(f"  [OK] Verified directly in PostgreSQL: status == '{db_app.status}'")
        
        # -------------------------------------------------------------
        # STEP 5 & 6: Employee opens Application Queue
        # -------------------------------------------------------------
        print("\n[STEP 5 & 6] Employee opens Application Queue (GET /api/employee/applications)...")
        res_queue = emp_client.get("/api/employee/applications")
        assert res_queue.status_code == 200, f"Queue access failed: {res_queue.text}"
        queue_items = res_queue.json()
        matching = [item for item in queue_items if item["id"] == app_id]
        assert len(matching) == 1, "Submitted application must be present in Employee Queue!"
        queue_match = matching[0]
        print(f"  [OK] Application visible in Employee Queue!")
        print(f"    Case ID: {queue_match['id']}")
        print(f"    Applicant: {queue_match['applicant_name']} ({queue_match['applicant_email']})")
        print(f"    Product: {queue_match['loan_type']}")
        print(f"    Amount: INR {queue_match['requested_amount']:,}")
        print(f"    Queue Status: {queue_match['status']}")
        print(f"    Document Count: {queue_match['document_count']}")
        assert queue_match["status"] == "SUBMITTED"
        assert queue_match["applicant_name"] == customer.full_name
        assert queue_match["requested_amount"] == 800000
        assert queue_match["document_count"] == 1
        
        # -------------------------------------------------------------
        # STEP 7: Employee opens Application Detail (INSPECT - GET)
        # -------------------------------------------------------------
        print("\n[STEP 7] Employee opens Application Detail / INSPECT (GET /api/employee/applications/[id])...")
        res_detail = emp_client.get(f"/api/employee/applications/{app_id}")
        assert res_detail.status_code == 200, f"Detail access failed: {res_detail.text}"
        detail_data = res_detail.json()
        print(f"  [OK] Underwriting Dossier loaded:")
        print(f"    Status returned to Employee: {detail_data['application']['status']}")
        print(f"    Applicant Full Name: {detail_data['applicant']['full_name']}")
        print(f"    Applicant Contact: {detail_data['applicant']['email']} / {detail_data['applicant']['phone_number']}")
        print(f"    Documents Attached: {len(detail_data['documents'])} verified in dossier")
        print(f"    Timeline Events: {len(detail_data['timeline'])} events recorded")
        assert detail_data["application"]["status"] == "SUBMITTED", "Inspect operation must NOT mutate application status!"
        
        # -------------------------------------------------------------
        # STEP 8: Verify PostgreSQL status remains SUBMITTED after Inspect
        # -------------------------------------------------------------
        print("\n[STEP 8] Verifying PostgreSQL database state after Employee opened dossier...")
        db.expire_all()
        db_app_after_inspect = db.query(Application).filter(Application.id == uuid.UUID(app_id)).first()
        assert db_app_after_inspect.status == ApplicationStatus.SUBMITTED.value
        print(f"  [OK] Confirmed in PostgreSQL: application.status is STILL '{db_app_after_inspect.status}'")
        
        # -------------------------------------------------------------
        # STEP 9: Employee clicks START REVIEW (POST /transition-review)
        # -------------------------------------------------------------
        print("\n[STEP 9] Employee clicks START REVIEW (POST /api/employee/applications/[id]/transition-review)...")
        res_start_review = emp_client.post(f"/api/employee/applications/{app_id}/transition-review")
        assert res_start_review.status_code == 200, f"Start review failed: {res_start_review.text}"
        review_data = res_start_review.json()
        print(f"  [OK] Status updated to: {review_data['application']['status']}")
        assert review_data["application"]["status"] == "UNDER_REVIEW"
        
        # -------------------------------------------------------------
        # STEP 10: Verify PostgreSQL status transitioned to UNDER_REVIEW
        # -------------------------------------------------------------
        print("\n[STEP 10] Verifying PostgreSQL database state after Start Review...")
        db.expire_all()
        db_app_review = db.query(Application).filter(Application.id == uuid.UUID(app_id)).first()
        assert db_app_review.status == ApplicationStatus.UNDER_REVIEW.value
        print(f"  [OK] Confirmed in PostgreSQL: application.status == '{db_app_review.status}'")
        
        # -------------------------------------------------------------
        # STEP 11: Customer checks Application Details & My Applications
        # -------------------------------------------------------------
        print("\n[STEP 11] Customer checks Application Details (GET /api/applications/[id])...")
        res_cust_check = cust_client.get(f"/api/applications/{app_id}")
        assert res_cust_check.status_code == 200, f"Customer check failed: {res_cust_check.text}"
        cust_view = res_cust_check.json()
        cust_status = cust_view["application"]["status"]
        print(f"  [OK] Customer Application Details reflects updated status: '{cust_status}'")
        assert cust_status == "UNDER_REVIEW", f"Customer must see UNDER_REVIEW, got: {cust_status}"
        
        # Customer My Applications list also reflects updated status
        res_cust_list = cust_client.get("/api/applications/")
        assert res_cust_list.status_code == 200
        cust_list = res_cust_list.json()
        list_match = [a for a in cust_list if a["id"] == app_id][0]
        assert list_match["status"] == "UNDER_REVIEW"
        print(f"  [OK] Customer 'My Applications' list reflects updated status: '{list_match['status']}'")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL E2E WORKFLOW CHECKS PASSED: REAL CUSTOMER -> EMPLOYEE LINK VERIFIED")
        print("=" * 70)
        return True
        
    finally:
        # Cleanup synthetic test records
        for uid in clean_uids:
            db.query(Notification).filter(Notification.user_id == uid).delete()
            db.query(Document).filter(Document.user_id == uid).delete()
            db.query(Application).filter(Application.user_id == uid).delete()
            db.query(EmployeeRequest).filter(EmployeeRequest.user_id == uid).delete()
            db.query(DBSession).filter(DBSession.user_id == uid).delete()
            db.query(User).filter(User.id == uid).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    success = run_e2e_test()
    if not success:
        sys.exit(1)
