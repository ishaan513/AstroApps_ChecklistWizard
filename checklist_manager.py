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
        
        for i, item in enumerate(session["items"]):
            col1, col2 = st.columns([4,1])
            with col1:
                checked = st.checkbox(item.strip("* "), value=session["checked"][i], key=f"check_{selected}_{i}")
                if checked != session["checked"][i]:
                    session["checked"][i] = checked
                    save_json(ACTIVE_FILE, active)
                
                if session["mandatory"][i] and not checked:
                    st.warning("Mandatory item")
                    
                comment = st.text_input("Comment", value=session["comments"][i], key=f"comm_{selected}_{i}")
                if comment != session["comments"][i]:
                    session["comments"][i] = comment
                    save_json(ACTIVE_FILE, active)
                    
            with col2:
                photo = st.file_uploader("Photo", type=["jpg","png"], key=f"photo_{selected}_{i}")
                if photo:
                    # In real app, save to folder or cloud
                    st.image(photo, width=100)

        if st.button("Mark as Complete & Archive"):
            # Move to archive later
            st.success("Checklist completed!")