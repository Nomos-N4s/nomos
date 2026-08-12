# Changelog

All notable changes to the Nomos project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> CHANGELOG.md is now maintained by release-please. Do not hand-edit this
> file — entries are generated from conventional-commit history on release.

## [0.13.0](https://github.com/Nomos-N4s/nomos/compare/v0.12.0...v0.13.0) (2026-08-12)


### Features

* **azure:** add automated verification script and operational report for [#222](https://github.com/Nomos-N4s/nomos/issues/222) ([feee829](https://github.com/Nomos-N4s/nomos/commit/feee8296654d7c4fcf14366bf2d4606549930dc1))
* **azure:** add automated verification script and report generation for [#222](https://github.com/Nomos-N4s/nomos/issues/222) ([2e7aaeb](https://github.com/Nomos-N4s/nomos/commit/2e7aaeb7cc1b4629f0c231f65af16fa753c787a7))


### Bug Fixes

* **azure:** correct Pulumi output parsing and failure exit code in verify.py ([4ae7c4d](https://github.com/Nomos-N4s/nomos/commit/4ae7c4d8d4f665ab09e4074c339ab5905ebe1a90))


### Documentation

* add provision verify and destroy hard rule to AGENTS.md ([c6eb3ce](https://github.com/Nomos-N4s/nomos/commit/c6eb3ceb8f948df847b71eab068bd6dc76f07c85))

## [0.12.0](https://github.com/Nomos-N4s/nomos/compare/v0.11.1...v0.12.0) (2026-08-12)


### Features

* add Pulumi IaC program for Azure Container Apps deployment ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([995b8dc](https://github.com/Nomos-N4s/nomos/commit/995b8dcfc95657d891d164d44c5c297d35cd0f5c))


### Bug Fixes

* **docker:** use explicit /bin/uv path instead of python -m uv ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([7b95509](https://github.com/Nomos-N4s/nomos/commit/7b95509ec751c476e63e5bfd18e322fba85d4696))
* **docker:** use python -m uv and scope extras per stage ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([614d0e8](https://github.com/Nomos-N4s/nomos/commit/614d0e87b0d72275690f0682dc587caf5ae72158))
* install dashboard extra in Dockerfile so streamlit-autorefresh is present in deployed images ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([cf7cd5c](https://github.com/Nomos-N4s/nomos/commit/cf7cd5c7c7758c37bfcfa20f4e9e4c622fc4f11e))


### Documentation

* clarify uv invocation rule for Dockerfiles in AGENTS.md ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([bbd4580](https://github.com/Nomos-N4s/nomos/commit/bbd45807a6fec2d3ee5eb143344e3c28324336ba))
* document Azure Container Apps deployment and update mkdocs nav ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([7c9b9cc](https://github.com/Nomos-N4s/nomos/commit/7c9b9cc0b05defedc7bcccdaf563756c4696dedd))
* enforce PR template compliance in AGENTS.md HARD RULE ([#221](https://github.com/Nomos-N4s/nomos/issues/221)) ([0ad194a](https://github.com/Nomos-N4s/nomos/commit/0ad194a19782f79cfc7e4c63d65bb395247f3b44))

## [0.11.1](https://github.com/Nomos-N4s/nomos/compare/v0.11.0...v0.11.1) (2026-08-12)


### Documentation

* ADR 0001 modular monolith and atomic governance gate ([#220](https://github.com/Nomos-N4s/nomos/issues/220)) ([f28fc40](https://github.com/Nomos-N4s/nomos/commit/f28fc40ef3e22c69aa6c10287b3273f51552ba03))
* ADR 0001 restricts MemoryBackend to local mode; label dashboard writes as projections ([16bd21a](https://github.com/Nomos-N4s/nomos/commit/16bd21a877acf2f0a7f2868b2b24946e27d7d84b))

## [0.11.0](https://github.com/Nomos-N4s/nomos/compare/v0.10.1...v0.11.0) (2026-08-12)


### Features

* tamper-evident hash-chained audit log ([#164](https://github.com/Nomos-N4s/nomos/issues/164)) ([15cc7a9](https://github.com/Nomos-N4s/nomos/commit/15cc7a96eca0fd37f07e72daa11e98687ab9ea56))


### Bug Fixes

* anchor audit chain in sidecar Merkle root outside JSONL (CWE-345) ([62af683](https://github.com/Nomos-N4s/nomos/commit/62af683a00514b8eaedd40cfc950459835b31d0d))
* restore chain from disk on reopen and detect truncation (CodeRabbit) ([42265e2](https://github.com/Nomos-N4s/nomos/commit/42265e2fc7fb380951cbcb9e6aaa3b69331c68c5))

## [0.10.1](https://github.com/Nomos-N4s/nomos/compare/v0.10.0...v0.10.1) (2026-08-11)


### Documentation

* add CodeRabbit review badge to README ([87b7683](https://github.com/Nomos-N4s/nomos/commit/87b7683af607cf037e654b6de7636375fc00012b))
* update roadmap state (Tracks A and I done, GHCR gap resolved) ([0574155](https://github.com/Nomos-N4s/nomos/commit/0574155b9e836db402458dcee4d10373a408b9ea))

## [0.10.0](https://github.com/Nomos-N4s/nomos/compare/v0.9.0...v0.10.0) (2026-08-11)


### Features

* /healthz, /readyz, /metrics endpoints for runner serve ([#163](https://github.com/Nomos-N4s/nomos/issues/163)) ([23ad445](https://github.com/Nomos-N4s/nomos/commit/23ad445fc4e748964787254501b1de3bf39747a6))
* add .parliament example configs for the LLM scenarios ([e0fcbfc](https://github.com/Nomos-N4s/nomos/commit/e0fcbfc489a42835bec754bb025d044c71123752))
* add agent benchmark report generation ([aa92807](https://github.com/Nomos-N4s/nomos/commit/aa928073206be2a9c4a417987c943185f1741b27))
* add agent trace tab to the dashboard ([89eb1e8](https://github.com/Nomos-N4s/nomos/commit/89eb1e81a3832ef5df366a04564458e3c4906967))
* add agent validation metrics ([214ed55](https://github.com/Nomos-N4s/nomos/commit/214ed556d62574c11fd5f23533e23a16302bf205))
* add four LLM-native scenarios with prompt renderers ([7fe49ce](https://github.com/Nomos-N4s/nomos/commit/7fe49cea5ce58f1686d663b47eb9e30427bcf681))
* add governance trace writer and self-contained HTML viewer ([5ae5393](https://github.com/Nomos-N4s/nomos/commit/5ae539311c5b807ce664ceccd6ccd7883cd6b59b))
* add governed vs ungoverned comparison harness ([d7642a7](https://github.com/Nomos-N4s/nomos/commit/d7642a7b3d1512025049432c1472c588814291fb))
* add prediction_harness core module and tests ([74018b4](https://github.com/Nomos-N4s/nomos/commit/74018b487ddae45713a0ca2b6ec6dacf8a3c9552))
* add property-based tests for contracts, identity, and TEE ([#119](https://github.com/Nomos-N4s/nomos/issues/119)) ([0b7f62c](https://github.com/Nomos-N4s/nomos/commit/0b7f62cfa931701544dad2ba1c13443a463e4ad4))
* add python-dotenv and refactor .env handling for agent runs ([bd0c288](https://github.com/Nomos-N4s/nomos/commit/bd0c2885bd3971fa19a25c1c021f1373d021140f))
* agent run reproducibility (response cache, schema contract, pipeline, runner subcommand) ([e87d10e](https://github.com/Nomos-N4s/nomos/commit/e87d10ee622487dd09ff45f31df00572caae8cdf))
* auto-refresh toggle for live Colab-to-dashboard updates ([#75](https://github.com/Nomos-N4s/nomos/issues/75)) ([05f6791](https://github.com/Nomos-N4s/nomos/commit/05f6791881a61339b65233a4607cac872bbf9919))
* export agent metrics and report API from the agents package ([5cc8124](https://github.com/Nomos-N4s/nomos/commit/5cc81246b162638cf11a78832601a915c5d611c7))
* expose Speaker per-member scoring publicly ([904574a](https://github.com/Nomos-N4s/nomos/commit/904574ab98b99e682ef334f2f4829b4d356c471e))
* integrate prove-agent CLI subcommand ([62025a3](https://github.com/Nomos-N4s/nomos/commit/62025a36346671968f136f3f5cdc0394ced75331))
* **lean:** prove genesis 3-of-5 multisig bootstrapping (Ch4 §4) ([84809be](https://github.com/Nomos-N4s/nomos/commit/84809be9dbdb279e9d4f7d43cf442ceed7c315eb))
* **lean:** prove identity coherence threshold guard (Ch4 §6.1) ([2982ba0](https://github.com/Nomos-N4s/nomos/commit/2982ba031387053bd7de72d70d2386f842f601cb))
* **lean:** prove identity tier mutability rules (Ch4 §3) ([c087a2a](https://github.com/Nomos-N4s/nomos/commit/c087a2a4f5b717271b15708267917459b980f1de))
* **lean:** prove runtime integrity hash chain invariants (Ch4 §2.1/§6.1) ([86ff22a](https://github.com/Nomos-N4s/nomos/commit/86ff22a48faa13efaa9a4b82a4871e3444dbce7f))
* **lean:** prove sandboxed isolation buffer protocol (Ch4 §5.2) ([767c47b](https://github.com/Nomos-N4s/nomos/commit/767c47b322292f23853d9146ea185ee6b90c51b7))
* **lean:** register IdentityBuffer in GovBudgetProof manifest ([c1b4219](https://github.com/Nomos-N4s/nomos/commit/c1b42191bb749e5d9b5c121b9476a79e3947f1b8))
* **lean:** register IdentityCoherence in GovBudgetProof manifest ([f56efa4](https://github.com/Nomos-N4s/nomos/commit/f56efa44903a0ca327992e54d7cc28dd864f37bc))
* **lean:** register IdentityGenesis in GovBudgetProof manifest ([08a0acf](https://github.com/Nomos-N4s/nomos/commit/08a0acffb230266f7dd7dc7d52fbde8bedbb293c))
* **lean:** register IdentityHashes in GovBudgetProof manifest ([0947528](https://github.com/Nomos-N4s/nomos/commit/0947528984a9eb1f69b8601de07920402457b14c))
* **lean:** register IdentityTiers in GovBudgetProof manifest ([7e8792a](https://github.com/Nomos-N4s/nomos/commit/7e8792ab2fd7165aa28b9df03a9d886e0e711998))
* publish multi-arch OCI images to GHCR on version tags ([#217](https://github.com/Nomos-N4s/nomos/issues/217)) ([a04ef0d](https://github.com/Nomos-N4s/nomos/commit/a04ef0db50e4ce3d9af006657071a0f8528cb2f2))
* record committee scores, vetoers, and contracts in the harness ([0f774e0](https://github.com/Nomos-N4s/nomos/commit/0f774e069aac2676a364b30fee2f5016a8b8e869))
* record per-step agent latency in the comparison harness ([77ac41f](https://github.com/Nomos-N4s/nomos/commit/77ac41f609a4e2f29e4bf279bef46e93a2ebcd14))
* structured JSON logging foundation ([#161](https://github.com/Nomos-N4s/nomos/issues/161)) ([1c56550](https://github.com/Nomos-N4s/nomos/commit/1c56550ada7e795a19d688abe41d5ea796be5e3f))
* support state-dependent action metadata; log applied decisions ([f3bdef2](https://github.com/Nomos-N4s/nomos/commit/f3bdef2bbaa00095943f4f07098559bf4a3e6815))
* switch LLM runs to OpenRouter free models only ([699e2ae](https://github.com/Nomos-N4s/nomos/commit/699e2ae732865b05f43ee7a174d11b7eff3bb8ac))


### Bug Fixes

* apply ruff format to prediction_harness ([a046da8](https://github.com/Nomos-N4s/nomos/commit/a046da82213428fc9f4dd90fc31363731fa33de9))
* correct OPENROUTER_API_KEY key name in .env.example ([d044e1d](https://github.com/Nomos-N4s/nomos/commit/d044e1d970e11c942a7402306974f4a475409d23))
* coverage comment action needs uppercase inputs and relative file paths ([cba13df](https://github.com/Nomos-N4s/nomos/commit/cba13dfca1572866dfd13b48c3aa413578fd4630))
* dual-inherit from gymnasium.Env + gym.Env for SB3 Colab compat ([a619c7c](https://github.com/Nomos-N4s/nomos/commit/a619c7c5589d79ed08f5cf90a4d33d7fb3b891f8))
* exclude root project files from Mintlify processing ([#148](https://github.com/Nomos-N4s/nomos/issues/148)) ([2540762](https://github.com/Nomos-N4s/nomos/commit/2540762f76fc0dd01d32ff20cd7bb6cc175e28c7))
* GovernanceGridWorld inherits from gym.Env, fixes PPO training on Colab ([6dcbc00](https://github.com/Nomos-N4s/nomos/commit/6dcbc0030688814800c61c4ef1541071f94d65d1))
* **lean:** repair IdentityHashes module content ([8c43e01](https://github.com/Nomos-N4s/nomos/commit/8c43e01be7f5de3641d61e8e88e776ba5d7a3e18))
* parliament sentinel string resolved to SpeakerStateMachine in __init__ ([50c702d](https://github.com/Nomos-N4s/nomos/commit/50c702d62a81c38d05d36ec60898b7a5f4599614))
* rebrand paths in server docs, ruff-format readyz test (review [#182](https://github.com/Nomos-N4s/nomos/issues/182)) ([a4126a2](https://github.com/Nomos-N4s/nomos/commit/a4126a27da2029dcd5ffc46d0eb4f524a02f6121))
* remove docs/ symlinks and MkDocs CI (prep for 3-repo split) ([0123a95](https://github.com/Nomos-N4s/nomos/commit/0123a958d42d220f94c8bd4e5871fd818bcadf59))
* remove duplicate changelog heading (review [#181](https://github.com/Nomos-N4s/nomos/issues/181)) ([8f2aec1](https://github.com/Nomos-N4s/nomos/commit/8f2aec1c67572955886a5b17a5e5ac6fbabcc977))
* resolve ruff lint issues (unused imports, lambda, json import) ([b5ff2e9](https://github.com/Nomos-N4s/nomos/commit/b5ff2e9152d00ec15c98b93a1179c35a263c8f90))
* resolve ruff lint issues across test files ([348a7c3](https://github.com/Nomos-N4s/nomos/commit/348a7c3c60047734bfce218385cf668c8530f070))
* ruff format line length in prediction_harness ([e9f5129](https://github.com/Nomos-N4s/nomos/commit/e9f51295dbb981fbc636fb2f87302cd4df7cff86))
* sweep leftover src/governance refs missed by brand slice 2 ([a36b99b](https://github.com/Nomos-N4s/nomos/commit/a36b99bb7f6521c585cef5790cf49adb60db10ae))
* sweep leftover src/governance refs missed by brand slice 2 [[#86](https://github.com/Nomos-N4s/nomos/issues/86)] ([89eab9f](https://github.com/Nomos-N4s/nomos/commit/89eab9f8638dce4ae8f0818b9f98c9b85049235e))
* tidy trace display data (rounded scores, no dead column) ([3a3ee1d](https://github.com/Nomos-N4s/nomos/commit/3a3ee1d6e1cfe54ad9a1632b0239923df1563796))
* use default coverage path for comment action (directory scan) ([c2d6810](https://github.com/Nomos-N4s/nomos/commit/c2d6810474c9304486569af892e3ec274072944b))


### Documentation

* add CHANGELOG entry for [#163](https://github.com/Nomos-N4s/nomos/issues/163) health endpoints ([a0b7b2b](https://github.com/Nomos-N4s/nomos/commit/a0b7b2b507bb464c044386919be6682f2d2ed472))
* add CHANGELOG entry for [#75](https://github.com/Nomos-N4s/nomos/issues/75) auto-refresh ([316dc75](https://github.com/Nomos-N4s/nomos/commit/316dc75cb4738d6498524fe0919c5fe6ce3a77e1))
* add feature-144 documentation with mermaid diagrams ([c1f07e3](https://github.com/Nomos-N4s/nomos/commit/c1f07e37485018e94946c2f7bf971577403b361e))
* add ordered execution roadmap (board-backed) ([c4b2f09](https://github.com/Nomos-N4s/nomos/commit/c4b2f0914b79809ea8462f4f3f8c336b51d2d0d3))
* add release badge to README ([784bb8a](https://github.com/Nomos-N4s/nomos/commit/784bb8add5b7be7cd85c8d1a3679cd84a8c44cd0))
* add SEO title and description frontmatter to nav pages ([#95](https://github.com/Nomos-N4s/nomos/issues/95)) ([aff3dfc](https://github.com/Nomos-N4s/nomos/commit/aff3dfcf4fe5a18e62f7132578472f72eb57854b))
* add social preview image for repo card and link shares ([85170bd](https://github.com/Nomos-N4s/nomos/commit/85170bd0622d531e215e5779dfa8390d18e22f17))
* agent benchmark protocol in reproducibility doc ([f96921b](https://github.com/Nomos-N4s/nomos/commit/f96921bfd2fad8a471c68a01ca18794a4efea1d6))
* align license references (README, CLA, docs index) with Apache-2.0 ([c8e4189](https://github.com/Nomos-N4s/nomos/commit/c8e4189f14c92f57501cfed9f326befec7b325ac))
* brand pass governance layer -&gt; Nomos (brand slice 2) ([9479f23](https://github.com/Nomos-N4s/nomos/commit/9479f234ec5007bc36972ce9da9c9185506d180d))
* cut changelog entry for v0.8.0 launch release ([e319581](https://github.com/Nomos-N4s/nomos/commit/e31958196f573474995dca2d159a53ed427eef6a))
* document strengthened statistical methods in benchmarks and Appendix D ([#112](https://github.com/Nomos-N4s/nomos/issues/112)) ([b12cff4](https://github.com/Nomos-N4s/nomos/commit/b12cff4663bc153e50e1800feaedc5e5cf373892))
* fix capitalization typo in chapter-03 ([#113](https://github.com/Nomos-N4s/nomos/issues/113)) ([a04e1d3](https://github.com/Nomos-N4s/nomos/commit/a04e1d35edbab89f6cdb088e99a3df8df525d498))
* fix stray whitespace and duplicate horizontal rule ([#121](https://github.com/Nomos-N4s/nomos/issues/121)) ([4f3752d](https://github.com/Nomos-N4s/nomos/commit/4f3752dab96215e2c54f827a0600f3940156edb3))
* fix typo "vetos" → "vetoes" in TEE isolation appendix ([#98](https://github.com/Nomos-N4s/nomos/issues/98)) ([d95ca73](https://github.com/Nomos-N4s/nomos/commit/d95ca7372b55d1b438e59f55d71dd6d0c96d79db))
* fix typos, grammar, and broken markdown formatting ([#96](https://github.com/Nomos-N4s/nomos/issues/96)) ([78bbef2](https://github.com/Nomos-N4s/nomos/commit/78bbef2d76d9a6ce3bc39ba5a3a47b3fb66faf7d))
* move osf-registration.md to nomos-website repo ([86237ed](https://github.com/Nomos-N4s/nomos/commit/86237ed0eada391740019831ed3a37d91ecbfa43))
* record uv and atomic-commit conventions in AGENTS.md ([b8bdf5d](https://github.com/Nomos-N4s/nomos/commit/b8bdf5d1a64b1a635e90b157c1cd5f7427d5b061))
* rename remaining Governance Layer references (requirements headers) ([6c6b767](https://github.com/Nomos-N4s/nomos/commit/6c6b767600d078492d0ff07f964698d206c010f4))
* rename repo surface to Nomos (single rebrand PR) ([57310ca](https://github.com/Nomos-N4s/nomos/commit/57310ca44c933c3c629ea7813e84d47761e89bfb))
* restore GitHub Pages mkdocs pipeline, add Lean verification page ([a3ccc4b](https://github.com/Nomos-N4s/nomos/commit/a3ccc4b560b3843c9d1c713377d941d9e624d5c0))
* roadmap decision record - release/delivery, Azure-first deployment, native gates ([d273a3b](https://github.com/Nomos-N4s/nomos/commit/d273a3b752c80f4177d300fe550de1fb974d6271))
* stage book/changelog/references/src into docs tree for mkdocs build ([51662b6](https://github.com/Nomos-N4s/nomos/commit/51662b632e58466ffad550ce2cf63c903bb21abe))
* sync AGENTS.md active state and roadmap to board ([a701596](https://github.com/Nomos-N4s/nomos/commit/a7015963fce72a09496dd0e1712ddd5d879e4869))
* update AGENTS.md with AI Agent Validation epic ([#145](https://github.com/Nomos-N4s/nomos/issues/145)) ([#146](https://github.com/Nomos-N4s/nomos/issues/146)) ([4e5d230](https://github.com/Nomos-N4s/nomos/commit/4e5d2300ed455f1196074483e87599f5792bb5ab))
* update AGENTS.md with Phase C epic and 3-repo roadmap ([db1bc54](https://github.com/Nomos-N4s/nomos/commit/db1bc545f0b6817f7534a0fd0e9a9f27eff89c8b))
* update CHANGELOG for feature [#144](https://github.com/Nomos-N4s/nomos/issues/144) ([e6274e3](https://github.com/Nomos-N4s/nomos/commit/e6274e399e44c9f3efb9d3daaa542b15ea58645b))

## [0.9.0](https://github.com/Nomos-N4s/nomos/compare/v0.8.0...v0.9.0) (2026-08-11)


### Features

* /healthz, /readyz, /metrics endpoints for runner serve ([#163](https://github.com/Nomos-N4s/nomos/issues/163)) ([23ad445](https://github.com/Nomos-N4s/nomos/commit/23ad445fc4e748964787254501b1de3bf39747a6))
* auto-refresh toggle for live Colab-to-dashboard updates ([#75](https://github.com/Nomos-N4s/nomos/issues/75)) ([05f6791](https://github.com/Nomos-N4s/nomos/commit/05f6791881a61339b65233a4607cac872bbf9919))
* publish multi-arch OCI images to GHCR on version tags ([#217](https://github.com/Nomos-N4s/nomos/issues/217)) ([a04ef0d](https://github.com/Nomos-N4s/nomos/commit/a04ef0db50e4ce3d9af006657071a0f8528cb2f2))
* structured JSON logging foundation ([#161](https://github.com/Nomos-N4s/nomos/issues/161)) ([1c56550](https://github.com/Nomos-N4s/nomos/commit/1c56550ada7e795a19d688abe41d5ea796be5e3f))


### Bug Fixes

* rebrand paths in server docs, ruff-format readyz test (review [#182](https://github.com/Nomos-N4s/nomos/issues/182)) ([a4126a2](https://github.com/Nomos-N4s/nomos/commit/a4126a27da2029dcd5ffc46d0eb4f524a02f6121))
* remove duplicate changelog heading (review [#181](https://github.com/Nomos-N4s/nomos/issues/181)) ([8f2aec1](https://github.com/Nomos-N4s/nomos/commit/8f2aec1c67572955886a5b17a5e5ac6fbabcc977))


### Documentation

* add CHANGELOG entry for [#163](https://github.com/Nomos-N4s/nomos/issues/163) health endpoints ([a0b7b2b](https://github.com/Nomos-N4s/nomos/commit/a0b7b2b507bb464c044386919be6682f2d2ed472))
* add CHANGELOG entry for [#75](https://github.com/Nomos-N4s/nomos/issues/75) auto-refresh ([316dc75](https://github.com/Nomos-N4s/nomos/commit/316dc75cb4738d6498524fe0919c5fe6ce3a77e1))
* add release badge to README ([784bb8a](https://github.com/Nomos-N4s/nomos/commit/784bb8add5b7be7cd85c8d1a3679cd84a8c44cd0))
* add social preview image for repo card and link shares ([85170bd](https://github.com/Nomos-N4s/nomos/commit/85170bd0622d531e215e5779dfa8390d18e22f17))
* record uv and atomic-commit conventions in AGENTS.md ([b8bdf5d](https://github.com/Nomos-N4s/nomos/commit/b8bdf5d1a64b1a635e90b157c1cd5f7427d5b061))
* roadmap decision record - release/delivery, Azure-first deployment, native gates ([d273a3b](https://github.com/Nomos-N4s/nomos/commit/d273a3b752c80f4177d300fe550de1fb974d6271))

## [0.8.0] — 2026-08-11

### Added
- License moved to Apache-2.0 (was CC BY 4.0); LICENSE, README, CLA, and docs references aligned
- Docker build fixed: tests/ and examples/ now copied into the image, base stage is the default build target, .dockerignore added
- MkDocs Material documentation build system (`mkdocs.yml`, `docs/`)
- GitHub Actions workflow to build and deploy docs to GitHub Pages
- GitHub Project #3 for issue tracking with 4 epics (A–D)
- End-to-end pipeline integration test (mini benchmark → analysis → figures → export) (#103)
- Hypothesis property-based tests for contracts (mask merger, enforcement, timelock), Identity Layer (tier rules, multisig thresholds, ontology hashes), and TEE (watchdog, Merkle trees, constant-time ops) (#104)
- Benchmark smoke test job in CI (`benchmark-smoke` in `.github/workflows/tests.yml`) (#105)
- Formal prediction cross-validation harness (#144): 12-prediction confirmation table, adversarial edge-case catalog, sensitivity analysis, and `prove-agent` CLI subcommand
- Auto-refresh toggle for the RL Training tab: polls `results/rl/` every 30s, shows a last-updated timestamp and a "Live from Colab" indicator when new results land (#75)
- `/healthz`, `/readyz`, `/metrics` endpoints for `runner serve`: liveness, readiness (Speaker, TEE watchdog, deadlock breaker, backend), and Prometheus metrics via the optional `observability` extra (#163)

### Changed
- Aligned all four benchmark figures with analysis pipeline: reward curves use bootstrap CIs instead of parametric error; violation rate and deadlock frequency bar charts use bootstrap CI error bars instead of stdev; Pareto frontier overlay added; color palette unified across all figure types (#101)
- **Rebrand live (#86).** Package renamed `governance` → `nomos` in #205; this PR ports the docs/brand state to the published surface: `mkdocs.yml` now presents the site as **Nomos** with `site_url`/`repo_url` pointing at `xcoder-es/nomos` (repo renamed from `xcoder-es/governance-layer`, old URLs redirect). README headline, badges, and citation updated; API reference, book responses, and changelog index swept of stale `governance-layer` references; page-visible module docstrings (runner, prove, ontology) updated.

## [0.7.0] — 2026-07-26

### Added
- RL Training Results dashboard tab (Tab 4) with governed vs ungoverned comparison
- Neo4j `rl_run` entity logging for MLflow-like experiment tracking
- Lean 4 formal proofs for budget enforcement (κ₂) and vote threshold invariants

### Fixed
- Baseline decoupling bug in benchmarks (all prior results invalidated; re-ran)

## [0.6.0] — 2026-07-20

### Added
- Property-based test suite for Speaker state machine (Hypothesis, ~1000 cases)
- TEE module tests for enclave, batch verification, watchdog, constant_time
- Fuzzing tests for edge cases and extreme inputs
- PPO training script for GovernanceGridWorld (`scripts/train_governance_grid_world.py`)
- RL comparison plots script (`scripts/rl_comparison_plots.py`)
- Minigrid environment wrapping with Neural Parliament governance
- Safety-constrained environments (Safety-Gymnasium-based)
- Colab GPU training notebook with Minigrid + Safety-Gymnasium

### Fixed
- MRO crash on Colab for GovernanceGridWorld (gym/gymnasium dual-inheritance)
- Robust Safety-Gymnasium install in Colab notebook

## [0.5.0] — 2026-07-15

### Added
- Comprehensive Mermaid architecture diagrams in book chapters
- Neo4j integration: `Neo4jBackend` in ontology package wired to Streamlit dashboard
- Decision logging records each replayed step as ontology entities
- Multi-enclave consensus addendum in Appendix A

## [0.4.0] — 2026-07-10

### Added
- Full modular reference implementation (~2100 lines):
  - Core types (`models.py`), 7 Parliament members, Identity Layer (383 lines)
  - Ulysses Contracts lifecycle, 3 enforcement modes, mask merger
  - TEE simulation (enclave, Merkle batch, watchdog, constant-time, deadlock breaker)
  - Speaker state machine with budgets, agenda sorting, scoring, vetoes, weighted voting
- Benchmark suite (4 scenarios × 5 strategies × 20 seeds):
  - `baselines.py`, `run_all.py`, `report.py`, `analysis.py`, `figures.py`
- CLI entry point (`runner.py` with `--baselines`, `--strategies`, `--steps`, `--seeds`, `--csv`)
- Streamlit dashboard (3-tab: Formal Model, Parliament Live, Benchmarks)
- Colab notebook (`notebooks/01-prove-tutorial.ipynb`)
- `prove.py`: 12 formal predictions from Chapters 2–4, all PASS

## [0.3.0] — 2026-07-01

### Added
- Appendix B: DSL Grammar for Parliament Configuration
- Appendix C: Data Types Reference
- Appendix D: Experiment Protocol & Reproducibility Checklist
- Appendix E: RL Adversary Results & Attack Patterns
- CSV export and steps/seeds validation in CLI
- PyTest test suite (unit + integration)

### Changed
- Rewrote README with hero section, quick-start, researcher/dev guide

## [0.2.0] — 2026-06-20

### Added
- Phase 1 benchmark suite: CLI, scaling, analysis, figures
- Gym environment (`GovernanceGridWorld`) with PPO training harness
- RL adversary CLI for testing governance robustness
- Ontology backends: abstract + in-memory + Neo4j
- Dashboard auto-detection of Neo4j from `.env`
- Final review panel response (Phase 5.2) with three fixes

### Changed
- Speaker state machine initialization to resolve sentinel-string bug

## [0.1.0] — 2026-06-10

### Added
- Theoretical framework: Chapters 1–4 and Appendix A
- Responses to first review panel (5 rounds, all fixes accepted)
- Reference implementation: Speaker state machine (deterministic falsification counter)
- Project setup: `pyproject.toml` (uv), `.env.example`, `results/` directory

## [0.0.1] — 2026-06-01

### Added
- Initial repository setup with README
- Chapter 1: problem statement and motivation
- Living bibliography system with 19 seed entries
