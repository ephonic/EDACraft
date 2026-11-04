# Frozen reported cases

Five distinct original RTL/TB/stimulus bundles from the user's cases directory. `inventory.json` records all eleven top-level archive names plus the carry follow-up, byte hashes, output widths and oracle provenance. Repeated bundles have identical simulation inputs and independent event-oracle hashes.

`expected-trace.txt` is generated from each archive's independent `events.json` oracle; its exact line inventory was checked against the archived VCS log. `expected-transport.txt` and `expected-all.txt` preserve VCS transport and total ordered observations. Fresh VCS runs on 103 revalidate both the archive and current simulator. The regression checks every bit, index, completion marker and transport record, including final/end. Original sources are unchanged; bound observers are retained.

`harness-rejected/` race-prone historical testbenches are excluded according to their existing invalid-harness classification. They are not simulator failures or numerical evidence.
