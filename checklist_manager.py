import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os

# --- Page Config ---
st.set_page_config(page_title="🚀 Astro Checklist Wizard", layout="centered")

# --- Supabase Setup ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# --- Session State for User Name ---
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# --- Sidebar: User Name (Required) + Theme Toggle ---
with st.sidebar:
    st.markdown("### 👤 Your Identifier")
    
    # Persistent name input
    user_name = st.text_input(
        "Enter your name (required for tracking who checks items)",
        value=st.session_state.get("user_name", ""),
        key="name_input"  # This makes it update session_state automatically
    ).strip()
    
    # Save to session_state
    st.session_state.user_name = user_name if user_name else "Anonymous"
    
    if st.session_state.user_name == "Anonymous":
        st.warning("⚠️ Please enter your name above — otherwise checks will show as 'Anonymous'")
    else:
        st.success(f"Logged in as: **{st.session_state.user_name}** 🚀")

    st.markdown("### Appearance")
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    def toggle_theme():
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()

    if st.session_state.theme == "light":
        if st.button("🌙 Dark Mode"):
            toggle_theme()
    else:
        if st.button("☀️ Light Mode"):
            toggle_theme()

    if st.session_state.theme == "dark":
        st._config.set_option("theme.base", "dark")
    else:
        st._config.set_option("theme.base", "light")

# --- Helper Functions ---
def get_templates():
    response = supabase.table("templates").select("*").execute()
    return {row["name"]: {"items": row["items"], "mandatory": row["mandatory"]} 
            for row in response.data}

def save_template(name: str, items: list[str], mandatory: list[bool]):
    supabase.table("templates").upsert({
        "name": name,
        "items": items,
        "mandatory": mandatory
    }).execute()

def get_active_checklists():
    response = supabase.table("checklists").select("*").eq("completed", False).order("created_at", desc=True).execute()
    return {row["id"]: row for row in response.data}

def start_checklist(session_name: str, template_name: str, template_data: dict):
    n = len(template_data["items"])
    data = {
        "session_name": session_name,
        "template_name": template_name,
        "items": template_data["items"],         
        "mandatory": template_data["mandatory"],  
        "checked": [False] * n,
        "comments": [""] * n,
        "user_names": [""] * n,
        "completed": False
    }
    response = supabase.table("checklists").insert(data).execute()
    return response.data[0]["id"]

def update_checklist(checklist_id: str, index: int, checked: bool = None, comment: str = None):
    # Fetch current state
    current = supabase.table("checklists").select("*").eq("id", checklist_id).single().execute().data
    
    if checked is not None:
        current["checked"][index] = checked
        # Record who checked it (only when checking, not unchecking)
        if checked:
            current["user_names"][index] = st.session_state.user_name
    
    if comment is not None:
        current["comments"][index] = comment
    
    current["updated_at"] = datetime.utcnow().isoformat()
    
    supabase.table("checklists").update(current).eq("id", checklist_id).execute()

# --- Main App ---
st.title("🚀 Astro Checklist Wizard")

mode = st.sidebar.selectbox("Mode", ["Start New Checklist", "View Active Checklists", "Manage Templates"])

# Auto-apply mode change from session_state
if "mode" in st.session_state:
    mode = st.session_state.mode

# Auto-select the newly created checklist in view mode
if mode == "View Active Checklists" and "selected_checklist_id" in st.session_state:
    # We'll use this in the view block
    preselected_id = st.session_state.selected_checklist_id
else:
    preselected_id = None


if mode == "Manage Templates":
    st.header("Checklist Templates")
    templates = get_templates()
    
    name = st.text_input("Template Name")
    items_text = st.text_area("Items (one per line, prefix with * for mandatory)", height=300)
    
    if st.button("Save Template") and name and items_text:
        items = [line.strip() for line in items_text.split("\n") if line.strip()]
        mandatory = [line.startswith("*") for line in items_text.split("\n")]
        clean_items = [item.lstrip("* ").strip() for item in items]
        save_template(name, clean_items, mandatory)
        st.success("Template saved!")
        st.rerun()

    st.markdown("### Existing Templates")
    if templates:
        for t_name, t_data in list(templates.items()):  # list() to avoid runtime dict change
            with st.expander(f"📝 Edit / Delete: {t_name} ({len(t_data['items'])} items)"):
                # Pre-fill form
                new_name = st.text_input("Template Name", value=t_name, key=f"name_edit_{t_name}")
                current_text = "\n".join(
                    f"* {item}" if mandatory else item
                    for item, mandatory in zip(t_data["items"], t_data["mandatory"])
                )
                new_items_text = st.text_area(
                    "Items (one per line, prefix with * for mandatory)",
                    value=current_text,
                    height=300,
                    key=f"items_edit_{t_name}"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💾 Save Changes", key=f"save_{t_name}", type="primary"):
                        lines = [line.strip() for line in new_items_text.split("\n") if line.strip()]
                        clean_items = [line.lstrip("* ").strip() for line in lines]
                        new_mandatory = [line.startswith("*") for line in lines]
                        
                        if clean_items and len(clean_items) == len(new_mandatory):
                            supabase.table("templates").upsert({
                                "name": new_name,
                                "items": clean_items,
                                "mandatory": new_mandatory
                            }).execute()
                            st.success(f"Template saved as '{new_name}'!")
                            st.rerun()
                        else:
                            st.error("Invalid items — check your list")

                with col2:
                    st.write("")  # Spacer

                with col3:
                    if st.button("🗑️ Delete Template", key=f"delete_btn_{t_name}", type="secondary"):
                        st.error(f"⚠️ Permanent delete of '{t_name}' — no undo!")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("🛑 Yes, Delete", key=f"confirm_delete_{t_name}", type="primary"):
                                # Fetch the template ID by name
                                response_find = supabase.table("templates").select("id").eq("name", t_name).execute()
                                if response_find.data:
                                    template_id = response_find.data[0]["id"]
                                    print("DEBUG: Deleting template with ID:", template_id)  # Logs to server
                                    response_delete = supabase.table("templates").delete().eq("id", template_id).execute()
                                    if len(response_delete.data) > 0:
                                        st.success(f"Template '{t_name}' deleted!")
                                        st.rerun()
                                    else:
                                        st.error("Delete failed — no matching ID found")
                                else:
                                    st.error("Template not found — already deleted or name mismatch")
                        with col_no:
                            if st.button("Cancel", key=f"cancel_delete_{t_name}"):
                                st.rerun()
    else:
        st.info("No templates yet — create one above!")

elif mode == "Start New Checklist":
    templates = get_templates()
    if not templates:
        st.info("No templates yet. Create one in 'Manage Templates' first.")
    else:
        template_name = st.selectbox("Select Template", list(templates.keys()))
        session_name = st.text_input("Session Name (e.g., 'Jan 4 Hot Fire')")
        
        if st.button("Start Checklist 🚀", type="primary") and session_name:
            with st.spinner("Creating checklist..."):
                new_id = start_checklist(session_name, template_name, templates[template_name])
                if new_id:
                    st.success("✅ Checklist started successfully!")
                    # Auto-switch to view mode and select the new one
                    st.session_state.mode = "View Active Checklists"
                    st.session_state.selected_checklist_id = new_id
                    st.rerun()
                else:
                    st.error("Failed to start checklist. Check template and try again.")

elif mode == "View Active Checklists":
    active_checklists = get_active_checklists()
    
    if not active_checklists:
        st.info("No active checklists. Start one!")
        if st.button("Refresh"):
            st.rerun()
    else:
        selected_id = st.selectbox(
            "Active Sessions",
            options=list(active_checklists.keys()),
            format_func=lambda cid: f"{active_checklists[cid]['session_name']} – {active_checklists[cid]['template_name']}",
            index=0 if preselected_id is None else (
                list(active_checklists.keys()).index(preselected_id) 
                if preselected_id in active_checklists else 0
            )
        )
        # Clear the preselection after first load
        if preselected_id:
            del st.session_state.selected_checklist_id

        session = active_checklists[selected_id]
        
        st.subheader(f"{session['session_name']} – {session['template_name']}")

        # Auto-refresh countdown
        placeholder = st.empty()
        refresh_interval = 5
        if "refresh_countdown" not in st.session_state:
            st.session_state.refresh_countdown = refresh_interval
        
        st.session_state.refresh_countdown -= 1
        if st.session_state.refresh_countdown <= 0:
            st.session_state.refresh_countdown = refresh_interval
            st.rerun()
        
        with placeholder:
            st.caption(f"🔄 Auto-refresh in {st.session_state.refresh_countdown} seconds | {datetime.now().strftime('%H:%M:%S')}")
            if st.button("Refresh Now"):
                st.rerun()

        # --- Progress Bar ---
        total = len(session["items"])
        checked_count = sum(session["checked"])
        mandatory_count = sum(session["mandatory"])
        checked_mandatory = sum(session["checked"][i] for i in range(total) if session["mandatory"][i])

        progress = checked_count / total if total > 0 else 0
        mandatory_progress = checked_mandatory / mandatory_count if mandatory_count > 0 else 1

        st.progress(progress)
        if progress == 1 and (mandatory_count == 0 or mandatory_progress == 1):
            st.success("✅ Checklist Complete!")
        elif mandatory_progress < 1:
            st.error(f"⚠️ {checked_mandatory}/{mandatory_count} mandatory items completed")
        else:
            st.info(f"{checked_count}/{total} items completed")

        if mandatory_count > 0:
            st.progress(mandatory_progress)
            st.caption(f"Mandatory: {checked_mandatory}/{mandatory_count}")

        # --- Checklist Items ---
        for i, item in enumerate(session["items"]):
            is_mandatory = session["mandatory"][i]
            current_user = session["user_names"][i] if i < len(session["user_names"]) and session["user_names"][i] else ""

            col1, col2 = st.columns([4, 1])
            with col1:
                label = f"{'🔴' if is_mandatory else '⚪'} {item}"
                if current_user:
                    label += f" (by {current_user})"

                checked = st.checkbox(
                    label,
                    value=session["checked"][i],
                    key=f"check_{selected_id}_{i}"
                )
                if checked != session["checked"][i]:
                    update_checklist(selected_id, i, checked=checked)
                    st.rerun()

                if is_mandatory and not checked:
                    st.warning("Mandatory item")

                comment = st.text_input(
                    "Comment",
                    value=session["comments"][i],
                    key=f"comm_{selected_id}_{i}"
                )
                if comment != session["comments"][i]:
                    update_checklist(selected_id, i, comment=comment)

            with col2:
                st.file_uploader("Photo", type=["jpg","png"], key=f"photo_{selected_id}_{i}")

        if st.button("Mark as Complete & Archive", type="primary"):
            supabase.table("checklists").update({"completed": True}).eq("id", selected_id).execute()
            st.success("Checklist completed!")
            st.rerun()

st.caption("Multi-user collaborative checklist • Refreshes automatically")