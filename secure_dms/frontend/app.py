import streamlit as st
import api_client as api

st.set_page_config(page_title="Secure DMS", page_icon="🔒", layout="wide")

ROLES = ["master", "investigating_officer", "judge", "prosecutor", "forensic", "clerk"]

for key, default in [("token", None), ("username", None), ("role", None),
                      ("user_id", None), ("page", "Dashboard"), ("active_case", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


def logout():
    for key in ["token", "username", "role", "user_id", "active_case"]:
        st.session_state[key] = None
    st.session_state.page = "Dashboard"


def login_signup_page():
    st.title("🔒 Secure Digital Document Management System")
    st.caption("Legal & investigation document management — encrypted storage, tamper-evident audit trail, role-based access")
    tab1, tab2 = st.tabs(["Login", "Sign up"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            r = api.login(username, password)
            if r.status_code == 200:
                data = r.json()
                st.session_state.token = data["access_token"]
                st.session_state.username = data["username"]
                st.session_state.role = data["role"]
                st.session_state.user_id = data["user_id"]
                st.rerun()
            else:
                try:
                    st.error(r.json().get("detail", "Login failed"))
                except Exception:
                    st.error("Login failed — is the backend running?")
        st.info("Default master account — username: `master`, password: `Master@123`. Change this after first login.")

    with tab2:
        with st.form("signup_form"):
            su_username = st.text_input("Choose a username")
            su_email = st.text_input("Email")
            su_full_name = st.text_input("Full name")
            su_password = st.text_input("Choose a password", type="password")
            su_submitted = st.form_submit_button("Create account", use_container_width=True)
        if su_submitted:
            r = api.signup(su_username, su_email, su_full_name, su_password)
            if r.status_code == 200:
                st.success("Account created with role 'clerk'. Ask a master account holder to grant case access or raise your role.")
            else:
                try:
                    st.error(r.json().get("detail", "Signup failed"))
                except Exception:
                    st.error("Signup failed — is the backend running?")


def dashboard_page():
    st.subheader("Cases")

    with st.expander("+ New case"):
        with st.form("new_case"):
            cn = st.text_input("Case number", placeholder="FIR-2026-0501")
            title = st.text_input("Title")
            desc = st.text_area("Description")
            sens = st.selectbox("Sensitivity", ["normal", "sensitive"])
            sub = st.form_submit_button("Create case")
        if sub:
            r = api.create_case(st.session_state.token, cn, title, desc, sens)
            if r.status_code == 200:
                st.success("Case created")
                st.rerun()
            else:
                st.error(r.json().get("detail", "Failed to create case"))

    r = api.list_cases(st.session_state.token)
    if r.status_code != 200:
        st.error("Could not load cases")
        return
    cases = r.json()
    if not cases:
        st.info("No cases visible to you yet. Create one above, or ask a master account to grant you access.")
        return

    for c in cases:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{c['case_number']} — {c['title']}**")
            badge = "🔴 sensitive" if c["sensitivity_level"] == "sensitive" else "normal"
            col1.caption(f"Status: {c['status']}  |  Sensitivity: {badge}")
            if col2.button("Open", key=f"open_{c['id']}", use_container_width=True):
                st.session_state.active_case = c["id"]
                st.session_state.page = "Case detail"
                st.rerun()


def case_detail_page():
    case_id = st.session_state.get("active_case")
    if not case_id:
        st.info("Select a case from the Dashboard first.")
        return
    r = api.get_case(st.session_state.token, case_id)
    if r.status_code != 200:
        st.error("Cannot access this case")
        return
    case = r.json()
    st.subheader(f"{case['case_number']} — {case['title']}")
    st.caption(case.get("description") or "No description")

    tab1, tab2, tab3 = st.tabs(["📄 Documents", "⬆️ Upload", "🔑 Access control"])

    with tab1:
        dr = api.list_documents(st.session_state.token, case_id)
        docs = dr.json() if dr.status_code == 200 else []
        if not docs:
            st.info("No documents yet — upload one in the Upload tab.")
        for d in docs:
            with st.container(border=True):
                st.markdown(f"**{d['title']}**  \n`{d['doc_type']}` · classification: `{d['classification']}`")
                c1, c2, c3 = st.columns([1, 1, 2])
                if c1.button("⬇️ Download", key=f"dl_{d['id']}"):
                    dlr = api.download_document(st.session_state.token, d["id"])
                    if dlr.status_code == 200:
                        st.download_button("Save file", dlr.content, file_name=d["title"], key=f"save_{d['id']}")
                    else:
                        try:
                            st.error(dlr.json().get("detail", "Download failed"))
                        except Exception:
                            st.error("Download failed")
                if c2.button("🕓 Versions", key=f"v_{d['id']}"):
                    vr = api.list_versions(st.session_state.token, d["id"])
                    if vr.status_code == 200:
                        st.json(vr.json())
                with c3:
                    nv_file = st.file_uploader("New version", key=f"nv_{d['id']}", label_visibility="collapsed")
                    if nv_file is not None and st.button("Upload as new version", key=f"nvbtn_{d['id']}"):
                        resp = api.upload_new_version(st.session_state.token, d["id"], nv_file, "revision")
                        if resp.status_code == 200:
                            st.success("New version uploaded")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Failed"))

    with tab2:
        with st.form("upload_form"):
            up_file = st.file_uploader("File")
            up_title = st.text_input("Title")
            up_type = st.selectbox("Document type", [
                "FIR", "Chargesheet", "Witness statement", "Evidence record",
                "Forensic report", "Court filing", "Legal notice", "Other",
            ])
            up_class = st.selectbox("Classification", ["internal", "confidential", "restricted"])
            up_sub = st.form_submit_button("Upload")
        if up_sub:
            if not up_file:
                st.error("Choose a file first")
            else:
                resp = api.upload_document(st.session_state.token, up_file, up_title, up_type, up_class, case_id)
                if resp.status_code == 200:
                    st.success("Document encrypted and stored")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Upload failed"))

    with tab3:
        st.caption("Grant investigators, judges, prosecutors, or forensic staff access to this case.")
        ar = api.list_case_access(st.session_state.token, case_id)
        if ar.status_code == 200 and ar.json():
            st.table(ar.json())
        else:
            st.info("No access grants yet besides the case creator.")

        ur = api.list_users(st.session_state.token)
        user_options = {}
        if ur.status_code == 200:
            user_options = {f"{u['username']} ({u['role']})": u["id"] for u in ur.json()}

        with st.form("grant_form"):
            if user_options:
                g_label = st.selectbox("User", list(user_options.keys()))
                g_user_id = user_options[g_label]
            else:
                g_user_id = st.text_input("User ID to grant (master view unavailable)")
            g_perm = st.selectbox("Permission", ["read", "write"])
            g_sub = st.form_submit_button("Grant access")
        if g_sub:
            gr = api.grant_access(st.session_state.token, g_user_id, case_id, None, g_perm)
            if gr.status_code == 200:
                st.success("Access granted")
                st.rerun()
            else:
                st.error(gr.json().get("detail", "Failed to grant access"))


def audit_page():
    st.subheader("Audit trail")
    st.caption("Every action — including denied access attempts — is written as a chained, tamper-evident hash-chain entry.")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔍 Verify chain integrity", use_container_width=True):
            vr = api.verify_audit_chain(st.session_state.token)
            result = vr.json()
            if result["status"] == "intact":
                st.success(f"✅ Chain intact — {result['total_logs']} log entries verified")
            else:
                st.error(f"⚠️ TAMPER DETECTED at log `{result['broken_at_log_id']}` — {result['reason']}")

    resource_filter = st.text_input("Filter by resource ID (optional)")
    lr = api.list_audit_logs(st.session_state.token, resource_filter or None)
    if lr.status_code == 200:
        st.dataframe(lr.json(), use_container_width=True, height=500)
    else:
        st.error("Could not load audit logs")


def admin_page():
    st.subheader("Admin — authority management")
    st.caption("Master-only panel. Promote or demote roles, suspend or reactivate accounts.")
    ur = api.list_users(st.session_state.token)
    if ur.status_code != 200:
        st.error("Master privilege required")
        return
    users = ur.json()
    for u in users:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            c1.markdown(f"**{u['username']}**  \n{u['email']}")
            new_role = c2.selectbox(
                "Role", ROLES, index=ROLES.index(u["role"]) if u["role"] in ROLES else 0,
                key=f"role_{u['id']}", label_visibility="collapsed",
            )
            if c2.button("Update role", key=f"updrole_{u['id']}"):
                rr = api.change_role(st.session_state.token, u["id"], new_role)
                if rr.status_code == 200:
                    st.success(f"Updated {u['username']} to {new_role}")
                    st.rerun()
                else:
                    st.error(rr.json().get("detail", "Failed"))
            status_label = "Suspend" if u["status"] == "active" else "Activate"
            if c3.button(status_label, key=f"stat_{u['id']}"):
                new_status = "suspended" if u["status"] == "active" else "active"
                api.change_status(st.session_state.token, u["id"], new_status)
                st.rerun()
            c4.caption(f"Status: **{u['status']}**")


# ---------------- main ----------------
if not st.session_state.token:
    login_signup_page()
else:
    st.sidebar.title("🔒 Secure DMS")
    st.sidebar.markdown(f"**{st.session_state.username}**  \nRole: `{st.session_state.role}`")
    pages = ["Dashboard", "Case detail", "Audit log"]
    if st.session_state.role == "master":
        pages.append("Admin")

    current = st.session_state.page if st.session_state.page in pages else "Dashboard"
    page = st.sidebar.radio("Navigate", pages, index=pages.index(current))
    st.session_state.page = page

    if st.sidebar.button("Logout", use_container_width=True):
        logout()
        st.rerun()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Case detail":
        case_detail_page()
    elif page == "Audit log":
        audit_page()
    elif page == "Admin":
        admin_page()
