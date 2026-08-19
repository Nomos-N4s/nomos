# Changelog

All notable changes to the Nomos project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> CHANGELOG.md is now maintained by release-please. Do not hand-edit this
> file — entries are generated from conventional-commit history on release.

## [1.2.1](https://github.com/Nomos-N4s/nomos/compare/v1.2.0...v1.2.1) (2026-08-19)


### Documentation

* **book:** drop a check count that had already gone stale ([c40a01b](https://github.com/Nomos-N4s/nomos/commit/c40a01b498e9c3a9f7bc0d1a09312e2b32866e42))
* cite a tracked file as the no-dependency evidence ([418b34a](https://github.com/Nomos-N4s/nomos/commit/418b34a0f87fe79b3445e07ac7a69bbb5b6ba71b))
* say what the Lean corpus proves, and what it does not reach ([cd864ff](https://github.com/Nomos-N4s/nomos/commit/cd864ff7418dd07ae3896375a9cda8e93eeb1dd6))

## [1.2.0](https://github.com/Nomos-N4s/nomos/compare/v1.1.0...v1.2.0) (2026-08-19)


### Features

* **lean:** count monitors and key holders in the isolation buffer ([7b2407c](https://github.com/Nomos-N4s/nomos/commit/7b2407ca72c234102e6590986718d5e33a5845e4))
* **lean:** prove what the falsification counter actually counts ([bdb5170](https://github.com/Nomos-N4s/nomos/commit/bdb51709d78feee7326477ab18f659da9d86db57))
* **lean:** state the genesis bar with the genesis constant ([f530734](https://github.com/Nomos-N4s/nomos/commit/f530734e757da521861fc1568fe617f6bf50ecbb))


### Bug Fixes

* **lean:** anchor TEE binding verification to the genesis commitment ([c78661d](https://github.com/Nomos-N4s/nomos/commit/c78661d24d69ecbc485d71db2424d06c98995373))
* **lean:** prove tee_accepts_three off its Prop sibling ([366461f](https://github.com/Nomos-N4s/nomos/commit/366461f574e22b57874f229cda70e0b94ec0d6e0))
* **lean:** prove tee_rejects_duplicate_alone off its Prop sibling ([c07a50f](https://github.com/Nomos-N4s/nomos/commit/c07a50f7f5fb0757d1e6c69ca7cdb5ebf774c99d))
* **lean:** prove tee_rejects_two off its Prop sibling ([54d9ba9](https://github.com/Nomos-N4s/nomos/commit/54d9ba9c585845fac4f5ae5ea1fedac46612657f))
* **lean:** prove the genesis TEE theorems without native_decide axioms ([42fa39d](https://github.com/Nomos-N4s/nomos/commit/42fa39d1d0a5fad67cff9bfcde9d6349b7305488))
* **lean:** replace the domain-free theorems with statements that constrain the model ([7206a5b](https://github.com/Nomos-N4s/nomos/commit/7206a5b2cd3fddba5b2e44e43a15f4a0e5e7c303))
* **test:** scan Lean source instead of regexing out its comments ([b2b0643](https://github.com/Nomos-N4s/nomos/commit/b2b0643c0c13910589521cae30a1667b4f4d5a21))


### Documentation

* **book:** correct the proof-module count after Basic.lean removal ([0f10432](https://github.com/Nomos-N4s/nomos/commit/0f10432b4a1390c6d88f9dfb187c9a4bca1f5c2d))
* **book:** record that Basic.lean was deleted, not documented ([810411b](https://github.com/Nomos-N4s/nomos/commit/810411b80a593f9b6058a908720633d3e9ee7ab4))
* **book:** scope the TEE inventory row to what the signature carries ([1b1109f](https://github.com/Nomos-N4s/nomos/commit/1b1109fdd979d4132e14eba6c8d63dd64913c67d))
* correct the Lean module inventories after issue [#298](https://github.com/Nomos-N4s/nomos/issues/298) ([8b25df6](https://github.com/Nomos-N4s/nomos/commit/8b25df6e809266c237250407308777778341dd48))
* **lean:** name the checks that enforce the genesis axiom discipline ([bec5d0a](https://github.com/Nomos-N4s/nomos/commit/bec5d0adbab9cd6f609e2ac14bcd92deda3d2a6b))
* **lean:** name the genesis-hash provenance as an assumption ([9f5e8f2](https://github.com/Nomos-N4s/nomos/commit/9f5e8f2a247ceb8a60beedefad90e371366997b3))
* **lean:** name the real source of quorumCount_bounded_by_five's propext ([084a94c](https://github.com/Nomos-N4s/nomos/commit/084a94c4eebe67d3cd560f770a243416b52d6b71))
* **lean:** name the three limits of the new buffer model ([bb55fb7](https://github.com/Nomos-N4s/nomos/commit/bb55fb70428328e343e84c6cfcb23c7fa2294ef1))
* **lean:** record the genesis file's axiom discipline in its header ([754d66d](https://github.com/Nomos-N4s/nomos/commit/754d66d406b8a9e5b7dfa949af82b6ba970ee2c3))
* **lean:** say the buffer gates count identities, not signatures ([3aa6c8e](https://github.com/Nomos-N4s/nomos/commit/3aa6c8e819aeb669d2a02f2205f76c50501041d4))
* **lean:** say which manifest each TEE theorem is about ([115b903](https://github.com/Nomos-N4s/nomos/commit/115b903d888994cde3405876be071613470a671c))
* **lean:** scope the buffer's base-ontology claim to extendFromBuffer ([e68aeaf](https://github.com/Nomos-N4s/nomos/commit/e68aeaf594b6bdeaaf632feff3e3b12644ed6e45))
* **test:** attribute the example-block native_decide uses to [#299](https://github.com/Nomos-N4s/nomos/issues/299) ([340b051](https://github.com/Nomos-N4s/nomos/commit/340b051a1b1e25f23a7a2d4d4313fde61afb14d8))
* **test:** say why both native-decision guards are needed ([d245ab5](https://github.com/Nomos-N4s/nomos/commit/d245ab5d342becb474a656e0596b18159f20f4d5))

## [1.1.0](https://github.com/Nomos-N4s/nomos/compare/v1.0.0...v1.1.0) (2026-08-19)


### Features

* **lean:** add the MIX multiplier and the per-binding digest ([4792837](https://github.com/Nomos-N4s/nomos/commit/4792837e97026ff847a2a5ad86688c4a00e8b633))
* **lean:** decide the tier permission gate in the falsification module ([97e9f6e](https://github.com/Nomos-N4s/nomos/commit/97e9f6e9be573e16900af1c3e230fce81340c77f))
* **lean:** exhibit an invalid chain sharing a root under every hash ([1d09e58](https://github.com/Nomos-N4s/nomos/commit/1d09e58358f1a9181d8b2642371d3f1f429c7b47))
* **lean:** gate falsification parameter edits on the tier model ([82123b9](https://github.com/Nomos-N4s/nomos/commit/82123b97673052488aa739f4a252a15ee1c647b6))
* **lean:** model the falsification parameters as a governed block ([2441b3d](https://github.com/Nomos-N4s/nomos/commit/2441b3d3483b7ed9ceea274b25731ed414d98cd4))
* **lean:** pin where the digest packing is still injective ([690546f](https://github.com/Nomos-N4s/nomos/commit/690546fa30e1ce5675d0114db37df2d83f93f0da))
* **lean:** prove chainRoot order sensitivity ([7b5292a](https://github.com/Nomos-N4s/nomos/commit/7b5292abf12499e5be2f31f301fca12b529b65bc))
* **lean:** prove falsification params unchanged at the immutable tier ([b0b52d9](https://github.com/Nomos-N4s/nomos/commit/b0b52d9208ff1cfbcd4b5a7cdea40bab7fa5245f))
* **lean:** prove the binding digest collides for distinct records ([fd842dd](https://github.com/Nomos-N4s/nomos/commit/fd842dd378aa54b8d213a61b7e0e1e70e5c176ab))
* **lean:** prove the binding digest separates each record field ([5eed2db](https://github.com/Nomos-N4s/nomos/commit/5eed2db57f73b6a1eff78cc0fe2080753865c474))
* **lean:** read the falsification bar off a parameter block ([1296d4a](https://github.com/Nomos-N4s/nomos/commit/1296d4a6d176d59aadb904fa5a31d715a4b45709))
* **lean:** refute the general invalid-chain root claim ([ca946f7](https://github.com/Nomos-N4s/nomos/commit/ca946f7d0b0f4ed0b4f6924fb5b976be31322bef))
* **lean:** relate IsValidChain to chainRoot via link forgery ([940dd42](https://github.com/Nomos-N4s/nomos/commit/940dd42aba32749c173269798639012ee76a5973))
* **lean:** show the root cannot separate two self-consistent bindings ([b61ad9c](https://github.com/Nomos-N4s/nomos/commit/b61ad9cb4e22e7297ae60d319293e4fff376b365))
* **lean:** tie the invariance to the declared parameter tier ([e759c9d](https://github.com/Nomos-N4s/nomos/commit/e759c9de4c9a4565afafe944659c3dde6014921e))


### Bug Fixes

* **lean:** commit bindingHash 13 for the tampered_impl example ([f37781f](https://github.com/Nomos-N4s/nomos/commit/f37781f4e98bd69d7af6a6fbc83d0bca56b3b3e7))
* **lean:** make the identity hash chain a real commitment ([e267152](https://github.com/Nomos-N4s/nomos/commit/e267152abf96215326f67224ee2103cee6ecf997))
* **lean:** prove falsification-parameter invariance against the tier model ([3c498f4](https://github.com/Nomos-N4s/nomos/commit/3c498f40e06e0de7231c463a7ede1b4f23ff6443))
* **lean:** replace the vacuous collision-free swap theorem ([6fab310](https://github.com/Nomos-N4s/nomos/commit/6fab31014c8f8ad3c8c6cda342d3d62fc5217ce9))
* **lean:** require BindingValid of a chain's terminal binding ([1751dd2](https://github.com/Nomos-N4s/nomos/commit/1751dd26ca2f3dcbf493e537786fc615acd39809))


### Documentation

* **book:** correct the IdentityHashes row in the Lean inventory ([daed677](https://github.com/Nomos-N4s/nomos/commit/daed67710d91eca794228f1a66032767578e954f))
* **book:** describe what VoteAndFalsification actually proves ([018a43e](https://github.com/Nomos-N4s/nomos/commit/018a43eb586a7a409ab25c2a1d82360646d482ef))
* **book:** qualify the IdentityHashes row in the Lean inventory ([ff9e218](https://github.com/Nomos-N4s/nomos/commit/ff9e21887793b6e717a865ac32a78483b8124e25))
* **lean:** drop the false necessity claim on the immutable-tier gate ([78223be](https://github.com/Nomos-N4s/nomos/commit/78223bef8ce855496738cb6ea4c6626e153a4134))
* **lean:** drop the unproved ordering between the two hypotheses ([4254bdc](https://github.com/Nomos-N4s/nomos/commit/4254bdc42b29773c1bfccda812926c7870c2e901))
* **lean:** qualify what the digest and the root actually separate ([504504c](https://github.com/Nomos-N4s/nomos/commit/504504ccd1cb5c0bc3c54b5e41ba2b26c684dfb0))
* **lean:** restate the IdentityHashes header assumptions ([c88ab59](https://github.com/Nomos-N4s/nomos/commit/c88ab598c9e8ca7941eba84b0c5505108bbb289f))
* **lean:** say the falsification params are declared immutable-tier ([ed5cc88](https://github.com/Nomos-N4s/nomos/commit/ed5cc88359c340c92d98556874954340f864d9cf))
* **lean:** say the tamper literals are illustrative, not pinned ([31d1cb0](https://github.com/Nomos-N4s/nomos/commit/31d1cb0ca28dc3dcdd03e76426df43f72beb3098))
* **lean:** scope the uninterpreted-hash claim to the RuntimeHash section ([f6a3d0b](https://github.com/Nomos-N4s/nomos/commit/f6a3d0bd51b8e0edd6a1bc1c5082d3ccb1bc0268))
* **lean:** sharpen the two caveats added with the collision lemmas ([6afddbc](https://github.com/Nomos-N4s/nomos/commit/6afddbc5566492a06a6f35082be2cdc72eaffd52))
* **lean:** stop blaming hash degeneracy for the root collisions ([ac417cb](https://github.com/Nomos-N4s/nomos/commit/ac417cbbfc5682e13ad924b22cfec13bd06e1b94))
* **readme:** headline the tier-derived falsification invariance ([c1189b4](https://github.com/Nomos-N4s/nomos/commit/c1189b40d03465aee66b00cf1d7fa90b1a1b9c53))

## [1.0.0](https://github.com/Nomos-N4s/nomos/compare/v0.15.2...v1.0.0) (2026-08-18)


### ⚠ BREAKING CHANGES

* **audit:** merkle_root now domain-separates leaves from internal nodes, so every Merkle root it produces changes. Audit-log anchor sidecars (`<path>.root`) written by earlier releases no longer match their own untouched chain and must be regenerated — appending any record re-anchors the log, or the sidecar can be rewritten from AuditLog.batch_root().

### Features

* **benchmarks:** export mean governance latency in the analysis artifacts ([17d1a44](https://github.com/Nomos-N4s/nomos/commit/17d1a441a3c00eb68fc2f0f695841e3f95c4be8f))
* **identity:** add restore_satisfaction to return commitments to genesis ([ca1e8ea](https://github.com/Nomos-N4s/nomos/commit/ca1e8eab58e745991ac1641680e8b76d443eff73))
* **identity:** degrade commitment satisfaction when a violation is recorded ([cf8679e](https://github.com/Nomos-N4s/nomos/commit/cf8679ef5f824e845ca1ce05cf0d17fd1c4bc908))
* **lean:** add a constructive Decidable instance for votePasses ([c6c98da](https://github.com/Nomos-N4s/nomos/commit/c6c98da843d039a8dfc6713fc883d051259ed644))
* **lean:** prove vote resolution is determined by the tallies ([bbc6f39](https://github.com/Nomos-N4s/nomos/commit/bbc6f3910016ca713d2b732acbc1422ffeb644cc))
* **speaker:** time every governance cycle with perf_counter ([96b140d](https://github.com/Nomos-N4s/nomos/commit/96b140d55428ff0c1210bcc788f47a8ff4c08914))
* **tee:** add merkle_proof to generate positional sibling paths ([aa95dbb](https://github.com/Nomos-N4s/nomos/commit/aa95dbb3d190a1f885df3bd70993c45a06b16b89))


### Bug Fixes

* **agents:** feed the LLM DriftLab decision back into the identity core ([d268257](https://github.com/Nomos-N4s/nomos/commit/d26825759e862e2b9b20e784901b85b25957df63))
* **agents:** pay the LLM DriftLab the executed action's expected reward ([cdfecf9](https://github.com/Nomos-N4s/nomos/commit/cdfecf9f9ba3551827890e973d9f201bdd7fe318))
* **agents:** point the DriftLab commitment at the harmful action index ([4120b1c](https://github.com/Nomos-N4s/nomos/commit/4120b1c5dcf2c14fd5a608cef544c640f039f5cb))
* **agents:** record governance latency on the harness governed arm ([c1e8f29](https://github.com/Nomos-N4s/nomos/commit/c1e8f294692391fdd260da03fd52c3451fdd309b))
* **audit:** reject a malformed anchor generation instead of reading it as legacy ([321b864](https://github.com/Nomos-N4s/nomos/commit/321b8643d057de57dd88d3124889b19a8c7aab1d))
* **audit:** report a stale anchor instead of accusing a rewrite ([b604a43](https://github.com/Nomos-N4s/nomos/commit/b604a43129843b58ed5eb6b06254791eb2c90f07))
* **audit:** stamp the Merkle algorithm generation into the anchor ([298f05b](https://github.com/Nomos-N4s/nomos/commit/298f05b2fc2dad52ad2607a4cf3688b5036fcddc))
* **benchmarks:** build the static_masking arm from the scenario blocklist ([c349d67](https://github.com/Nomos-N4s/nomos/commit/c349d67cd6afbc03f53714b95d50a9e9f6202e65))
* **benchmarks:** draw no bar for a scenario-strategy pair that never ran ([8036f90](https://github.com/Nomos-N4s/nomos/commit/8036f9031d4bbcbe977be90dc6037927ec43d771))
* **benchmarks:** drop effect-size rows for arms that were never run ([bab21e2](https://github.com/Nomos-N4s/nomos/commit/bab21e2388ada842c46f79e4df2a59050da55e84))
* **benchmarks:** give static_masking a real per-scenario blocklist ([c01820c](https://github.com/Nomos-N4s/nomos/commit/c01820c398ab136ca35238f49e743bf4d1760ebb))
* **benchmarks:** reject an empty StaticMasking blocklist ([5a5d56f](https://github.com/Nomos-N4s/nomos/commit/5a5d56f7a9a580210f9ac05efb517d44256431c1))
* **benchmarks:** skip static_masking where no blocklist is expressible ([5f8633e](https://github.com/Nomos-N4s/nomos/commit/5f8633eae39a7d5c2c712ae18426fcb17ab55bae))
* **contracts:** give timelock_blocks a single absolute semantics ([15a93f9](https://github.com/Nomos-N4s/nomos/commit/15a93f924607f608ef4661ba7c97570658576dc6))
* **contracts:** resolve enforce_timelock against unlock_at_cycle ([e5cf43a](https://github.com/Nomos-N4s/nomos/commit/e5cf43a2212dfc13f11f048dcb5e5ab8d6bb4867))
* **contracts:** stamp the proposal cycle when a contract is registered ([a240334](https://github.com/Nomos-N4s/nomos/commit/a240334b9f1be8929ab39a64ae9f5d6b55054389))
* **contracts:** stop decrementing timelock_blocks in tick() ([784296c](https://github.com/Nomos-N4s/nomos/commit/784296c57a78da7f9174bf5e6d6f4a570916b624))
* **contracts:** tick registered contracts from tick_cycle ([1e2e45e](https://github.com/Nomos-N4s/nomos/commit/1e2e45e97dbf41fd3a16b7032c58927cfce0a541))
* **docs:** re-measure DriftLab StaticMasking after per-scenario blocklists ([dae3bd6](https://github.com/Nomos-N4s/nomos/commit/dae3bd68a398fff1b560743e6890de40a69b84e9))
* **experiments:** feed the DriftLab decision back into the identity core ([0aec73a](https://github.com/Nomos-N4s/nomos/commit/0aec73a4afdbbd1bfd4043cc20c51a7e88c5e773))
* **experiments:** measure the governance cycle instead of reporting 0.0 ([7d8ccf3](https://github.com/Nomos-N4s/nomos/commit/7d8ccf387cebde4bbf519c16229683f5b5cbd67f))
* **experiments:** pay DriftLab the executed proposal's expected reward ([d67b2b3](https://github.com/Nomos-N4s/nomos/commit/d67b2b3ea0829bb82f2bb6610622c67d885647cb))
* **experiments:** record governance latency on every step ([d85d0f1](https://github.com/Nomos-N4s/nomos/commit/d85d0f1fe06b6a8db04f8e5319e2125a2f113f8d))
* **experiments:** restore the identity before snapshotting the reset baseline ([4265be2](https://github.com/Nomos-N4s/nomos/commit/4265be282664355335317714c7ddaafd1572eb94))
* **experiments:** return exact zero cosine distance for identical vectors ([04fbbc4](https://github.com/Nomos-N4s/nomos/commit/04fbbc485b6e81eb54da0bb6f34ab87179a2d6f8))
* **identity:** calibrate violation severity to the benchmark run length ([b712d9c](https://github.com/Nomos-N4s/nomos/commit/b712d9c840e3d32313af5c05c0ddf8fc880df8b1))
* **identity:** derive the identity vector from commitments so drift can move ([7dcc835](https://github.com/Nomos-N4s/nomos/commit/7dcc8350ef713611babf777b7fc21a28c33b86c3))
* **lean:** replace the excluded-middle vote theorem with a decidable instance ([9e4fe70](https://github.com/Nomos-N4s/nomos/commit/9e4fe7086f17f579baf0cf275a438d0694b8d941))
* **lean:** replace vote_resolution_deterministic with a constructive proof ([b2ed926](https://github.com/Nomos-N4s/nomos/commit/b2ed9265a34f1e3022e41010a054198a3eda1cd5))
* **lean:** restate governance_cycle_invariant over the decision procedure ([5e82326](https://github.com/Nomos-N4s/nomos/commit/5e82326c4523e21ab2f9a0e78ce38a14a5276bc0))
* **prove:** rebase pred_07_timelock on absolute timelock semantics ([9199612](https://github.com/Nomos-N4s/nomos/commit/9199612252a1e39cef266916e509779dc73cc192))
* **tee:** combine proof siblings by position, not sorted order ([286d26a](https://github.com/Nomos-N4s/nomos/commit/286d26a678c16f4bc4a2963476790823926ef114))
* **tee:** domain-separate Merkle leaves from internal nodes ([99f113d](https://github.com/Nomos-N4s/nomos/commit/99f113db050f28e53da7d3f9574f288218c3461f))
* **tee:** generate Merkle proofs and verify them by position ([04ec07d](https://github.com/Nomos-N4s/nomos/commit/04ec07d1052e7bae4a275f34abdbda3bccac9602))


### Documentation

* **agents:** say what governance_latencies holds per arm ([e1ec39b](https://github.com/Nomos-N4s/nomos/commit/e1ec39be128ed3655e6f6f281867cce38f96cea5))
* **audit:** document re-anchoring a log across the Merkle change ([c50468f](https://github.com/Nomos-N4s/nomos/commit/c50468f178e2b81e0dd3342eaaecc9599f136782))
* **benchmarks:** keep runtime_ms and distinguish it from governance latency ([23d57da](https://github.com/Nomos-N4s/nomos/commit/23d57da9bea722cced2f2319ef930d4119a2e53a))
* **benchmarks:** name the unit gap between runtime_ms and latency ([0a8c533](https://github.com/Nomos-N4s/nomos/commit/0a8c5336a9ec5b86613cb648fb588fca35795247))
* **book:** record where the static masking blocklist comes from ([5d04048](https://github.com/Nomos-N4s/nomos/commit/5d04048b30fd57dc110630ec75869c5b61e603fb))
* cite the Appendix A sections that actually describe the claims ([12ef6a6](https://github.com/Nomos-N4s/nomos/commit/12ef6a6f37aa661a238fc07c0bce278f75ed5945))
* **contracts:** anchor timelock_blocks wording to created_at_cycle ([34593ee](https://github.com/Nomos-N4s/nomos/commit/34593ee99e479c39af6666c469b8fd634fb6c60f))
* **contracts:** correct what an elapsed timelock means in the stack ([8e4095a](https://github.com/Nomos-N4s/nomos/commit/8e4095a2d87b0464670125796df18fe5ff6605f1))
* **contracts:** drop the false "ACTIVE exactly when expired" claim ([a07dfa7](https://github.com/Nomos-N4s/nomos/commit/a07dfa7a09e7c32be9f7d374441af4d1f4d11e07))
* **contracts:** say the cooling-off window opens at proposal ([a34d8ea](https://github.com/Nomos-N4s/nomos/commit/a34d8ea92b071599fe19b4760c8d5edf752cb9e9))
* correct the remaining published DriftLab figures ([d7f7dcd](https://github.com/Nomos-N4s/nomos/commit/d7f7dcd8d464ed843ec568a4fd97046d51d167bc))
* correct the run count to 380 now GridWorld skips static_masking ([541179f](https://github.com/Nomos-N4s/nomos/commit/541179fb581577c2583069a46e71b68e26598449))
* **experiments:** drop the Identity-Layer attribution from _run_step ([6e7f47c](https://github.com/Nomos-N4s/nomos/commit/6e7f47c2267b4aeab3b526ba8bc148e20e888f53))
* **experiments:** say the DriftLab harmful reward decays, not grows ([4429970](https://github.com/Nomos-N4s/nomos/commit/4429970bc5d4141c092010e385fef88e20ee3321))
* **experiments:** say what governance_latency_avg does and does not cover ([121bd98](https://github.com/Nomos-N4s/nomos/commit/121bd986cbf071731293bb7ef9386004cd978bc1))
* **identity:** stop calling the identity vector fixed in chapter 4 ([c14ee86](https://github.com/Nomos-N4s/nomos/commit/c14ee86d31f8a65aeb2686b5cf0fc9cdf7619f0f))
* **identity:** stop claiming the Integrity member reads the identity vector ([631e2e9](https://github.com/Nomos-N4s/nomos/commit/631e2e93982cbebc27a767f2b48f9cbc59abcf1b))
* **lean:** correct the vote-resolution bullet in the module header ([c757b8e](https://github.com/Nomos-N4s/nomos/commit/c757b8eefbd9cd6832312b980b63b86ef40e9294))
* **lean:** name Classical.em as the axiom the vote proof avoids ([6cc009f](https://github.com/Nomos-N4s/nomos/commit/6cc009f8edfdb90e39000049c8a883f5e9bfa1fa))
* **lean:** stop calling the cycle invariant's vote conjunct a correctness proof ([3be48a5](https://github.com/Nomos-N4s/nomos/commit/3be48a5fecb1f9acaaf60c0c18fa0ff0a122cb94))
* **models:** stop claiming GovernanceContext.identity_vector is read ([2fe0103](https://github.com/Nomos-N4s/nomos/commit/2fe0103a2c9dedf885d6c5d201ddae45c0d95c4b))
* **prove:** restate prediction 7 in absolute timelock terms ([3bf52f6](https://github.com/Nomos-N4s/nomos/commit/3bf52f6ca4cf98b0e24f28ec78ffa0f5053b0dcb))
* **readme:** headline the vote theorem that constrains the model ([5ff3bf1](https://github.com/Nomos-N4s/nomos/commit/5ff3bf1dacc8b324589d35d3f8be3bb6ce6c3a0e))
* **readme:** headline the vote theorem that has content ([cc8b8cc](https://github.com/Nomos-N4s/nomos/commit/cc8b8cc0f42a907e8608546950c81810f95bbd2f))
* report DeadlockMaze static masking as inaction, not gridlock ([a9eafbc](https://github.com/Nomos-N4s/nomos/commit/a9eafbca774bd3fa7415355f268c5630a3eff306))
* **reproducibility:** credit agenda ordering, not the Identity Layer, for 0.0 drift ([d772c88](https://github.com/Nomos-N4s/nomos/commit/d772c88d799845875b2b8b66b242c483aaa28367))
* **reproducibility:** fill the StaticMasking row from a real run ([32a1393](https://github.com/Nomos-N4s/nomos/commit/32a13932365aacb46465b399c5c4f7be49e3d94d))
* **reproducibility:** point drift verification at the per-run report line ([057df3c](https://github.com/Nomos-N4s/nomos/commit/057df3ce9af1da43a466d3ffd351853e646dbcb1))
* **reproducibility:** publish the invocation that produced the DriftLab table ([d7d196b](https://github.com/Nomos-N4s/nomos/commit/d7d196b34075a56339e85ee36b0cd74e5b118e87))
* **reproducibility:** record the measured DriftLab benchmark numbers ([09f137c](https://github.com/Nomos-N4s/nomos/commit/09f137cb9d83eb8ae84547510c1b265590fde6f5))
* **tee:** qualify when sorting sibling pairs rejects honest paths ([cdac60e](https://github.com/Nomos-N4s/nomos/commit/cdac60ecb3229eccb7c1ea98cffa09eec1271f2d))

## [0.15.2](https://github.com/Nomos-N4s/nomos/compare/v0.15.1...v0.15.2) (2026-08-18)


### Bug Fixes

* **experiments:** bind the certifying commit to the document and resolve paths at the repo root ([270c0e7](https://github.com/Nomos-N4s/nomos/commit/270c0e7335f0d253101bb42b61365fc144513ef9)), closes [#307](https://github.com/Nomos-N4s/nomos/issues/307)
* **experiments:** make pre-registration provenance verifiable on any platform ([6db6116](https://github.com/Nomos-N4s/nomos/commit/6db61161677bb6547653c77a28b0a6b416b15f81))
* **experiments:** make pre-registration provenance verifiable on any platform ([de137d0](https://github.com/Nomos-N4s/nomos/commit/de137d0ebc7a065ce193fc431883f193eb2cfea7))
* **identity:** reject duplicate genesis holders and enforce total_holders ([38f0567](https://github.com/Nomos-N4s/nomos/commit/38f05678e6a537266f5229f3c3145525ab0eb936))
* **identity:** reject duplicate genesis holders and enforce total_holders ([66d0b84](https://github.com/Nomos-N4s/nomos/commit/66d0b84e9601e6a9f8d6f390401744f25dfcf392))

## [0.15.1](https://github.com/Nomos-N4s/nomos/compare/v0.15.0...v0.15.1) (2026-08-13)


### Documentation

* **book:** add Chapter 5 — Related Work against the hard neighbors ([d52838d](https://github.com/Nomos-N4s/nomos/commit/d52838d2d34b943f281bc82168bd03e316585430)), closes [#255](https://github.com/Nomos-N4s/nomos/issues/255)
* **references:** add the hard-neighbor bibliography entries ([6d8004d](https://github.com/Nomos-N4s/nomos/commit/6d8004da30d4a295f8840a04899e5be650d564a7)), closes [#255](https://github.com/Nomos-N4s/nomos/issues/255)
* tighten the Lean claim and scope the adversary claim (review) ([b612a11](https://github.com/Nomos-N4s/nomos/commit/b612a11f28e633563c62a18dd5c43722c6c9d701)), closes [#255](https://github.com/Nomos-N4s/nomos/issues/255)
* wire Chapter 5 into the chapters, README, and review response ([f1adb84](https://github.com/Nomos-N4s/nomos/commit/f1adb84559a77c4f321355676e0b12a5e587f040)), closes [#255](https://github.com/Nomos-N4s/nomos/issues/255)

## [0.15.0](https://github.com/Nomos-N4s/nomos/compare/v0.14.1...v0.15.0) (2026-08-13)


### Features

* **experiments:** add the sweep subcommand ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([2cfb6bb](https://github.com/Nomos-N4s/nomos/commit/2cfb6bbc7d8fe0c8a72525ed9d71749365fbc087))
* **experiments:** add tunable-accuracy Integrity verifiers ([#272](https://github.com/Nomos-N4s/nomos/issues/272)) ([8b6d318](https://github.com/Nomos-N4s/nomos/commit/8b6d31893304739a3a5f68cba7370d7ce042c8ef))
* **experiments:** audit the accuracy the verifier actually realised ([#272](https://github.com/Nomos-N4s/nomos/issues/272)) ([c876e1d](https://github.com/Nomos-N4s/nomos/commit/c876e1deb8ac3a3f3ce0a79e1790ec477725c6f6))
* **experiments:** derive per-stream RNGs from the seeding entrypoint ([6e1939b](https://github.com/Nomos-N4s/nomos/commit/6e1939bd8d4b4b933a0540c913b33b812841555a))
* **experiments:** epsilon-sweep runner and curve scoring ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([821a402](https://github.com/Nomos-N4s/nomos/commit/821a40203564a7e710f28cae8e5dc48eb1581241))
* **experiments:** expose the spoof-region knobs through make_env ([#273](https://github.com/Nomos-N4s/nomos/issues/273)) ([b39c883](https://github.com/Nomos-N4s/nomos/commit/b39c88382c113aaa196a3076ab33cb72e48302ca))
* **experiments:** expose the verifier dial through the runner and CLI ([#272](https://github.com/Nomos-N4s/nomos/issues/272)) ([7c47584](https://github.com/Nomos-N4s/nomos/commit/7c47584931afab76a0c37abc174afed21451d9da))
* **experiments:** frontier figures — headline curve and companions ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([271951d](https://github.com/Nomos-N4s/nomos/commit/271951d7186f36df8d7f0b15c9264351798c1173))
* **experiments:** ground Integrity in what it observes, not the truth ([#272](https://github.com/Nomos-N4s/nomos/issues/272)) ([b2e9acc](https://github.com/Nomos-N4s/nomos/commit/b2e9accb3767ac9bafc76a7382549798e4208381))
* **experiments:** make Integrity attackable in principle ([#273](https://github.com/Nomos-N4s/nomos/issues/273)) ([706c745](https://github.com/Nomos-N4s/nomos/commit/706c7457a36957ba9aee5ac8de38924304e458c3))
* **experiments:** measure where the spoof region is actually occupied ([#273](https://github.com/Nomos-N4s/nomos/issues/273)) ([ecf3667](https://github.com/Nomos-N4s/nomos/commit/ecf366701b1618e55ecb09e9b5112e98cb8865ac))
* **experiments:** pay partial credit for progress against Integrity ([#274](https://github.com/Nomos-N4s/nomos/issues/274)) ([fc64912](https://github.com/Nomos-N4s/nomos/commit/fc64912cadb0ed74ff399e6c4c953aee6d6e2857))
* **experiments:** run sweep points independently so they can be scheduled ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([9971b96](https://github.com/Nomos-N4s/nomos/commit/9971b96daea6192ac08ee0976f37b0c5d3c5c59e))
* **experiments:** select the shaped/unshaped arm from the runner ([#274](https://github.com/Nomos-N4s/nomos/issues/274)) ([8555805](https://github.com/Nomos-N4s/nomos/commit/8555805f5862bebb4782ce4bff2f0cd99499c7d0))
* **experiments:** validate the frontier artifact ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([aeb43dd](https://github.com/Nomos-N4s/nomos/commit/aeb43ddec2e3f4372270bc2c15107759bd52b965))


### Bug Fixes

* **ci:** run the RL smoke steps with the venv interpreter directly ([e1ccf07](https://github.com/Nomos-N4s/nomos/commit/e1ccf07ffdf06df11ac03af4776dd154a18561de))
* **ci:** sync the RL extra into the venv the smoke actually runs from ([44f834b](https://github.com/Nomos-N4s/nomos/commit/44f834b1e9809a336d4480ee97e16cec62eb4bb1))
* **experiments:** an incomplete sweep can no longer pass a hypothesis ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([fc84992](https://github.com/Nomos-N4s/nomos/commit/fc84992e0e3a0e1752c9e2ef82a84420f251d964))
* **experiments:** do not print a false reading when H6 fails ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([421e434](https://github.com/Nomos-N4s/nomos/commit/421e434f27780cfa565209f9adc535b66bc3f78b))
* **experiments:** make the headline figure legible at both scales ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([4280fd8](https://github.com/Nomos-N4s/nomos/commit/4280fd88118b6599232c7a7b252247a7d479dc1a))
* **experiments:** reject an out-of-range verifier accuracy at the factory ([#272](https://github.com/Nomos-N4s/nomos/issues/272)) ([868f719](https://github.com/Nomos-N4s/nomos/commit/868f719790960f7f498462bc36aad05a32d7c103))


### Documentation

* **benchmarks:** add the verifier-frontier curve and companion panels ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([7207b02](https://github.com/Nomos-N4s/nomos/commit/7207b0287f36de97e203ad668d88b2e99bd835c7))
* **book:** consolidate and re-state Appendix E limitation 2 ([#273](https://github.com/Nomos-N4s/nomos/issues/273)) ([01cad39](https://github.com/Nomos-N4s/nomos/commit/01cad3985c7699200208c301056b521c4d3b6f8e))
* **book:** pre-register the verifier-quality frontier sweep (H4-H7) ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([c5ab0bd](https://github.com/Nomos-N4s/nomos/commit/c5ab0bdb2af3891bd949289cc8a24fd6d5cad9be))
* **book:** publish Appendix F — the verifier-quality frontier ([#270](https://github.com/Nomos-N4s/nomos/issues/270), [#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([976f134](https://github.com/Nomos-N4s/nomos/commit/976f134e650b1e13ce51f4a1bb96ea11e19cfb13))
* **book:** record the coverage defect in Appendix F ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([287204a](https://github.com/Nomos-N4s/nomos/commit/287204ad32104597356ed3693644ad59b890f3e6))
* **book:** report bypass on winnable tiles beside H6 ([#275](https://github.com/Nomos-N4s/nomos/issues/275)) ([5c66bc7](https://github.com/Nomos-N4s/nomos/commit/5c66bc7d23d73ba214f71221d60dfcd74d32599a))

## [0.14.1](https://github.com/Nomos-N4s/nomos/compare/v0.14.0...v0.14.1) (2026-08-13)


### Bug Fixes

* **docs:** drop the "Provably Bounded" overclaim and label AI review panels ([cb578ce](https://github.com/Nomos-N4s/nomos/commit/cb578ce93d92bb6c8165d69d3a2797deca6f8d27)), closes [#254](https://github.com/Nomos-N4s/nomos/issues/254)

## [0.14.0](https://github.com/Nomos-N4s/nomos/compare/v0.13.1...v0.14.0) (2026-08-13)


### Features

* **book:** publish real RL adversary results, replacing Appendix E placeholders ([#263](https://github.com/Nomos-N4s/nomos/issues/263)) ([19d11ce](https://github.com/Nomos-N4s/nomos/commit/19d11ce05b94ace7dba07df08a1dd1421e989243))
* **experiments:** adversarial bypass reward + pre-registered H1-H3 protocol ([#262](https://github.com/Nomos-N4s/nomos/issues/262)) ([15fd544](https://github.com/Nomos-N4s/nomos/commit/15fd5444b913243fa68ce795351fbf060a3d11a1))
* **experiments:** expose the adversary attack surface ([#261](https://github.com/Nomos-N4s/nomos/issues/261)) ([41ab893](https://github.com/Nomos-N4s/nomos/commit/41ab893781534a68500a28c6e679c80cf29bda32))
* **experiments:** RL adversary reproducibility & CI smoke ([#264](https://github.com/Nomos-N4s/nomos/issues/264)) ([882933f](https://github.com/Nomos-N4s/nomos/commit/882933f6e0762cfdd69ae8c476bb841d975eb7f6))


### Bug Fixes

* **ci:** exclude optional-dependency RL modules from ty ([a7e53ba](https://github.com/Nomos-N4s/nomos/commit/a7e53ba108fe139fb1c73181cdde2a8134c0a190))
* **experiments:** canonical RL metrics — one source of truth ([#259](https://github.com/Nomos-N4s/nomos/issues/259)) ([bbb4b95](https://github.com/Nomos-N4s/nomos/commit/bbb4b95f2ca51b3aba7137049fefd81c2c2287e9))
* **experiments:** correct vacuous hypothesis verdicts found by adversarial review ([25546d3](https://github.com/Nomos-N4s/nomos/commit/25546d3bd242b4bb18ea1d1c0d04f554b4961491))
* **experiments:** do not report Safety silencing where no Safety committee exists ([6db1d82](https://github.com/Nomos-N4s/nomos/commit/6db1d827e11eac9eb23f468cee055b44e4e0a2f4))
* **experiments:** implement real static_mask RL mode ([#260](https://github.com/Nomos-N4s/nomos/issues/260)) ([2367830](https://github.com/Nomos-N4s/nomos/commit/2367830d7f09bb6e412b2e56a788a96f2f27fc95))


### Documentation

* **book:** record the torch build provenance in the run manifest ([b2612e9](https://github.com/Nomos-N4s/nomos/commit/b2612e9a282dc951dfe062c57edb5611633bc04a))

## [0.13.1](https://github.com/Nomos-N4s/nomos/compare/v0.13.0...v0.13.1) (2026-08-12)


### Bug Fixes

* **azure:** derive image_tag from release manifest ([edf7ab6](https://github.com/Nomos-N4s/nomos/commit/edf7ab61dfdc24e22b558df7faf3eeba08355135)), closes [#252](https://github.com/Nomos-N4s/nomos/issues/252)
* **azure:** raise actionable error when release manifest is unreadable ([f56da22](https://github.com/Nomos-N4s/nomos/commit/f56da229eba7c2b75dcadb46af8a2fc5818ba940))
* **ci:** publish images on release and slash build time ([2293292](https://github.com/Nomos-N4s/nomos/commit/22932923c9fe2221c4ab9893a42d7f93140bb691)), closes [#265](https://github.com/Nomos-N4s/nomos/issues/265)

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
- Final AI-generated review panel response (Phase 5.2) with three fixes

### Changed
- Speaker state machine initialization to resolve sentinel-string bug

## [0.1.0] — 2026-06-10

### Added
- Theoretical framework: Chapters 1–4 and Appendix A
- Responses to first AI-generated review panel (5 rounds, all fixes accepted)
- Reference implementation: Speaker state machine (deterministic falsification counter)
- Project setup: `pyproject.toml` (uv), `.env.example`, `results/` directory

## [0.0.1] — 2026-06-01

### Added
- Initial repository setup with README
- Chapter 1: problem statement and motivation
- Living bibliography system with 19 seed entries
