# Resume and publication attribution

An output directory certifies one analysis configuration. Before `--resume`,
nf-claw compares effective parameters, selected profiles, configuration content,
pipeline revision and source content, engine/environment, resource limits and
the runtime configuration recipes. It also checks the existing local input
namespace and SHA-256 records and prior dependency stability.

When these records agree, ordinary Nextflow caching is retained. Automatically
generated report suffixes keep their earlier value so unchanged runs do not
create another set of reports. An explicit replacement suffix is a configuration
change.

If an analysis configuration differs, or its previous identity is unavailable,
the entire existing run is preserved in a sibling `<outdir>.previous-<unique-id>`
archive. That includes earlier publications, parameter settings, source bundle,
logs and user-added files. The current directory starts fresh, with a fresh
Nextflow cache session. Nothing is silently deleted. Changes that disable an
output branch therefore cannot leave its previous results in the current output
manifest. The archive operation retains the existing active-session checks,
write lock, input/configuration separation and failure rollback.

`--check --resume` reports this decision and prints the fresh command without
moving or writing the existing output directory. The lightweight versioned
`provenance/analysis.json` record is written even with `--no-provenance` and uses
component hashes so environment credentials are not exposed. Existing historical
runs without an analysis identity conservatively start fresh.

This guard covers supported local configuration and declared dependencies. It
does not identify arbitrary task-internal downloads or unresolved dynamic remote
configuration. The provenance and dependency policies document those limits;
unchanged local configuration is not proof that a mutable remote resource stayed
unchanged. Keep work files that published symlinks and cached tasks depend on.
