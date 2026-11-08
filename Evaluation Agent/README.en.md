# Evaluation Agent

Reads saved answers from ../Sample Data/responses/<batch>/ and writes judgments,
trials, supplements, and reports to ../Sample Data/evaluations/<batch>/.
Runtime code, versioned prompts, checklists, and calibration text remain here.
Frozen baseline metadata and scores are in ../Sample Data/reference_data/.

The current configuration uses V4.17 and Final_Batch_Type_1. Its completed
combined dataset contains 375 scored judgments, including five provisional
records. The selected missing-score recovery reports zero pending judgments
and makes no requests when the completed trial is opened again.

From this folder, preview without API calls or output writes:

    python -B main.py --preview

Settings remain at the top of main.py. For a new experiment, select its response
files and output batch and set MISSING_SCORE_TRIAL = None. Actual API runs are
initiated by the user.

Publication metadata uses project-relative paths and retains historical code
hashes. The IO adapter resolves references from this project's current location.
Frozen-trial continuation still checks original inputs
and code fingerprints; reorganized code does not silently bypass those checks.
Historical fixture-dependent tests and frozen GPT-stability checks require their
original environment. Local archive snapshots are excluded from this copy.

See ../README.md for setup and the completed supplemented dataset path.
