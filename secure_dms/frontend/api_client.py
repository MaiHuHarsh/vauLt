import requests

BASE_URL = "http://localhost:8000"


def _headers(token=None):
    return {"Authorization": f"Bearer {token}"} if token else {}


def signup(username, email, full_name, password):
    return requests.post(f"{BASE_URL}/auth/signup", json={
        "username": username, "email": email, "full_name": full_name, "password": password,
    })


def login(username, password):
    return requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})


def get_me(token):
    return requests.get(f"{BASE_URL}/users/me", headers=_headers(token))


def list_users(token):
    return requests.get(f"{BASE_URL}/users", headers=_headers(token))


def change_role(token, user_id, role):
    return requests.patch(f"{BASE_URL}/users/{user_id}/role", json={"role": role}, headers=_headers(token))


def change_status(token, user_id, status):
    return requests.patch(f"{BASE_URL}/users/{user_id}/status", json={"status": status}, headers=_headers(token))


def create_case(token, case_number, title, description, sensitivity_level):
    return requests.post(f"{BASE_URL}/cases", json={
        "case_number": case_number, "title": title,
        "description": description, "sensitivity_level": sensitivity_level,
    }, headers=_headers(token))


def list_cases(token):
    return requests.get(f"{BASE_URL}/cases", headers=_headers(token))


def get_case(token, case_id):
    return requests.get(f"{BASE_URL}/cases/{case_id}", headers=_headers(token))


def upload_document(token, file, title, doc_type, classification, case_id):
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    data = {"title": title, "doc_type": doc_type, "classification": classification}
    if case_id:
        data["case_id"] = case_id
    return requests.post(f"{BASE_URL}/documents/upload", files=files, data=data, headers=_headers(token))


def upload_new_version(token, document_id, file, change_reason):
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    data = {"change_reason": change_reason}
    return requests.post(f"{BASE_URL}/documents/{document_id}/new-version", files=files, data=data,
                          headers=_headers(token))


def list_documents(token, case_id=None):
    params = {"case_id": case_id} if case_id else {}
    return requests.get(f"{BASE_URL}/documents", params=params, headers=_headers(token))


def download_document(token, document_id):
    return requests.get(f"{BASE_URL}/documents/{document_id}/download", headers=_headers(token))


def list_versions(token, document_id):
    return requests.get(f"{BASE_URL}/documents/{document_id}/versions", headers=_headers(token))


def grant_access(token, user_id, case_id, document_id, permission, expires_at=None):
    payload = {"user_id": user_id, "permission": permission}
    if case_id:
        payload["case_id"] = case_id
    if document_id:
        payload["document_id"] = document_id
    if expires_at:
        payload["expires_at"] = expires_at
    return requests.post(f"{BASE_URL}/access/grant", json=payload, headers=_headers(token))


def revoke_access(token, access_id):
    return requests.post(f"{BASE_URL}/access/revoke/{access_id}", headers=_headers(token))


def list_case_access(token, case_id):
    return requests.get(f"{BASE_URL}/access/case/{case_id}", headers=_headers(token))


def list_audit_logs(token, resource_id=None):
    params = {"resource_id": resource_id} if resource_id else {}
    return requests.get(f"{BASE_URL}/audit/logs", params=params, headers=_headers(token))


def verify_audit_chain(token):
    return requests.get(f"{BASE_URL}/audit/verify", headers=_headers(token))
