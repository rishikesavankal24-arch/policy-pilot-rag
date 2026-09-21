import requests
import uuid

BASE = 'http://127.0.0.1:8000'

# Step 1: Login as Admin
s_admin = requests.Session()
r_login = s_admin.post(f'{BASE}/auth/local/login', json={'identifier': 'admin.demo@policypilot.local', 'password': 'AdminPassword123!'})
assert r_login.status_code == 200, f'Admin login failed: {r_login.text}'
print('[PASS] Admin authenticated successfully.')

# Step 2: Fetch Admin Overview APIs
reqs = s_admin.get(f'{BASE}/admin/employee-requests').json()
emps = s_admin.get(f'{BASE}/admin/employees').json()
custs = s_admin.get(f'{BASE}/admin/customers').json()
print(f'[PASS] Admin overview data: {len(reqs)} employee requests, {len(emps)} employees, {len(custs)} customers.')

# Step 3: Ensure a pending synthetic employee request exists
from app.db.session import SessionLocal
from app.db.models import User, EmployeeRequest, EmployeeRequestStatus, Role, OnboardingStatus
from app.core.security import get_password_hash
db = SessionLocal()

test_emp_email = 'test.e2e.emp@policypilot.local'
emp_user = db.query(User).filter(User.email == test_emp_email).first()
if not emp_user:
    emp_user = User(
        email=test_emp_email,
        full_name='Priya Sharma',
        authentication_provider='local',
        provider_subject_id=test_emp_email,
        hashed_password=get_password_hash('EmployeePassword123!'),
        onboarding_status=OnboardingStatus.PENDING_VERIFICATION.value,
        role=Role.CUSTOMER.value,
        requested_role=Role.EMPLOYEE.value
    )
    db.add(emp_user)
    db.commit()
    db.refresh(emp_user)

emp_req = db.query(EmployeeRequest).filter(EmployeeRequest.user_id == emp_user.id).first()
if not emp_req:
    emp_req = EmployeeRequest(
        user_id=emp_user.id,
        organization='PolicyPilot Demo Bank',
        department='Retail Credit Operations',
        designation='Assistant Underwriter',
        employee_id='PP-DEMO-EMP-999',
        work_email='priya.sharma@policypilot.local',
        status=EmployeeRequestStatus.PENDING.value
    )
    db.add(emp_req)
    db.commit()
    db.refresh(emp_req)
else:
    emp_req.status = EmployeeRequestStatus.PENDING.value
    emp_user.role = Role.CUSTOMER.value
    emp_user.onboarding_status = OnboardingStatus.PENDING_VERIFICATION.value
    db.commit()

print(f'[PASS] Pending synthetic employee request ready: id={emp_req.id}, applicant={emp_user.full_name}')

# Step 4: Inspect employee request via Admin API
r_inspect = s_admin.get(f'{BASE}/admin/employee-requests/{emp_req.id}')
assert r_inspect.status_code == 200, f'Inspect failed: {r_inspect.text}'
req_data = r_inspect.json()
assert req_data['employee_id'] == 'PP-DEMO-EMP-999'
assert req_data['status'] == 'PENDING'
print(f'[PASS] Inspected employee request: {req_data.get("full_name")} ({req_data.get("designation")}) - Status: {req_data.get("status")}')

# Step 5: Approve employee request via Admin API
r_approve = s_admin.post(f'{BASE}/admin/employee-requests/{emp_req.id}/approve')
assert r_approve.status_code == 200, f'Approve failed: {r_approve.text}'
print('[PASS] Admin approved employee request.')

# Step 6: Verify status in database and via API
r_inspect2 = s_admin.get(f'{BASE}/admin/employee-requests/{emp_req.id}')
assert r_inspect2.json()['status'] == 'APPROVED'
print('[PASS] Status confirmed updated to APPROVED.')

# Step 7: Verify employee appears in /admin/employees
r_emps = s_admin.get(f'{BASE}/admin/employees?search=priya')
assert r_emps.status_code == 200
matching = [e for e in r_emps.json() if e['id'] == str(emp_user.id)]
assert len(matching) == 1, 'Approved employee not found in /admin/employees'
print(f'[PASS] Approved employee listed in active employees directory: {matching[0].get("full_name")}')

# Step 8: Test Customers list and Customer detail
r_custs = s_admin.get(f'{BASE}/admin/customers')
assert r_custs.status_code == 200
cust_list = r_custs.json()
assert len(cust_list) > 0, 'No customers returned'
first_cust = cust_list[0]
print(f'[PASS] Customer registry retrieved: {len(cust_list)} customers. Sample: {first_cust.get("email")}')

r_cust_detail = s_admin.get(f'{BASE}/admin/customers/{first_cust.get("id")}')
assert r_cust_detail.status_code == 200
detail = r_cust_detail.json()
assert 'hashed_password' not in detail
assert 'reset_token' not in detail
assert 'applications' in detail
print(f'[PASS] Customer detail verified: {detail.get("full_name")} has {detail.get("application_count")} applications. Zero secrets exposed.')

# Step 9: Login as the newly approved employee and verify Employee Portal access
s_emp = requests.Session()
r_emp_login = s_emp.post(f'{BASE}/auth/local/login', json={'identifier': test_emp_email, 'password': 'EmployeePassword123!'})
assert r_emp_login.status_code == 200, f'Approved employee login failed: {r_emp_login.text}'

r_emp_dash = s_emp.get(f'{BASE}/api/employee/dashboard/summary')
assert r_emp_dash.status_code == 200, f'Employee dashboard access failed: {r_emp_dash.status_code} {r_emp_dash.text}'
dash_data = r_emp_dash.json()
assert 'metrics' in dash_data
print(f'[PASS] Approved employee accessed Employee Portal (:3000 backend API) successfully! Total submitted apps in queue: {dash_data["metrics"]["total_submitted_applications"]}')

# Step 10: Verify Customer Portal login & dashboard still works for regular customer
s_cust = requests.Session()
r_cust_login = s_cust.post(f'{BASE}/auth/local/login', json={'identifier': 'customer.demo@policypilot.local', 'password': 'CustomerPassword123!'})
assert r_cust_login.status_code == 200
r_cust_dash = s_cust.get(f'{BASE}/api/customer/dashboard/summary')
assert r_cust_dash.status_code == 200
print(f'[PASS] Customer Portal (:3000 backend API) verified operational. Total customer apps: {r_cust_dash.json()["applications"]["total"]}')

print('\n================ ALL 10 E2E WORKFLOW STEPS PASSED SUCCESSFULLY ================')
