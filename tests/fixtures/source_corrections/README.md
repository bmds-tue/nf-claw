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
