import uuid
import io
import os
from pathlib import Path
from app.db.session import SessionLocal
from app.db.models import (
    User, Role, OnboardingStatus, Application, ApplicationStatus,
    Document, DocumentStatus, EmployeeRequest, EmployeeRequestStatus
)
from app.core.security import get_password_hash
from app.api.documents import STORAGE_DIR

def seed_demo_data():
    db = SessionLocal()
    try:
        # 1. Employee
        emp_email = "employee.review@policypilot.internal"
        emp = db.query(User).filter(User.email == emp_email).first()
        if not emp:
            emp = User(
                id=uuid.uuid4(),
                email=emp_email,
                full_name="Rajesh Underwriter",
                hashed_password=get_password_hash("Password123!"),
                role=Role.EMPLOYEE.value,
                requested_role=Role.EMPLOYEE.value,
                onboarding_status=OnboardingStatus.COMPLETED.value,
                authentication_provider="local",
                provider_subject_id=emp_email,
                phone_number="+919876500001"
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)

            req = EmployeeRequest(
                user_id=emp.id,
                organization="PolicyPilot Operations Desk",
                department="Retail Credit Underwriting",
                employee_id="EMP-9001",
                designation="Senior Credit Underwriter",
                work_email=emp_email,
                reason="Commercial and MSME Underwriting",
                status=EmployeeRequestStatus.APPROVED.value
            )
            db.add(req)
            db.commit()
        else:
            emp.hashed_password = get_password_hash("Password123!")
            emp.onboarding_status = OnboardingStatus.COMPLETED.value
            emp.role = Role.EMPLOYEE.value
            db.commit()

        # 2. Customer
        cust_email = "customer.review@policypilot.internal"
        cust = db.query(User).filter(User.email == cust_email).first()
        if not cust:
            cust = User(
                id=uuid.uuid4(),
                email=cust_email,
                full_name="Ananya Sharma",
                hashed_password=get_password_hash("Password123!"),
                role=Role.CUSTOMER.value,
                requested_role=Role.CUSTOMER.value,
                onboarding_status=OnboardingStatus.COMPLETED.value,
                authentication_provider="local",
                provider_subject_id=cust_email,
                phone_number="+919876500002",
                address="Flat 402, Lotus Heights",
                city="Pune",
                state="Maharashtra",
                pincode="411001"
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)
        else:
            cust.hashed_password = get_password_hash("Password123!")
            cust.onboarding_status = OnboardingStatus.COMPLETED.value
            cust.role = Role.CUSTOMER.value
            db.commit()

        # 3. Application
        app = db.query(Application).filter(Application.user_id == cust.id).first()
        if not app:
            app = Application(
                id=uuid.uuid4(),
                user_id=cust.id,
                loan_type="Business Loan",
                requested_amount=1500000,
                tenure=36,
                purpose="Working capital and inventory replenishment for festive season",
                employment_info="Self-Employed Entrepreneur",
                income_info="₹1,80,000 / month declared",
                existing_liabilities="None",
                status=ApplicationStatus.UNDER_REVIEW.value
            )
            db.add(app)
            db.commit()
            db.refresh(app)

            # 4. Two documents with real files
            doc1_id = uuid.uuid4()
            doc1_dir = STORAGE_DIR / str(doc1_id)
            doc1_dir.mkdir(parents=True, exist_ok=True)
            doc1_file = doc1_dir / "GST_Registration_Certificate.pdf"
            doc1_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
            doc1_file.write_bytes(doc1_content)

            doc1 = Document(
                id=doc1_id,
                user_id=cust.id,
                application_id=app.id,
                document_type="INCORPORATION_CERTIFICATE",
                file_url=f"documents/{doc1_id}/GST_Registration_Certificate.pdf",
                status=DocumentStatus.UPLOADED.value
            )
            db.add(doc1)

            doc2_id = uuid.uuid4()
            doc2_dir = STORAGE_DIR / str(doc2_id)
            doc2_dir.mkdir(parents=True, exist_ok=True)
            doc2_file = doc2_dir / "Audited_Financial_Statement_FY24.pdf"
            doc2_file.write_bytes(doc1_content)

            doc2 = Document(
                id=doc2_id,
                user_id=cust.id,
                application_id=app.id,
                document_type="FINANCIAL_STATEMENT",
                file_url=f"documents/{doc2_id}/Audited_Financial_Statement_FY24.pdf",
                status=DocumentStatus.UPLOADED.value
            )
            db.add(doc2)
            db.commit()
            print(f"Created application {app.id} with documents {doc1_id} and {doc2_id}")
        else:
            app.status = ApplicationStatus.UNDER_REVIEW.value
            db.commit()
            print(f"Application {app.id} ready.")

        print(f"Employee: {emp_email} / Password123!")
        print(f"Customer: {cust_email} / Password123!")
        print(f"App ID: {app.id}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
