# AstroApps_ChecklistWizard
Part of the Astro App suite. Checklist Wizard allows users to input procedural checklists, manage them, and use them during operations.

# Setup
Requires Python 3.11 or newer.

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Add your Supabase credentials. Copy the example secrets file and replace the placeholders with your project URL and anon key (Supabase dashboard → Project Settings → API):

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   `.streamlit/secrets.toml` is gitignored. Do not commit it.

3. Run the app:

   ```bash
   streamlit run checklist_manager.py
   ```

# User's Guide
1. Enter your name in the side menu to log all checks
2. If creating a new checklist template, set mode to *Manage Templates*
3. If you are working on an active checklist, set mode to *View Active Checklists*
4. If you are creating a new instance of a checklist template, set mode to *Start New Checklist*
5. Within *Manage Checklists*, you can create a new checklist template. New items should be separated with new lines. You can also edit or delete existing templates.
6. Within *View Active Checklists*, you can select an active checklist, check off items, add comments or images, and close out the checklist.
7. Within *Start New Checklist*, you can create a new instance of a checklist by first selecting the template and then entering a new name. Once you hit *Start Checklist*, your checklist will automatically open in *View Active Checklists*, and you can begin working.
