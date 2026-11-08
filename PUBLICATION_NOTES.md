# Publication copy

This is a separate sanitized copy. Keep Response Agent, Evaluation Agent and
Sample Data as sibling folders. No original computer directory is needed.

Local absolute paths in metadata and reports use project-relative references
beginning with project://. Metadata values and dictionary keys are resolved
against this project's own location when loaded. Newly saved evaluation JSON
also uses these references. External local-file paths are redacted.

Local archives, virtual environments, editor settings, caches, stale locks,
machine-specific migration receipts and backup locations are omitted.

Answer IDs, model answers, prompts, dimension scores, provisional flags,
timestamps and historical scoring-code fingerprints are retained. Metadata
files containing paths have new file hashes; links between distributed metadata
files refer to their sanitized copies. PUBLICATION_INVENTORY.json records
original and publication hashes using relative filenames.

The local original research records are unchanged. This copy does not claim
to recreate the exact frozen execution environment. Historical fingerprints
remain historical: continuation checks do not silently treat current code as
the code originally used. Completed final data can be read without model calls.

## Windows Git long paths

Historical trial folders contain deeply nested paths. Git for Windows needs
long-path support to add or check out these files. For an existing local
repository, run this once from its root:

    git config --local core.longpaths true

Before cloning through GitHub Desktop on Windows, enable support for your user:

    git config --global core.longpaths true

The repository's .gitattributes preserves file bytes during commit and checkout,
so stored metadata hash links are not changed by automatic newline conversion.
