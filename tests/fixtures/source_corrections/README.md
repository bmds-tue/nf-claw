# Exact upstream source fixtures

These small, unmodified files exercise source-bound working-copy corrections. Their upstream
MIT licenses are retained alongside them. Tests must preserve their original byte representation.

- `createtaxdb-sourmash-create.nf`: nf-core/createtaxdb 3.1.0 commit
  `b01a0f8ed96a5990d15470828dfa92a22cf08bba`,
  `subworkflows/local/sourmash_create/main.nf`, SHA-256
  `d4bba56bd872f0d99dbe96998f781338458cdca6b02cf2ed61fbef6e1c168cc5`.
- `funcscan-amp.nf`: nf-core/funcscan 4.0.0 commit
  `aee3dc965eb0c77267435544dda30da858763913`, `subworkflows/local/amp.nf`, SHA-256
  `da0910b19617ffe05551968930acf181ede17e8af21b4b52d0548d66342738cf`.

Source: [Createtaxdb](https://github.com/nf-core/createtaxdb/blob/b01a0f8ed96a5990d15470828dfa92a22cf08bba/subworkflows/local/sourmash_create/main.nf)
and [Funcscan](https://github.com/nf-core/funcscan/blob/aee3dc965eb0c77267435544dda30da858763913/subworkflows/local/amp.nf).

Bactmap 1.0.0 commit `834642d8ac150ca10d705833223e7bcf15efc210` fixtures:

| Fixture | Upstream path | SHA-256 |
| --- | --- | --- |
| `bactmap-test.config` | `conf/test.config` | `665ad967b8dc704a59fd75d617cc449b2f0ed85748b379ac6c8ff982dde97604` |
| `bactmap-NfcoreTemplate.groovy` | `lib/NfcoreTemplate.groovy` | `dc8ee97c5830c319e02ee3f2efd0df36e23e2ee7c4db3d37fbadd5c0fa3a44a2` |
| `bactmap-modules.config` | `conf/modules.config` | `c8e6bbab1e3a2215541458757805b85251bb252435d68507acfd9643439aa142` |
| `bactmap-check_samplesheet.py.txt` | `bin/check_samplesheet.py` | `2e6b4b3e32dd0935fd4d5b4f42c359ed306f71a6be9b5676f26fdde14f228b54` |
| `bactmap-alignpseudogenomes.nf` | `modules/local/alignpseudogenomes.nf` | `691df6917c716891a027ce8bbe13136a158de62d056edd72af3736bf4db3628e` |
| `bactmap-LICENSE` | `LICENSE` | `875fe056225497d4ef97899b1aaeb3900ea3b40536cd2a3ff9bb49b7a0c210f0` |

Source: [Bactmap tree](https://github.com/nf-core/bactmap/tree/834642d8ac150ca10d705833223e7bcf15efc210).
