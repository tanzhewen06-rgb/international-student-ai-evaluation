# Response Agent

Generates independent model answers from the selected persona, student
background, and scenario prompts. Editable settings remain at the top of
main.py. Versioned prompt files stay in prompts/.

All generated answers and generation reports are stored in
../Sample Data/responses/<batch>/. The current selection is Final_Batch_Type_1:
five models, five scenarios, five generations per scenario (125 answers).
Existing nonempty model files are protected against accidental reruns.

From this folder, preview without API calls or output writes:

    python -B -c "import main; main.main(preview=True)"

Actual generation is a separate user action. See ../README.md for setup,
credentials, data locations, and how to configure a new batch.
