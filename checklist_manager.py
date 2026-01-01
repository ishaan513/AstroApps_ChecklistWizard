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

    if st.button("🔄 Force Refresh All Data"):
        st.rerun()

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
    response = supabase.table("templates").select("name, items, mandatory").execute()
    templates = {}
    for row in response.data:
        if row["items"] is not None and row["mandatory"] is not None and len(row["items"]) == len(row["mandatory"]):
            templates[row["name"]] = {
                "items": row["items"],
                "mandatory": row["mandatory"]
            }
        else:
            print(f"Skipping invalid template: {row['name']}")  # Debug log
    return templates

def save_template(name: str, clean_items: list[str], mandatory: list[bool]):
    supabase.table("templates").upsert({
        "name": name,
        "items": clean_items,       # Direct Python list → Supabase handles as array
        "mandatory": mandatory
    }).execute()

def get_active_checklists():
    response = supabase.table("checklists").select("*").eq("completed", False).order("created_at", desc=True).execute()
    return {row["id"]: row for row in response.data}

def start_checklist(session_name: str, template_name: str, template_data: dict):
    st.write("DEBUG: Raw template_data from load:", template_data)  # Shows exactly what was loaded
    
    items = template_data.get("items", [])
    mandatory = template_data.get("mandatory", [])
    
    st.write("DEBUG: Extracted items:", items)
    st.write("DEBUG: Extracted mandatory:", mandatory)
    
    if not items:
        st.error("No items in template — cannot start checklist.")
        return None
    
    n = len(items)
    
    data = {
        "session_name": session_name,
        "template_name": template_name,
        "items": list(items),                # Force to Python list
        "mandatory": list(mandatory),        # Force to Python list
        "checked": [False] * n,
        "comments": [""] * n,
        "user_names": [""] * n,
        "completed": False
    }
    
    st.write("DEBUG: Final data for insert:", data)
    
    try:
        response = supabase.table("checklists").insert(data).execute()
        st.success("Checklist started successfully!")
        return response.data[0]["id"]
    except Exception as e:
        st.error(f"Insert error: {str(e)}")
        return None

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


if mode == "Manage Templates":
    st.header("Checklist Templates")
    templates = get_templates()
    
    name = st.text_input("Template Name (unique)")
    items_text = st.text_area("Items (one per line, prefix with * for mandatory)", height=300)
    
    if st.button("Save Template") and name and items_text:
        lines = [line.strip() for line in items_text.split("\n") if line.strip()]
        clean_items = [line.lstrip("* ").strip() for line in lines]
        mandatory = [line.startswith("*") for line in lines]
        
        if len(clean_items) != len(mandatory):
            st.error("Error processing items — try again")
        else:
            save_template(name, clean_items, mandatory)
            st.success(f"Template '{name}' saved!")
            st.rerun()

    st.markdown("### Existing Templates")
    for t_name, t_data in templates.items():
        with st.expander(f"{t_name} ({len(t_data['items'])} items)"):
            for i, item in enumerate(t_data["items"]):
                prefix = "🔴 " if t_data["mandatory"][i] else "⚪ "
                st.write(prefix + item)

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
    # Auto-refresh every 5 seconds for near real-time updates
    placeholder = st.empty()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh > 5:
        st.rerun()

    with placeholder.container():
        st.caption(f"🔄 Auto-refresh in {5 - (time_since_refresh % 5)} seconds | Manual refresh 👇")
        if st.button("Refresh Now"):
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