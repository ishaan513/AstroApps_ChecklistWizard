import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os

# --- Page Config ---
st.set_page_config(page_title="🚀 Astro Checklist Wizard", layout="centered")

# --- Custom CSS for better UX ---
st.markdown("""
<style>
    /* Checked items styling */
    .checked-item {
        opacity: 0.6;
        text-decoration: line-through;
    }
    
    /* Progress metrics */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Mandatory item highlight */
    .mandatory-section {
        border-left: 4px solid #ef4444;
        padding-left: 1rem;
        margin: 1rem 0;
    }
    
    /* Optional item section */
    .optional-section {
        border-left: 4px solid #10b981;
        padding-left: 1rem;
        margin: 1rem 0;
    }
    
    /* Smoother transitions */
    .stCheckbox, .stTextInput {
        transition: all 0.2s ease;
    }
    
    /* Better spacing */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

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
        key="name_input"
    ).strip()
    
    # Save to session_state
    st.session_state.user_name = user_name if user_name else "Anonymous"
    
    if st.session_state.user_name == "Anonymous":
        st.warning("⚠️ Please enter your name above")
    else:
        st.success(f"✅ {st.session_state.user_name}")

    st.divider()
    
    # Set dark mode by default
    st._config.set_option("theme.base", "dark")

# --- Helper Functions ---
def get_templates():
    response = supabase.table("templates").select("id, name, items, mandatory").execute()
    templates = {}
    for row in response.data:
        templates[row["name"]] = {
            "id": row["id"],
            "items": row["items"] or [],
            "mandatory": row["mandatory"] or []
        }
    return templates

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
    current = supabase.table("checklists").select("*").eq("id", checklist_id).single().execute().data
    
    if checked is not None:
        current["checked"][index] = checked
        if checked:
            current["user_names"][index] = st.session_state.user_name
    
    if comment is not None:
        current["comments"][index] = comment
    
    current["updated_at"] = datetime.utcnow().isoformat()
    
    supabase.table("checklists").update(current).eq("id", checklist_id).execute()

# --- Main App ---
st.title("🚀 Astro Checklist Wizard")
st.caption("Multi-user collaborative checklist system")

# Mode selection with icons
mode = st.sidebar.radio(
    "🎯 Navigation",
    ["🆕 Start New Checklist", "📋 View Active Checklists", "⚙️ Manage Templates"],
    label_visibility="collapsed"
)

# Bug report link below navigation
st.sidebar.divider()
st.sidebar.markdown("### 🐛 Found a Bug?")
st.sidebar.link_button(
    "Report Issue",
    "https://forms.gle/bjbZy3aSsfHJAJEb7",
    use_container_width=True,
    type="secondary"
)

# Clean up mode string
mode = mode.split(" ", 1)[1]  # Remove emoji prefix

# Auto-apply mode change from session_state
if "mode" in st.session_state:
    mode = st.session_state.mode

# Auto-select the newly created checklist in view mode
if mode == "View Active Checklists" and "selected_checklist_id" in st.session_state:
    preselected_id = st.session_state.selected_checklist_id
else:
    preselected_id = None


if mode == "Manage Templates":
    st.header("⚙️ Template Management")
    st.caption("Create and edit checklist templates")
    
    st.divider()
    
    templates = get_templates()
    
    with st.expander("➕ Create New Template", expanded=not templates):
        name = st.text_input("Template Name", placeholder="e.g., Hot Fire Test Checklist")
        items_text = st.text_area(
            "Items (one per line)",
            height=300,
            placeholder="Check fuel pressure\nVerify connections\nConfirm safety zone clear"
        )
        
        if st.button("💾 Save Template", type="primary", use_container_width=True) and name and items_text:
            items = [line.strip() for line in items_text.split("\n") if line.strip()]
            mandatory = [True] * len(items)  # All items are mandatory
            save_template(name, items, mandatory)
            st.success(f"✅ Template '{name}' saved!")
            st.rerun()

    if templates:
        st.subheader("📚 Existing Templates")
        for t_name, t_data in list(templates.items()):
            with st.expander(f"📝 {t_name} • {len(t_data['items'])} items"):
                # Pre-fill form
                new_name = st.text_input("Template Name", value=t_name, key=f"name_edit_{t_name}")
                current_text = "\n".join(t_data["items"])
                new_items_text = st.text_area(
                    "Items (one per line)",
                    value=current_text,
                    height=300,
                    key=f"items_edit_{t_name}"
                )

                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("💾 Save Changes", key=f"save_{t_name}", type="primary", use_container_width=True):
                        lines = [line.strip() for line in new_items_text.split("\n") if line.strip()]
                        new_mandatory = [True] * len(lines)  # All items are mandatory
                        
                        if lines:
                            supabase.table("templates").upsert({
                                "name": new_name,
                                "items": lines,
                                "mandatory": new_mandatory
                            }).execute()
                            st.success(f"✅ Template '{new_name}' updated!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid items — check your list")

                with col2:
                    template_id = t_data["id"]
                    
                    # Initialize session state for this template's delete confirmation
                    delete_key = f"confirm_delete_{template_id}"
                    if delete_key not in st.session_state:
                        st.session_state[delete_key] = False
                    
                    # Show delete button or confirmation based on state
                    if not st.session_state[delete_key]:
                        if st.button("🗑️ Delete", key=f"delete_btn_{template_id}", type="secondary", use_container_width=True):
                            st.session_state[delete_key] = True
                            st.rerun()
                    else:
                        st.error(f"⚠️ Delete '{t_name}'?")
                        
                        if st.button("🛑 Yes, Delete", key=f"confirm_yes_{template_id}", type="primary", use_container_width=True):
                            response = supabase.table("templates").delete().eq("id", template_id).execute()
                            
                            if response.data and len(response.data) > 0:
                                st.success(f"✅ Template deleted!")
                                if delete_key in st.session_state:
                                    del st.session_state[delete_key]
                                st.rerun()
                            else:
                                st.error("❌ Delete failed")
                                st.session_state[delete_key] = False
                        
                        if st.button("Cancel", key=f"cancel_delete_{template_id}", use_container_width=True):
                            st.session_state[delete_key] = False
                            st.rerun()
    else:
        st.info("💡 No templates yet — create one above!")

elif mode == "Start New Checklist":
    st.header("🆕 Start New Checklist")
    st.caption("Create a new checklist session from a template")
    
    st.divider()
    
    templates = get_templates()
    if not templates:
        st.warning("⚠️ No templates available")
        st.info("💡 Create a template in 'Manage Templates' first")
    else:
        template_name = st.selectbox(
            "📋 Select Template",
            list(templates.keys()),
            help="Choose a checklist template to use"
        )
        
        # Show template preview
        if template_name:
            template_data = templates[template_name]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Items", len(template_data["items"]))
            with col2:
                st.metric("Estimated Time", f"~{len(template_data['items']) * 2} min")
        
        session_name = st.text_input(
            "🏷️ Session Name",
            placeholder="e.g., Jan 4 Hot Fire Test",
            help="Give this checklist session a unique name"
        )
        
        if st.button("🚀 Start Checklist", type="primary", disabled=not session_name, use_container_width=True):
            with st.spinner("Creating checklist..."):
                new_id = start_checklist(session_name, template_name, templates[template_name])
                if new_id:
                    st.success("✅ Checklist started successfully!")
                    st.session_state.mode = "View Active Checklists"
                    st.session_state.selected_checklist_id = new_id
                    st.rerun()
                else:
                    st.error("❌ Failed to start checklist")

elif mode == "View Active Checklists":
    active_checklists = get_active_checklists()
    
    if not active_checklists:
        st.info("💡 No active checklists")
        st.caption("Start a new checklist to get going!")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    else:
        # Session selector
        selected_id = st.selectbox(
            "📋 Active Sessions",
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
        
        st.divider()
        
        # Header with refresh
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"{session['session_name']}")
            st.caption(f"Template: {session['template_name']}")
        with col2:
            # Subtle auto-refresh indicator
            if "refresh_countdown" not in st.session_state:
                st.session_state.refresh_countdown = 10
            
            st.session_state.refresh_countdown -= 1
            if st.session_state.refresh_countdown <= 0:
                st.session_state.refresh_countdown = 10
                st.rerun()
            
            st.caption(f"🔄 {st.session_state.refresh_countdown}s")
            if st.button("Refresh", key="manual_refresh", use_container_width=True):
                st.rerun()

        # --- Enhanced Progress Display ---
        total = len(session["items"])
        checked_count = sum(session["checked"])

        progress = checked_count / total if total > 0 else 0

        # Overall Progress Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overall Progress", f"{int(progress * 100)}%", f"{checked_count}/{total}")
        with col2:
            remaining = total - checked_count
            st.metric("Remaining Items", remaining)

        # Progress bar with color coding
        if progress == 1.0:
            st.progress(progress, text="✅ Complete!")
        else:
            st.progress(progress, text=f"🔄 {int(progress * 100)}% Complete")

        st.divider()

        # --- All Items ---
        st.markdown("### 📋 Checklist Items")
        for idx, (i, item) in enumerate(enumerate(session["items"]), 1):
            is_checked = session["checked"][i]
            current_user = session["user_names"][i] if i < len(session["user_names"]) and session["user_names"][i] else ""

            # Item container
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    label = f"**{idx}.** {item}"
                    if current_user:
                        label += f" ✓ *by {current_user}*"

                    checked = st.checkbox(
                        label,
                        value=is_checked,
                        key=f"check_{selected_id}_{i}"
                    )
                    
                    if checked != is_checked:
                        update_checklist(selected_id, i, checked=checked)
                        st.rerun()

                    # Comment field - only show if checked or has existing comment
                    if is_checked or session["comments"][i]:
                        comment = st.text_input(
                            "💬 Comment",
                            value=session["comments"][i],
                            key=f"comm_{selected_id}_{i}",
                            label_visibility="collapsed",
                            placeholder="Add a comment..."
                        )
                        if comment != session["comments"][i]:
                            update_checklist(selected_id, i, comment=comment)

                with col2:
                    st.file_uploader("📷", type=["jpg","png"], key=f"photo_{selected_id}_{i}", label_visibility="collapsed")
                
                st.divider()

        # Complete button
        st.markdown("---")
        complete_disabled = progress < 1.0
        if st.button(
            "✅ Mark as Complete & Archive",
            type="primary",
            disabled=complete_disabled,
            use_container_width=True,
            help="All items must be checked first" if complete_disabled else None
        ):
            supabase.table("checklists").update({"completed": True}).eq("id", selected_id).execute()
            st.success("🎉 Checklist completed and archived!")
            st.rerun()

st.caption("Built with ❤️ for mission-critical operations | Ishaan Patel")