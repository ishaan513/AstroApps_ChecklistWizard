import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os

# --- Page Config ---
st.set_page_config(page_title="🚀 Team Checklist Manager", layout="centered")

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
st.title("🚀 Team Checklist Manager")

mode = st.sidebar.selectbox("Mode", ["Start New Checklist", "View Active Checklists", "Manage Templates"])

# Real-time subscription (only in view mode to avoid conflicts)
if mode == "View Active Checklists":
    def on_realtime(payload):
        st.rerun()

    supabase.realtime.connect()
    supabase.table("checklists").on("UPDATE", on_realtime).subscribe()

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
    for t_name in templates:
        if st.button(f"📝 Edit / Delete: {t_name}"):
            st.session_state.editing_template = t_name
        if "editing_template" in st.session_state and st.session_state.editing_template == t_name:
            st.write(templates[t_name]["items"])

elif mode == "Start New Checklist":
    templates = get_templates()
    if not templates:
        st.info("No templates yet. Create one in 'Manage Templates' first.")
    else:
        template_name = st.selectbox("Select Template", list(templates.keys()))
        session_name = st.text_input("Session Name (e.g., 'Jan 4 Hot Fire')")
        if st.button("Start Checklist") and session_name:
            start_checklist(session_name, template_name, templates[template_name])
            st.success("Checklist started!")
            st.rerun()

elif mode == "View Active Checklists":
    # --- Improved Realtime Subscription ---
    if "checklist_channel" not in st.session_state:
        def handle_realtime(payload):
            # Trigger a rerun when any UPDATE happens on checklists table
            st.session_state.realtime_trigger = datetime.now()

        # Subscribe once and store the channel
        channel = supabase.table("checklists").on("UPDATE", handle_realtime).subscribe()
        st.session_state.checklist_channel = channel

    # Rerun the app if we received a realtime event
    if st.session_state.get("realtime_trigger"):
        st.rerun()

    # Fetch latest data (will reflect changes from other devices)
    active_checklists = get_active_checklists()
    
    if not active_checklists:
        st.info("No active checklists. Start one!")
    else:
        selected_id = st.selectbox(
            "Active Sessions",
            options=list(active_checklists.keys()),
            format_func=lambda cid: f"{active_checklists[cid]['session_name']} – {active_checklists[cid]['template_name']}"
        )
        session = active_checklists[selected_id]
        
        st.subheader(f"{session['session_name']} – {session['template_name']}")

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
            current_user = session["user_names"][i] if i < len(session["user_names"]) else ""

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

st.caption("Real-time multi-user • Changes sync instantly across devices")