import streamlit as st
import pandas as pd
import json
from datetime import datetime

# Simple JSON file to store templates and active checklists
TEMPLATES_FILE = "checklists_templates.json"
ACTIVE_FILE = "active_checklists.json"

# Load/save helpers
def load_json(file): 
    try: 
        with open(file, "r") as f: 
            return json.load(f)
    except: 
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# Sidebar: Choose or create checklist
st.title("🚀 Astro Checklist Wizard")

import streamlit as st

# --- Dark Mode Toggle ---
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

# Place toggle in sidebar
with st.sidebar:
    st.markdown("### Appearance")
    if st.session_state.theme == "light":
        if st.button("🌙 Switch to Dark Mode"):
            toggle_theme()
            st.rerun()
    else:
        if st.button("☀️ Switch to Light Mode"):
            toggle_theme()
            st.rerun()

# Apply the theme (Streamlit respects system preference by default, but we override)
if st.session_state.theme == "dark":
    st._config.set_option("theme.base", "dark")
else:
    st._config.set_option("theme.base", "light")

mode = st.sidebar.selectbox("Mode", ["Start New Checklist", "View Active Checklists", "Manage Templates"])

if mode == "Manage Templates":
    # Simple template editor (you can expand this)
    st.header("Checklist Templates")
    templates = load_json(TEMPLATES_FILE)
    name = st.text_input("Template Name")
    items = st.text_area("Items (one per line, prefix with * for mandatory)", height=300)
    if st.button("Save Template"):
        templates[name] = {
            "items": items.split("\n"),
            "mandatory": [i.startswith("*") for i in items.split("\n")]
        }
        save_json(TEMPLATES_FILE, templates)
        st.success("Template saved!")

elif mode == "Start New Checklist":
    templates = load_json(TEMPLATES_FILE)
    template_name = st.selectbox("Select Template", list(templates.keys()))
    session_name = st.text_input("Session Name (e.g., 'Jan 4 Hot Fire')")
    if st.button("Start Checklist"):
        active = load_json(ACTIVE_FILE)
        active[f"{session_name}_{datetime.now().isoformat()}"] = {
            "template": template_name,
            "items": templates[template_name]["items"],
            "mandatory": templates[template_name]["mandatory"],
            "checked": [False] * len(templates[template_name]["items"]),
            "comments": [""] * len(templates[template_name]["items"]),
            "photos": [None] * len(templates[template_name]["items"])
        }
        save_json(ACTIVE_FILE, active)
        st.success("Checklist started!")

elif mode == "View Active Checklists":
    active = load_json(ACTIVE_FILE)
    if not active:
        st.info("No active checklists.")
    else:
        selected = st.selectbox("Active Sessions", list(active.keys()))
        session = active[selected]
        st.subheader(f"{selected.split('_')[0]} – {session['template']}")

        # --- Progress Bar Calculation ---
        total_items = len(session["items"])
        checked_items = sum(session["checked"])
        mandatory_items = sum(session["mandatory"])
        checked_mandatory = sum(
            session["checked"][i] for i in range(total_items) if session["mandatory"][i]
        )

        progress = checked_items / total_items if total_items > 0 else 0
        mandatory_progress = checked_mandatory / mandatory_items if mandatory_items > 0 else 1

        # Progress bar with color logic
        if progress == 1 and (mandatory_items == 0 or mandatory_progress == 1):
            bar_color = "success"
            status = "✅ Complete!"
        elif mandatory_progress < 1:
            bar_color = "error"
            status = f"⚠️ {checked_mandatory}/{mandatory_items} mandatory items done"
        else:
            bar_color = "normal"
            status = f"{checked_items}/{total_items} items completed"

        st.progress(progress)
        st.caption(f"**Progress:** {status}")

        # Optional: Show separate mandatory progress
        if mandatory_items > 0:
            st.progress(mandatory_progress)
            st.caption(f"**Mandatory Items:** {checked_mandatory}/{mandatory_items}")

        # --- Checklist Items ---
        for i, item in enumerate(session["items"]):
            clean_item = item.strip("* ").strip()
            is_mandatory = session["mandatory"][i]

            col1, col2 = st.columns([4, 1])
            with col1:
                checked = st.checkbox(
                    f"{'🔴' if is_mandatory else '⚪'} {clean_item}",
                    value=session["checked"][i],
                    key=f"check_{selected}_{i}"
                )
                if checked != session["checked"][i]:
                    session["checked"][i] = checked
                    save_json(ACTIVE_FILE, active)
                    st.rerun()  # Refresh to update progress instantly

                if is_mandatory and not checked:
                    st.warning("This is a mandatory item")

                comment = st.text_input(
                    "Comment (optional)",
                    value=session["comments"][i],
                    key=f"comm_{selected}_{i}"
                )
                if comment != session["comments"][i]:
                    session["comments"][i] = comment
                    save_json(ACTIVE_FILE, active)

            with col2:
                photo = st.file_uploader(
                    "Photo proof",
                    type=["jpg", "jpeg", "png"],
                    key=f"photo_{selected}_{i}"
                )
                if photo:
                    st.image(photo, width=100)
                    # Future: save photo permanently

        if st.button("Mark as Complete & Archive", type="primary"):
            # TODO: Move to archive file later
            del active[selected]
            save_json(ACTIVE_FILE, active)
            st.success("Checklist completed and archived!")
            st.rerun()