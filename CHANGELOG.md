# Changelog

## [1.20.2](https://github.com/CINEV/codex-lb-cinamon/compare/v1.20.1...v1.20.2) (2026-06-19)


### Bug Fixes

* **proxy:** forward route kwargs through core_stream_responses adapter ([#39](https://github.com/CINEV/codex-lb-cinamon/issues/39)) ([e454ef5](https://github.com/CINEV/codex-lb-cinamon/commit/e454ef512454980e1c06214df633ceb39f4a236e))

## [1.20.1](https://github.com/CINEV/codex-lb-cinamon/compare/v1.20.0...v1.20.1) (2026-06-18)


### Features

* **acc-del:** cascade delete request log option  ([#823](https://github.com/CINEV/codex-lb-cinamon/issues/823)) ([3fac360](https://github.com/CINEV/codex-lb-cinamon/commit/3fac360b5415f414522cd68dd80a47e7210af5ec))
* **accounts:** add account list sort controls ([#897](https://github.com/CINEV/codex-lb-cinamon/issues/897)) ([0e413e6](https://github.com/CINEV/codex-lb-cinamon/commit/0e413e6929261c2ad34c1f060d6d21e70ad4425e))
* **accounts:** add dashboard action for account force-probe ([#895](https://github.com/CINEV/codex-lb-cinamon/issues/895)) ([72222c5](https://github.com/CINEV/codex-lb-cinamon/commit/72222c5a815ea0dbc3e67133adae2f5af324f95e))
* **accounts:** add export action with audit and no-store safeguards ([#412](https://github.com/CINEV/codex-lb-cinamon/issues/412)) ([c03e310](https://github.com/CINEV/codex-lb-cinamon/commit/c03e31023bc0481696f1e85a0d373eaa086ef531))
* **accounts:** add operator-controlled account aliases ([#759](https://github.com/CINEV/codex-lb-cinamon/issues/759)) ([781e259](https://github.com/CINEV/codex-lb-cinamon/commit/781e2598b44356c90fc9e5e9c0780a87b59db202))
* **accounts:** export OpenCode auth json ([#757](https://github.com/CINEV/codex-lb-cinamon/issues/757)) ([530c97f](https://github.com/CINEV/codex-lb-cinamon/commit/530c97f080093db186cdad92cd30939f64836b77))
* **accounts:** expose weekly token pace data ([#655](https://github.com/CINEV/codex-lb-cinamon/issues/655)) ([9bd5bc3](https://github.com/CINEV/codex-lb-cinamon/commit/9bd5bc3b73803935fff437437b0a038002177265))
* **accounts:** surface email duplicate pairs ([#829](https://github.com/CINEV/codex-lb-cinamon/issues/829)) ([ab754ff](https://github.com/CINEV/codex-lb-cinamon/commit/ab754ff0f7e115fe453ea58b108bf69f936afca3)), closes [#787](https://github.com/CINEV/codex-lb-cinamon/issues/787)
* **acc:** preserve metrics when the account is deleted ([#640](https://github.com/CINEV/codex-lb-cinamon/issues/640)) ([4aee3aa](https://github.com/CINEV/codex-lb-cinamon/commit/4aee3aaa26f32bd2c6ac7206afefc70637bc4ea3))
* add reports page with cost/token charts and CSV export ([#854](https://github.com/CINEV/codex-lb-cinamon/issues/854)) ([f5fcfab](https://github.com/CINEV/codex-lb-cinamon/commit/f5fcfabe2f849a711e2a70eb12a3ce4acca21de4))
* **api-keys:** add key overview usage stats ([#900](https://github.com/CINEV/codex-lb-cinamon/issues/900)) ([ed8caab](https://github.com/CINEV/codex-lb-cinamon/commit/ed8caabec424e6b5b5164b3a2b7df180f55f0547))
* **api-ui:** add account cost distribution for API ([#734](https://github.com/CINEV/codex-lb-cinamon/issues/734)) ([d0a6737](https://github.com/CINEV/codex-lb-cinamon/commit/d0a6737fb6016a627b23d12810e4a89d7b062ac3))
* **api-ui:** add account pool window usage remaining bar ([#785](https://github.com/CINEV/codex-lb-cinamon/issues/785)) ([8eee9e2](https://github.com/CINEV/codex-lb-cinamon/commit/8eee9e2c00e3739d1108f3d98cc4bf075d71900e))
* **api:** add app version response header ([#796](https://github.com/CINEV/codex-lb-cinamon/issues/796)) ([a84d6f4](https://github.com/CINEV/codex-lb-cinamon/commit/a84d6f4364751ef897ff779b514430615032a856))
* **api:** add codex /model support for allowed models ([#607](https://github.com/CINEV/codex-lb-cinamon/issues/607)) ([15874aa](https://github.com/CINEV/codex-lb-cinamon/commit/15874aa80795486c0bb0a33489a417c8b5613f51))
* **auth:** proactively refresh stale active accounts ([#928](https://github.com/CINEV/codex-lb-cinamon/issues/928)) ([163326a](https://github.com/CINEV/codex-lb-cinamon/commit/163326a3d099e4542e91cca1ca1150c1503f4605))
* **cli:** add Codex session retag command ([#763](https://github.com/CINEV/codex-lb-cinamon/issues/763)) ([7b67aef](https://github.com/CINEV/codex-lb-cinamon/commit/7b67aef953d5f01f186720010f8a3eb7456d97b1))
* **config:** flexible location of DATA_DIR by env-variable ([#837](https://github.com/CINEV/codex-lb-cinamon/issues/837)) ([3787dd3](https://github.com/CINEV/codex-lb-cinamon/commit/3787dd37e8cdced3ced4cb3e05bd4d0c06d027a4))
* **dashboard-auth:** add read-only guest access ([#703](https://github.com/CINEV/codex-lb-cinamon/issues/703)) ([1f02ec8](https://github.com/CINEV/codex-lb-cinamon/commit/1f02ec80314b788352faec2268f4bb93128fa20a))
* **dashboard-ui:** Multiple dashboard changes ([#973](https://github.com/CINEV/codex-lb-cinamon/issues/973)) ([fc00649](https://github.com/CINEV/codex-lb-cinamon/commit/fc006492107309a2bbb6a6051539a7e8ecccd488))
* **dashboard:** account burn projection card ([#752](https://github.com/CINEV/codex-lb-cinamon/issues/752)) ([c48a20a](https://github.com/CINEV/codex-lb-cinamon/commit/c48a20a566aa74213ec909bcc3e798bf835cbeef))
* **dashboard:** present hourly/weekly credits as raw remaining/total ([#612](https://github.com/CINEV/codex-lb-cinamon/issues/612)) ([b6b2f8b](https://github.com/CINEV/codex-lb-cinamon/commit/b6b2f8b0b64dbef8b66459e21b9406bdc24a8e94))
* **dashboard:** show weekly token pace card ([#656](https://github.com/CINEV/codex-lb-cinamon/issues/656)) ([998e2f0](https://github.com/CINEV/codex-lb-cinamon/commit/998e2f058c2218a69377ce054199d76d4e181107))
* **dashboard:** support weekly pace working days ([#901](https://github.com/CINEV/codex-lb-cinamon/issues/901)) ([7abbcf8](https://github.com/CINEV/codex-lb-cinamon/commit/7abbcf8bdf7222bedf19cea4c78566678083db61))
* **frontend:** add GitHub link to status bar ([#508](https://github.com/CINEV/codex-lb-cinamon/issues/508)) ([8577edc](https://github.com/CINEV/codex-lb-cinamon/commit/8577edc9a2eaeeabc736c2dcc6f3597e2da6e08f))
* **frontend:** add upstream proxy controls ([#912](https://github.com/CINEV/codex-lb-cinamon/issues/912)) ([f1d4826](https://github.com/CINEV/codex-lb-cinamon/commit/f1d4826579406a960a6355b45f1b8ab05d21e32f))
* **observability:** add conversation archive backend ([#653](https://github.com/CINEV/codex-lb-cinamon/issues/653)) ([1473269](https://github.com/CINEV/codex-lb-cinamon/commit/147326907c840f7641bbd353807388743dd6a74b))
* **observability:** add conversation archive viewer ([#654](https://github.com/CINEV/codex-lb-cinamon/issues/654)) ([06ceac7](https://github.com/CINEV/codex-lb-cinamon/commit/06ceac750b2e68d5b9d7cb0080f87a7cffcaf5cc))
* **proxy:** add account-bound Codex upstream routing ([#878](https://github.com/CINEV/codex-lb-cinamon/issues/878)) ([0c01b19](https://github.com/CINEV/codex-lb-cinamon/commit/0c01b197668613d3e14000a7bbdb1ed93cfd7cc5))
* **proxy:** add SOCKS4/SOCKS5 outbound proxy support via env vars ([#1008](https://github.com/CINEV/codex-lb-cinamon/issues/1008)) ([c8fcc65](https://github.com/CINEV/codex-lb-cinamon/commit/c8fcc65a140adf5fdcabd548881b8bd7eb673b64))
* **proxy:** add upstream websocket proxy support ([#758](https://github.com/CINEV/codex-lb-cinamon/issues/758)) ([4532646](https://github.com/CINEV/codex-lb-cinamon/commit/4532646e1de3f48339b37bd3024b35f99ab956ce)), closes [#407](https://github.com/CINEV/codex-lb-cinamon/issues/407)
* **proxy:** restore opportunistic traffic class on main ([#716](https://github.com/CINEV/codex-lb-cinamon/issues/716)) ([52445aa](https://github.com/CINEV/codex-lb-cinamon/commit/52445aa70b700e08875c70dadcac18bdb92bdb04))
* **quota:** add reset-confirmed limit warm-up ([#786](https://github.com/CINEV/codex-lb-cinamon/issues/786)) ([bfc7d6c](https://github.com/CINEV/codex-lb-cinamon/commit/bfc7d6cd4138047dcc8e691a25019f19286a838f))
* **release:** add PR-driven beta release channel ([#732](https://github.com/CINEV/codex-lb-cinamon/issues/732)) ([72b2962](https://github.com/CINEV/codex-lb-cinamon/commit/72b2962b1a45f9b4796f4fc11f3f9db69cbceaf0))
* **report:** add window comparison, cleanup openspec and ui fixes ([776dfaa](https://github.com/CINEV/codex-lb-cinamon/commit/776dfaa30a065ea7a9c4959a5c6b115c236e735d))
* **request-log:** detail cost breakdown for each request ([#694](https://github.com/CINEV/codex-lb-cinamon/issues/694)) ([cb05d0e](https://github.com/CINEV/codex-lb-cinamon/commit/cb05d0eca7908b0be6a82ba0ad736382351a6608))
* **routing:** add relative availability strategy ([#765](https://github.com/CINEV/codex-lb-cinamon/issues/765)) ([7227e16](https://github.com/CINEV/codex-lb-cinamon/commit/7227e169848ffb8580cc0e00f1bc0a9c4260c44f))
* show update indicator for stale runtime version ([#805](https://github.com/CINEV/codex-lb-cinamon/issues/805)) ([76488a5](https://github.com/CINEV/codex-lb-cinamon/commit/76488a5e30d120ab54ed063c9a352819437b1733))
* **ui:** log the User-Agent and store it in database ([#882](https://github.com/CINEV/codex-lb-cinamon/issues/882)) ([1a8e112](https://github.com/CINEV/codex-lb-cinamon/commit/1a8e11256eae2cbf83587621c453b1f2996ec509))
* **ui:** multiple dashboard ui adjustments ([#776](https://github.com/CINEV/codex-lb-cinamon/issues/776)) ([c933b52](https://github.com/CINEV/codex-lb-cinamon/commit/c933b527ea285a543fdbc19a94936b8de66eebc4))
* **ui:** polish proxy and account dashboard UX ([#937](https://github.com/CINEV/codex-lb-cinamon/issues/937)) ([522cae5](https://github.com/CINEV/codex-lb-cinamon/commit/522cae5e4d16e5b1f5abb69de9afb9d21b1500ed))


### Bug Fixes

* **acc:** create `monthly` window for the `free` account due to the policy change ([#909](https://github.com/CINEV/codex-lb-cinamon/issues/909)) ([50b9add](https://github.com/CINEV/codex-lb-cinamon/commit/50b9add6dd5425fb74c5fed65cbcda145ca67fcc))
* **accounts:** avoid SQLite window plan for usage trends ([#861](https://github.com/CINEV/codex-lb-cinamon/issues/861)) ([50b393f](https://github.com/CINEV/codex-lb-cinamon/commit/50b393f9e987ecef2601382e41ff7c480914497e))
* **accounts:** dedupe request usage rows by request id ([#904](https://github.com/CINEV/codex-lb-cinamon/issues/904)) ([86e2350](https://github.com/CINEV/codex-lb-cinamon/commit/86e2350d21fb0b39f3d5f225e46abede49a89e28))
* **accounts:** hide zero-capacity primary quota rows ([#770](https://github.com/CINEV/codex-lb-cinamon/issues/770)) ([8920274](https://github.com/CINEV/codex-lb-cinamon/commit/8920274add84917a63bf18fbbfb475038ffa778a))
* **accounts:** key imported credentials by workspace ([#865](https://github.com/CINEV/codex-lb-cinamon/issues/865)) ([47b0c36](https://github.com/CINEV/codex-lb-cinamon/commit/47b0c3624faf9c40211cbf52957d91ddce4bb5cb))
* **accounts:** mark invalidated credentials for reauth ([#925](https://github.com/CINEV/codex-lb-cinamon/issues/925)) ([39fb653](https://github.com/CINEV/codex-lb-cinamon/commit/39fb653c0e779aef30a2ecbfa6608ea4d797a789))
* **accounts:** own DB session in detached token-refresh task ([#774](https://github.com/CINEV/codex-lb-cinamon/issues/774)) ([3bdc9de](https://github.com/CINEV/codex-lb-cinamon/commit/3bdc9dea0b524ad0e46a89d1afc727712825eb0b))
* **accounts:** preserve shared workspace account slots ([#974](https://github.com/CINEV/codex-lb-cinamon/issues/974)) ([dd4436f](https://github.com/CINEV/codex-lb-cinamon/commit/dd4436f7dc619894e9a38e6c8f4a0a2510230e7b))
* align fork unit CI contracts ([478bdf5](https://github.com/CINEV/codex-lb-cinamon/commit/478bdf566fc3fc261e77f1fe466555518a6b369e))
* align helm smoke policy test with cached ci build ([9aa05c6](https://github.com/CINEV/codex-lb-cinamon/commit/9aa05c606393bebfae2dce54f935b7c5ce0daf3e))
* **api-keys:** map enforced service_tier auto/default to outbound omission ([#611](https://github.com/CINEV/codex-lb-cinamon/issues/611)) ([9a64e23](https://github.com/CINEV/codex-lb-cinamon/commit/9a64e238f185bfee48069029de9a25b3413ad4d8))
* **api-keys:** size usage reservations from request budget ([#706](https://github.com/CINEV/codex-lb-cinamon/issues/706)) ([ea72eea](https://github.com/CINEV/codex-lb-cinamon/commit/ea72eeaac9b8512ba2684f5617c5e6fa04a39fc1))
* **api:** add back the account selection on api creation ([#594](https://github.com/CINEV/codex-lb-cinamon/issues/594)) ([f9b62bf](https://github.com/CINEV/codex-lb-cinamon/commit/f9b62bfdee061a2b1011e804041f631cee1804ec))
* **api:** tolerate null model filters and truncation ([#886](https://github.com/CINEV/codex-lb-cinamon/issues/886)) ([cc636d7](https://github.com/CINEV/codex-lb-cinamon/commit/cc636d7e61bef87bee7f2e8ee988cb8e903fe0c0)), closes [#885](https://github.com/CINEV/codex-lb-cinamon/issues/885) [#856](https://github.com/CINEV/codex-lb-cinamon/issues/856)
* **archive:** stream gzip writes asynchronously ([#725](https://github.com/CINEV/codex-lb-cinamon/issues/725)) ([67917ca](https://github.com/CINEV/codex-lb-cinamon/commit/67917ca310775114ac1a6c6f87befa5487d6e857))
* **archive:** throttle backpressure warnings ([#718](https://github.com/CINEV/codex-lb-cinamon/issues/718)) ([feb0def](https://github.com/CINEV/codex-lb-cinamon/commit/feb0def4fd69a77ff832bd9ffad97852d8628b45))
* **ci:** harden Codex label sync token writes ([#740](https://github.com/CINEV/codex-lb-cinamon/issues/740)) ([c40837d](https://github.com/CINEV/codex-lb-cinamon/commit/c40837dcfeaae8ad22fd73176f8e4f03c0bb1379))
* **ci:** restore main and enforce merge-head gates ([#715](https://github.com/CINEV/codex-lb-cinamon/issues/715)) ([b061ea5](https://github.com/CINEV/codex-lb-cinamon/commit/b061ea5d25c503df8d8961d8b0f92d301ee5ef71))
* **ci:** tolerate transient Codex label read failures ([#769](https://github.com/CINEV/codex-lb-cinamon/issues/769)) ([8fe58fe](https://github.com/CINEV/codex-lb-cinamon/commit/8fe58fe53f6c8c40196043e9a772e2fe78da9f4c))
* **codex desktop:** restore backend responses compatibility ([#756](https://github.com/CINEV/codex-lb-cinamon/issues/756)) ([fe591b7](https://github.com/CINEV/codex-lb-cinamon/commit/fe591b727c9a06aadb5689e1dc9c52550c85b29e))
* Codex websocket pre-created keepalives ([#727](https://github.com/CINEV/codex-lb-cinamon/issues/727)) ([f52167d](https://github.com/CINEV/codex-lb-cinamon/commit/f52167dd6b8e7dee3f40b84e118f4c412a8c2ec9))
* **codex_version:** fall back to npm registry when GitHub is rate-limited ([#744](https://github.com/CINEV/codex-lb-cinamon/issues/744)) ([7d790ba](https://github.com/CINEV/codex-lb-cinamon/commit/7d790bae893b62ff7216c1c3c0f4f11e17015d4f)), closes [#664](https://github.com/CINEV/codex-lb-cinamon/issues/664)
* **codex:** accept OpenAI-style backend responses requests ([#755](https://github.com/CINEV/codex-lb-cinamon/issues/755)) ([838386c](https://github.com/CINEV/codex-lb-cinamon/commit/838386cc0c66c6c0d5ae42e3bd1d20b8681cc313))
* **copy:** add clipboard fallback for non-secure contexts ([#843](https://github.com/CINEV/codex-lb-cinamon/issues/843)) ([58387f0](https://github.com/CINEV/codex-lb-cinamon/commit/58387f0e5fa0781624f1b355af5df207e9e92297))
* **dashboard:** derive quota status from usage windows ([#686](https://github.com/CINEV/codex-lb-cinamon/issues/686)) ([c463def](https://github.com/CINEV/codex-lb-cinamon/commit/c463deffecafd745c96a5a9a3fe053e1e6b9f9bf))
* **dashboard:** make weekly credit pace backend-driven ([#692](https://github.com/CINEV/codex-lb-cinamon/issues/692)) ([313783c](https://github.com/CINEV/codex-lb-cinamon/commit/313783c17294ded64b4a0fc320384da25308bf3b))
* **db,firewall:** validate pooled connections + raise IP cache TTL ([#679](https://github.com/CINEV/codex-lb-cinamon/issues/679)) ([f46a5de](https://github.com/CINEV/codex-lb-cinamon/commit/f46a5de6afed70553381d76532b477ad9fdb2ecd))
* **db,firewall:** validate pooled connections + raise IP cache TTL ([#679](https://github.com/CINEV/codex-lb-cinamon/issues/679)) ([f46a5de](https://github.com/CINEV/codex-lb-cinamon/commit/f46a5de6afed70553381d76532b477ad9fdb2ecd)), closes [#672](https://github.com/CINEV/codex-lb-cinamon/issues/672)
* **db:** recover stale reservations and serialize sqlite writers ([#667](https://github.com/CINEV/codex-lb-cinamon/issues/667)) ([6635628](https://github.com/CINEV/codex-lb-cinamon/commit/663562892396d53affc2f2ddb12790d30487e970))
* **docker:** pin Postgres upgrade helper digest ([#945](https://github.com/CINEV/codex-lb-cinamon/issues/945)) ([66a6220](https://github.com/CINEV/codex-lb-cinamon/commit/66a62204d021fae3d568337daba4c0e685f1a5d0))
* **frontend/auth:** cap dashboard password at 72 UTF-8 bytes ([#615](https://github.com/CINEV/codex-lb-cinamon/issues/615)) ([#647](https://github.com/CINEV/codex-lb-cinamon/issues/647)) ([7ba02b9](https://github.com/CINEV/codex-lb-cinamon/commit/7ba02b97740ab642708b46732bc542ef5d01f2c2))
* **frontend:** disable browser translation on dashboard ([#908](https://github.com/CINEV/codex-lb-cinamon/issues/908)) ([a0aea6d](https://github.com/CINEV/codex-lb-cinamon/commit/a0aea6df9c410185903a021fbef28aa8b40794ea)), closes [#906](https://github.com/CINEV/codex-lb-cinamon/issues/906)
* **frontend:** guard React DOM against translation mutations ([#929](https://github.com/CINEV/codex-lb-cinamon/issues/929)) ([ea9f99c](https://github.com/CINEV/codex-lb-cinamon/commit/ea9f99c6fb253995349fc5a3bee687a179b8b30f))
* integrate upstream v1.20.0 into fork release train ([2fc9d28](https://github.com/CINEV/codex-lb-cinamon/commit/2fc9d28f83adaa2d1c397153656e894f505691cf))
* **limit-warmup:** refresh opt-in state before warm-up ([#778](https://github.com/CINEV/codex-lb-cinamon/issues/778)) ([a96c487](https://github.com/CINEV/codex-lb-cinamon/commit/a96c4876359aa811592e76537cc92125e45c5a3a))
* make helm smoke ci observable ([2fafffb](https://github.com/CINEV/codex-lb-cinamon/commit/2fafffb5e92103486f9de2012347ec0299ea97a6))
* make release-please update fork lockfile ([6e3a82d](https://github.com/CINEV/codex-lb-cinamon/commit/6e3a82d530e0274c02aed7ec21d22893a1a4a788))
* **model-refresh:** refresh HTTP client on transport errors ([#547](https://github.com/CINEV/codex-lb-cinamon/issues/547)) ([2087df0](https://github.com/CINEV/codex-lb-cinamon/commit/2087df09984bf773c4ee1d5dff4ac976162dab52))
* **model-registry:** populate bootstrap model metadata ([#750](https://github.com/CINEV/codex-lb-cinamon/issues/750)) ([5e77320](https://github.com/CINEV/codex-lb-cinamon/commit/5e77320be78676d6f25a39a7ececaa771d923bb2)), closes [#528](https://github.com/CINEV/codex-lb-cinamon/issues/528)
* **models:** report full context in v1 metadata ([#681](https://github.com/CINEV/codex-lb-cinamon/issues/681)) ([c3c977d](https://github.com/CINEV/codex-lb-cinamon/commit/c3c977d9fdfd5e2fc2a9b7f1903622fd8de46c89))
* normalize responses instruction messages ([#950](https://github.com/CINEV/codex-lb-cinamon/issues/950)) ([603c794](https://github.com/CINEV/codex-lb-cinamon/commit/603c794d74547bd122b8dd43668bcc4637480b89))
* **oauth:** isolate concurrent browser flows ([#753](https://github.com/CINEV/codex-lb-cinamon/issues/753)) ([409a83e](https://github.com/CINEV/codex-lb-cinamon/commit/409a83ef5a9c3026a7549c4a63cef4daae1df5cb))
* **openai:** preserve json mode instruction messages ([#731](https://github.com/CINEV/codex-lb-cinamon/issues/731)) ([b48ed67](https://github.com/CINEV/codex-lb-cinamon/commit/b48ed67bef119e5dc0929df20188630b3a0cc5b5)), closes [#730](https://github.com/CINEV/codex-lb-cinamon/issues/730)
* prepare release-please 1.20.1 patch train ([65a4406](https://github.com/CINEV/codex-lb-cinamon/commit/65a44064be8a6ef5f26fdde122ee96397d66a70e))
* preserve bridge websocket adapter patch point ([d39a426](https://github.com/CINEV/codex-lb-cinamon/commit/d39a426eafa5ad3199fb84e01ac9257f95c27d17))
* preserve fork release package identity ([ac85a7b](https://github.com/CINEV/codex-lb-cinamon/commit/ac85a7b0ff62301b0c65e2b569b2af3fa1a5d526))
* **proxy-responses:** harden concurrent responses routing ([#868](https://github.com/CINEV/codex-lb-cinamon/issues/868)) ([cb5951d](https://github.com/CINEV/codex-lb-cinamon/commit/cb5951df0f18f94eac783d57d6f0bac9734c1c7d))
* **proxy:** accept /backend-api/codex/v1/&lt;rest&gt; as alias for /backend-api/codex/&lt;rest&gt; ([#610](https://github.com/CINEV/codex-lb-cinamon/issues/610)) ([0aaaa80](https://github.com/CINEV/codex-lb-cinamon/commit/0aaaa80d69078634dc9b5fe471da2a2d02e3004f))
* **proxy:** add HTTP bridge keepalive backstop and prewarm timeout ([#736](https://github.com/CINEV/codex-lb-cinamon/issues/736)) ([28c2430](https://github.com/CINEV/codex-lb-cinamon/commit/28c243078f7b10d8c08f01f3c6f3bd02f229d056))
* **proxy:** align Codex websocket error parsing ([#789](https://github.com/CINEV/codex-lb-cinamon/issues/789)) ([714315f](https://github.com/CINEV/codex-lb-cinamon/commit/714315f4d443dddf1256d7872a123c639316978a))
* **proxy:** allow larger compressed responses bodies ([#772](https://github.com/CINEV/codex-lb-cinamon/issues/772)) ([67795a1](https://github.com/CINEV/codex-lb-cinamon/commit/67795a1ae8e5420070502bee5ad029182471bef5))
* **proxy:** avoid unsafe websocket previous-response replay ([#802](https://github.com/CINEV/codex-lb-cinamon/issues/802)) ([b58e724](https://github.com/CINEV/codex-lb-cinamon/commit/b58e7249a80f04300febbe93362f6230c72fcd16))
* **proxy:** bound HTTP bridge startup waits ([#723](https://github.com/CINEV/codex-lb-cinamon/issues/723)) ([48e7ccf](https://github.com/CINEV/codex-lb-cinamon/commit/48e7ccf924260255d912d0b9e637b3be37537c8c))
* **proxy:** bridge codex compaction triggers ([#977](https://github.com/CINEV/codex-lb-cinamon/issues/977)) ([bf1ded2](https://github.com/CINEV/codex-lb-cinamon/commit/bf1ded2e1f994a79cfc05c640ba911ee4e4ffa9c))
* **proxy:** bypass HTTP bridge for input images ([#903](https://github.com/CINEV/codex-lb-cinamon/issues/903)) ([bcd63c8](https://github.com/CINEV/codex-lb-cinamon/commit/bcd63c8272b066f0a6ec7d624f07c33b45e26a18))
* **proxy:** cap selector "Try again in" hint at 300s ([#690](https://github.com/CINEV/codex-lb-cinamon/issues/690)) ([cf09bd6](https://github.com/CINEV/codex-lb-cinamon/commit/cf09bd6d4ad1bfad91b458681f491ec36fef9772)), closes [#676](https://github.com/CINEV/codex-lb-cinamon/issues/676) [#678](https://github.com/CINEV/codex-lb-cinamon/issues/678)
* **proxy:** classify request budget exhaustion as timeout ([#820](https://github.com/CINEV/codex-lb-cinamon/issues/820)) ([978797a](https://github.com/CINEV/codex-lb-cinamon/commit/978797a82a8931f95695d837be2d7cc3cf073703))
* **proxy:** classify stale Codex websocket anchors ([#801](https://github.com/CINEV/codex-lb-cinamon/issues/801)) ([93ce129](https://github.com/CINEV/codex-lb-cinamon/commit/93ce1299a73dab1d2f5231bf4d39fb99d2c135ff))
* **proxy:** clear stale HTTP bridge retry errors ([#815](https://github.com/CINEV/codex-lb-cinamon/issues/815)) ([5aa2162](https://github.com/CINEV/codex-lb-cinamon/commit/5aa21624ff4528ac9d1cfe17dca37fde9ae2de94))
* **proxy:** eliminate /v1 responses cancel/retry stream contamination ([#696](https://github.com/CINEV/codex-lb-cinamon/issues/696)) ([c9da497](https://github.com/CINEV/codex-lb-cinamon/commit/c9da4974c9b10217e83f7dc0a81f5207337c7c58))
* **proxy:** extend HTTP Responses stream budget ([#825](https://github.com/CINEV/codex-lb-cinamon/issues/825)) ([3993c9c](https://github.com/CINEV/codex-lb-cinamon/commit/3993c9cede74b9ff3450821ae67777885e5b1c13))
* **proxy:** fail over compact after invalidated token ([#777](https://github.com/CINEV/codex-lb-cinamon/issues/777)) ([afd23d2](https://github.com/CINEV/codex-lb-cinamon/commit/afd23d229901d39c99f15bc0bd686b6c7df73ce2))
* **proxy:** fail over reset-prone upstream stalls ([#771](https://github.com/CINEV/codex-lb-cinamon/issues/771)) ([13dcf74](https://github.com/CINEV/codex-lb-cinamon/commit/13dcf7434f65ab0ba4a8c1f1136d05b602f4cb01))
* **proxy:** fail over websocket connect timeouts ([#726](https://github.com/CINEV/codex-lb-cinamon/issues/726)) ([a8b44f7](https://github.com/CINEV/codex-lb-cinamon/commit/a8b44f77d8ef954e983095ff47fbff21c96e3e8c))
* **proxy:** give HTTP bridge long-turn budget ([#819](https://github.com/CINEV/codex-lb-cinamon/issues/819)) ([ff02923](https://github.com/CINEV/codex-lb-cinamon/commit/ff029236ae605a481b0d138392a9f88f85de7afc))
* **proxy:** harden long Codex websocket turns ([#674](https://github.com/CINEV/codex-lb-cinamon/issues/674)) ([12bec0f](https://github.com/CINEV/codex-lb-cinamon/commit/12bec0f37f853342d3fa6eab1624bccd1c20d961))
* **proxy:** harden responses bridge stale cleanup ([#931](https://github.com/CINEV/codex-lb-cinamon/issues/931)) ([c90d62b](https://github.com/CINEV/codex-lb-cinamon/commit/c90d62b72af6bb1bda61650a6b624a4236a4c324))
* **proxy:** improve Cursor chat-completions compatibility ([#833](https://github.com/CINEV/codex-lb-cinamon/issues/833)) ([a1cb7e0](https://github.com/CINEV/codex-lb-cinamon/commit/a1cb7e098321287d82046f8f149e16ff0ec05729))
* **proxy:** include sticky thread in budget-pressure guard ([#514](https://github.com/CINEV/codex-lb-cinamon/issues/514)) ([1e2c6d6](https://github.com/CINEV/codex-lb-cinamon/commit/1e2c6d6fb49bb74bae2707f7afb5de6514c95a73))
* **proxy:** inline external image URLs in HTTP bridge path ([#794](https://github.com/CINEV/codex-lb-cinamon/issues/794)) ([5ff6679](https://github.com/CINEV/codex-lb-cinamon/commit/5ff6679e3b6fc1801080a95cc62986a78d48b7be))
* **proxy:** keep idle timeout classification after scheduler jitter ([#693](https://github.com/CINEV/codex-lb-cinamon/issues/693)) ([17e8abc](https://github.com/CINEV/codex-lb-cinamon/commit/17e8abc0eca7cb823eb3c7f7e9687b45dca920a8))
* **proxy:** keep local usage snapshots advisory ([#1030](https://github.com/CINEV/codex-lb-cinamon/issues/1030)) ([ceb671a](https://github.com/CINEV/codex-lb-cinamon/commit/ceb671a872de66e2c3513c0cdeb6fea6ccb88d57))
* **proxy:** keep streams alive while account capacity recovers ([#1000](https://github.com/CINEV/codex-lb-cinamon/issues/1000)) ([8d8061b](https://github.com/CINEV/codex-lb-cinamon/commit/8d8061bae897863603fd6876d164811a796a5310))
* **proxy:** make Codex Spark quota gating plan-aware ([#751](https://github.com/CINEV/codex-lb-cinamon/issues/751)) ([a476ecd](https://github.com/CINEV/codex-lb-cinamon/commit/a476ecd866e9e1f8507be645146aceafec9eb082))
* **proxy:** mask codex chatgpt previous-response websocket errors ([#775](https://github.com/CINEV/codex-lb-cinamon/issues/775)) ([d39350f](https://github.com/CINEV/codex-lb-cinamon/commit/d39350f323cfcc024f3c2e125a5d3c813772a933))
* **proxy:** mask partial previous-response stream errors ([#689](https://github.com/CINEV/codex-lb-cinamon/issues/689)) ([a4a138c](https://github.com/CINEV/codex-lb-cinamon/commit/a4a138cd3003ad891212760f4ffe63bab798e9f7))
* **proxy:** mask websocket prepare continuity errors ([#717](https://github.com/CINEV/codex-lb-cinamon/issues/717)) ([a0a290b](https://github.com/CINEV/codex-lb-cinamon/commit/a0a290b0f9c9e2b82dad10a9e6812e84d507cea0))
* **proxy:** parse multiline Codex websocket errors ([#810](https://github.com/CINEV/codex-lb-cinamon/issues/810)) ([1f089f2](https://github.com/CINEV/codex-lb-cinamon/commit/1f089f2991640847bc8c0c9471f84195aaf5b69f))
* **proxy:** persist request logs outside cancellation ([#688](https://github.com/CINEV/codex-lb-cinamon/issues/688)) ([6e8fa56](https://github.com/CINEV/codex-lb-cinamon/commit/6e8fa56fe07967d74b7e84b7757238425a989e5f))
* **proxy:** pre-validate strict function tool schemas ([#658](https://github.com/CINEV/codex-lb-cinamon/issues/658)) ([0998cac](https://github.com/CINEV/codex-lb-cinamon/commit/0998cacd25f9e057a790155c07b2d121a697d46e))
* **proxy:** preserve codex image generation tools ([#930](https://github.com/CINEV/codex-lb-cinamon/issues/930)) ([fb8800f](https://github.com/CINEV/codex-lb-cinamon/commit/fb8800f463f153bc4861bdb91adcaf7edf24bf6c)), closes [#839](https://github.com/CINEV/codex-lb-cinamon/issues/839)
* **proxy:** proxy Codex control-plane protocol ([#596](https://github.com/CINEV/codex-lb-cinamon/issues/596)) ([1ca7d2e](https://github.com/CINEV/codex-lb-cinamon/commit/1ca7d2e8a20375f0062866de6296792954ff37a4))
* **proxy:** recover stale websocket previous response anchors ([#724](https://github.com/CINEV/codex-lb-cinamon/issues/724)) ([48f083e](https://github.com/CINEV/codex-lb-cinamon/commit/48f083ef1ffb74be867636abd9fc737e5086692b))
* **proxy:** recover websocket terminal auth failures ([#809](https://github.com/CINEV/codex-lb-cinamon/issues/809)) ([098100f](https://github.com/CINEV/codex-lb-cinamon/commit/098100f7d84548ab9a2e88b8c4bcc1d9004a6743))
* **proxy:** repair interrupted Codex response continuity ([#698](https://github.com/CINEV/codex-lb-cinamon/issues/698)) ([682447f](https://github.com/CINEV/codex-lb-cinamon/commit/682447f2981f608bd94e19dce3c58a464c564568))
* **proxy:** repair request failure metadata migration ([#870](https://github.com/CINEV/codex-lb-cinamon/issues/870)) ([0e584fa](https://github.com/CINEV/codex-lb-cinamon/commit/0e584fa81c0b7e89ac57ba8cc9d5b13b02bd6d54))
* **proxy:** replay HTTP bridge quota failures ([#634](https://github.com/CINEV/codex-lb-cinamon/issues/634)) ([ad34477](https://github.com/CINEV/codex-lb-cinamon/commit/ad3447776e8312f8bd1967dfaa659b8961916882))
* **proxy:** replay pre-visible websocket drops ([#729](https://github.com/CINEV/codex-lb-cinamon/issues/729)) ([4471b9a](https://github.com/CINEV/codex-lb-cinamon/commit/4471b9af4254505b7aa46eeb2097049f215ff6c7))
* **proxy:** report backend context window in v1 models ([#722](https://github.com/CINEV/codex-lb-cinamon/issues/722)) ([ebabd31](https://github.com/CINEV/codex-lb-cinamon/commit/ebabd312e23ab62b7a718da332457989d6311e12))
* **proxy:** respect stream_idle_timeout_seconds in HTTP bridge keepalive backstop ([#793](https://github.com/CINEV/codex-lb-cinamon/issues/793)) ([ccdf99f](https://github.com/CINEV/codex-lb-cinamon/commit/ccdf99fd4b3695b7f9933af9886b0f9e5d252477))
* **proxy:** suppress duplicate side-effect tool calls ([#586](https://github.com/CINEV/codex-lb-cinamon/issues/586)) ([bc5d1bd](https://github.com/CINEV/codex-lb-cinamon/commit/bc5d1bd0a97cbcc2a292ec4f615185409322327d))
* **proxy:** trim anchored http bridge replay inputs ([#652](https://github.com/CINEV/codex-lb-cinamon/issues/652)) ([3d682a6](https://github.com/CINEV/codex-lb-cinamon/commit/3d682a6dd0d2a2b99a8ed9a164e81403fcb8bce4))
* **proxy:** trim durable full-resend continuations ([#687](https://github.com/CINEV/codex-lb-cinamon/issues/687)) ([dfc38c0](https://github.com/CINEV/codex-lb-cinamon/commit/dfc38c0d35398012086e2bac7c92c27a13ce8441))
* **proxy:** trim replayed websocket tool inputs ([#651](https://github.com/CINEV/codex-lb-cinamon/issues/651)) ([0ea6293](https://github.com/CINEV/codex-lb-cinamon/commit/0ea6293ea60282880cd39e46e291f0eafdeb16c0))
* **proxy:** trim websocket codex full-replay continuations ([#650](https://github.com/CINEV/codex-lb-cinamon/issues/650)) ([e503b06](https://github.com/CINEV/codex-lb-cinamon/commit/e503b068bea04eec70a5db9d5d0c3ddd40fab7f9))
* **quota:** keep credit-backed accounts usable ([#764](https://github.com/CINEV/codex-lb-cinamon/issues/764)) ([6da403a](https://github.com/CINEV/codex-lb-cinamon/commit/6da403a6195d42943393229cb0c18ba8ba96d277))
* record fork contributor metadata ([b13cc39](https://github.com/CINEV/codex-lb-cinamon/commit/b13cc396da3460df69766d5707ab866c7ee14619))
* **release:** require validation for canonical beta PRs ([#1032](https://github.com/CINEV/codex-lb-cinamon/issues/1032)) ([2a64002](https://github.com/CINEV/codex-lb-cinamon/commit/2a64002b429478273610de00a4ca10f9f5e3d743))
* **repo:** remove Codex sandbox-breaking symlink ([#942](https://github.com/CINEV/codex-lb-cinamon/issues/942)) ([1b03833](https://github.com/CINEV/codex-lb-cinamon/commit/1b038334f811af67df54389f2c42345b5391caaa))
* **report-ui:** fix language and onHover Tooltip alignment ([#961](https://github.com/CINEV/codex-lb-cinamon/issues/961)) ([094d47b](https://github.com/CINEV/codex-lb-cinamon/commit/094d47be5982dbcde48a48a8723076b5423d6786))
* **report:** add ui changes on report ([776dfaa](https://github.com/CINEV/codex-lb-cinamon/commit/776dfaa30a065ea7a9c4959a5c6b115c236e735d))
* **report:** multiple fix for report ui ([776dfaa](https://github.com/CINEV/codex-lb-cinamon/commit/776dfaa30a065ea7a9c4959a5c6b115c236e735d))
* **report:** Multiple fixes and enhances on report ([#990](https://github.com/CINEV/codex-lb-cinamon/issues/990)) ([776dfaa](https://github.com/CINEV/codex-lb-cinamon/commit/776dfaa30a065ea7a9c4959a5c6b115c236e735d))
* restore fork CI compatibility after upstream sync ([79bb1b4](https://github.com/CINEV/codex-lb-cinamon/commit/79bb1b4a4b050e9a89e00cf4c0435339c3436f40))
* **security:** harden CodeQL alert surfaces ([#935](https://github.com/CINEV/codex-lb-cinamon/issues/935)) ([2992b86](https://github.com/CINEV/codex-lb-cinamon/commit/2992b86d52a1b5fc13cc238ed684b6ef8b816044))
* **security:** remediate Docker code scanning alerts ([#699](https://github.com/CINEV/codex-lb-cinamon/issues/699)) ([de24c2e](https://github.com/CINEV/codex-lb-cinamon/commit/de24c2ea374b3b398792dd2e61f2cb7efcab233d))
* **settings:** include all updatable fields in audit changed_fields ([#719](https://github.com/CINEV/codex-lb-cinamon/issues/719)) ([def95bb](https://github.com/CINEV/codex-lb-cinamon/commit/def95bb8dc085e83f869a6919a054a4a7502f11a))
* split helm smoke ci modes ([90ad11a](https://github.com/CINEV/codex-lb-cinamon/commit/90ad11a59eb0fc597ec260e0aac0358065e48d99))
* stabilize fork integration core ci ([5c4ef06](https://github.com/CINEV/codex-lb-cinamon/commit/5c4ef06b2b4e39890a98324caab4403801075bb0))
* stabilize helm smoke ci image build ([0667d5c](https://github.com/CINEV/codex-lb-cinamon/commit/0667d5c20571cdc09861b3f114fe3a6826027e44))
* **status:** reconcile background account recovery after resets ([#754](https://github.com/CINEV/codex-lb-cinamon/issues/754)) ([4b9ada8](https://github.com/CINEV/codex-lb-cinamon/commit/4b9ada8e398bb4cc50471e2fd3c6186b367b96ed)), closes [#479](https://github.com/CINEV/codex-lb-cinamon/issues/479)
* **sticky-sessions:** chunk delete_entries to avoid sqlite bind overflow ([#828](https://github.com/CINEV/codex-lb-cinamon/issues/828)) ([20158f9](https://github.com/CINEV/codex-lb-cinamon/commit/20158f9e5e5e01454f7c9e162f280e01a0b4f27c))
* **usage:** ignore stale usage after account reset ([#760](https://github.com/CINEV/codex-lb-cinamon/issues/760)) ([d739ebf](https://github.com/CINEV/codex-lb-cinamon/commit/d739ebf142b59a06b013f14cb558f004e207939d))
* use release-please patch versioning config ([4288591](https://github.com/CINEV/codex-lb-cinamon/commit/428859158747f154046e0a7e49d2616b7cbb5f12))


### Performance Improvements

* **dashboard:** load projections in background ([#800](https://github.com/CINEV/codex-lb-cinamon/issues/800)) ([5c40be8](https://github.com/CINEV/codex-lb-cinamon/commit/5c40be83dc128754df3c5711d5a5d45f364b9e80))
* **dashboard:** memoize per-account depletion EWMA state ([#749](https://github.com/CINEV/codex-lb-cinamon/issues/749)) ([2abe7a9](https://github.com/CINEV/codex-lb-cinamon/commit/2abe7a98c7ac95fcc9348b09858dc1f0b7a524b2))
* **dashboard:** speed up SQLite overview usage reads ([#866](https://github.com/CINEV/codex-lb-cinamon/issues/866)) ([7b1d208](https://github.com/CINEV/codex-lb-cinamon/commit/7b1d208ff3f53bf62472c040699e3bd805f6f8da))
* **db:** add raw window usage latest index ([#797](https://github.com/CINEV/codex-lb-cinamon/issues/797)) ([93be0cd](https://github.com/CINEV/codex-lb-cinamon/commit/93be0cdc5bbf6f9afedb969d9ff81b7038d41dbf))
* **usage:** avoid SQLite window latest usage lookup ([#862](https://github.com/CINEV/codex-lb-cinamon/issues/862)) ([65c5f4f](https://github.com/CINEV/codex-lb-cinamon/commit/65c5f4f56e2f10ca035dbc8a584fedfe77a32f47))


### Documentation

* add AnobleSCM as a contributor for code, and test ([#695](https://github.com/CINEV/codex-lb-cinamon/issues/695)) ([718931e](https://github.com/CINEV/codex-lb-cinamon/commit/718931e7d036cd2ab57cec9a9d6507bb5231c3d8))
* add aruis as a contributor for code, test, and bug ([#646](https://github.com/CINEV/codex-lb-cinamon/issues/646)) ([ba1948b](https://github.com/CINEV/codex-lb-cinamon/commit/ba1948be1085290897785d63acca66d2e1560e00))
* add balakumardev as a contributor for ideas ([#468](https://github.com/CINEV/codex-lb-cinamon/issues/468)) ([1c75087](https://github.com/CINEV/codex-lb-cinamon/commit/1c750879c16f2714a25055af93ba6fec60f15d6c))
* add jgorostegui as contributor ([#697](https://github.com/CINEV/codex-lb-cinamon/issues/697)) ([d9d5a6e](https://github.com/CINEV/codex-lb-cinamon/commit/d9d5a6e8d8bf1067ec8db4e98aeb2855e5a75de5))
* add linusmixson as contributor ([#705](https://github.com/CINEV/codex-lb-cinamon/issues/705)) ([f3ad60a](https://github.com/CINEV/codex-lb-cinamon/commit/f3ad60aa4933ffde83096bc7c4da7b224cb4ce84))
* add Lotfree618 as a contributor for code, test, and 2 more ([#739](https://github.com/CINEV/codex-lb-cinamon/issues/739)) ([66764f4](https://github.com/CINEV/codex-lb-cinamon/commit/66764f44aa81e378e0c43fe5e549de766d550d1a))
* add plastictaste as a contributor for code, test, and doc ([#1003](https://github.com/CINEV/codex-lb-cinamon/issues/1003)) ([013b98f](https://github.com/CINEV/codex-lb-cinamon/commit/013b98fa2d184998f880bc7020eb6ee47fb2911e))
* add PR readiness trapdoors to AGENTS ([#838](https://github.com/CINEV/codex-lb-cinamon/issues/838)) ([9b0f5c1](https://github.com/CINEV/codex-lb-cinamon/commit/9b0f5c1e9d5cc17dae6865c199f6527bd38c527a))
* add usage reset troubleshooting FAQ ([#710](https://github.com/CINEV/codex-lb-cinamon/issues/710)) ([b6c35f6](https://github.com/CINEV/codex-lb-cinamon/commit/b6c35f6cfa6a35f56b93718305ca1755773aac61))
* backfill missing contributors ([#741](https://github.com/CINEV/codex-lb-cinamon/issues/741)) ([505a208](https://github.com/CINEV/codex-lb-cinamon/commit/505a2081f5a1a3e7a195888a454d46a822546b80))
* **images:** clarify single-image request contract ([#891](https://github.com/CINEV/codex-lb-cinamon/issues/891)) ([65b5e72](https://github.com/CINEV/codex-lb-cinamon/commit/65b5e729be52bb79e0f70fe2cdda8a37d324ac3e))
* **proxy:** explain fast mode service tiers ([#910](https://github.com/CINEV/codex-lb-cinamon/issues/910)) ([769a12c](https://github.com/CINEV/codex-lb-cinamon/commit/769a12ca126df42cd7aa086709fbb965e27fa690)), closes [#291](https://github.com/CINEV/codex-lb-cinamon/issues/291)
* **readme:** clarify plan-dependent model availability ([#893](https://github.com/CINEV/codex-lb-cinamon/issues/893)) ([5c114a0](https://github.com/CINEV/codex-lb-cinamon/commit/5c114a08b1fa47c3be1522a43ec7fff9cd861dc9)), closes [#375](https://github.com/CINEV/codex-lb-cinamon/issues/375) [#219](https://github.com/CINEV/codex-lb-cinamon/issues/219)
* **readme:** lowercase codex provider name to match Codex 2026-05-23 update ([#798](https://github.com/CINEV/codex-lb-cinamon/issues/798)) ([a185479](https://github.com/CINEV/codex-lb-cinamon/commit/a185479f9b080a6c00c503e74ed6947a9e4b5dbe)), closes [#783](https://github.com/CINEV/codex-lb-cinamon/issues/783)
* **readme:** update all-contributors emoji key link ([#830](https://github.com/CINEV/codex-lb-cinamon/issues/830)) ([88eeba9](https://github.com/CINEV/codex-lb-cinamon/commit/88eeba910363ef2b01da6433360479ca282930d6))

## [1.17.2](https://github.com/CINEV/codex-lb-cinamon/compare/v1.17.1...v1.17.2) (2026-05-15)


### Bug Fixes

* **proxy:** force platform service tier default ([e2719c2](https://github.com/CINEV/codex-lb-cinamon/commit/e2719c2452cf6d4eccba23610811708ad9a6383a))
* **proxy:** force platform service tier default ([e9c82b7](https://github.com/CINEV/codex-lb-cinamon/commit/e9c82b77f2df1738683fd5fd12ec58f6aaf01952))

## [1.17.1](https://github.com/CINEV/codex-lb-cinamon/compare/v1.17.0...v1.17.1) (2026-05-15)


### Bug Fixes

* **proxy:** harden platform cache alerts ([dd0fd98](https://github.com/CINEV/codex-lb-cinamon/commit/dd0fd983ef5801718e08c6e0e5d7b7799eb07da7))

## [1.17.0](https://github.com/CINEV/codex-lb-cinamon/compare/v1.16.0...v1.17.0) (2026-05-14)


### Features

* **proxy:** alert on platform cache misses ([9263d2e](https://github.com/CINEV/codex-lb-cinamon/commit/9263d2ed42cf19efcd145d271f1b79367d1aa40a))


### Bug Fixes

* **chat:** resolve parallel tool_call argument duplication via output_index routing ([#543](https://github.com/CINEV/codex-lb-cinamon/issues/543)) ([6b1cb47](https://github.com/CINEV/codex-lb-cinamon/commit/6b1cb47e3e39a9825b25282b0f8ec2911743786a))
* **proxy:** preserve platform fallback cache affinity ([118bbcc](https://github.com/CINEV/codex-lb-cinamon/commit/118bbcc0942552ba30a3b1c51d3f92dc0caf960a))
* **proxy:** preserve platform fallback cache affinity ([d7df03e](https://github.com/CINEV/codex-lb-cinamon/commit/d7df03e1f8e3c43c8fc875365ca9d398b668b191))
* **proxy:** preserve websocket stream error statuses ([#585](https://github.com/CINEV/codex-lb-cinamon/issues/585)) ([8530f89](https://github.com/CINEV/codex-lb-cinamon/commit/8530f89374e9c648f5fb91deaa9adaf244c3535c))

## [1.16.0](https://github.com/CINEV/codex-lb-cinamon/compare/v1.15.2...v1.16.0) (2026-05-12)


### Features

* **accounts:** split compact quota row display ([#562](https://github.com/CINEV/codex-lb-cinamon/issues/562)) ([9581fe7](https://github.com/CINEV/codex-lb-cinamon/commit/9581fe7c65f025780943486757a0c8020d7b7917))
* **dash:** sort the pie in decending order for better graphing. ([#580](https://github.com/CINEV/codex-lb-cinamon/issues/580)) ([3a60855](https://github.com/CINEV/codex-lb-cinamon/commit/3a60855f31d86c28e5a0ab7990cead61da4f0e52))
* **proxy:** add /backend-api/files upload protocol ([#515](https://github.com/CINEV/codex-lb-cinamon/issues/515)) ([7ecb77a](https://github.com/CINEV/codex-lb-cinamon/commit/7ecb77ae854591e1e6c4e50e785573c74b7ca68e))


### Bug Fixes

* **accounts:** recover quota status from usage refresh ([#559](https://github.com/CINEV/codex-lb-cinamon/issues/559)) ([ee747d3](https://github.com/CINEV/codex-lb-cinamon/commit/ee747d373b50386461ed41ec6dc463cb14912a57))
* **db:** size background pool for burst traffic ([#563](https://github.com/CINEV/codex-lb-cinamon/issues/563)) ([1e397e8](https://github.com/CINEV/codex-lb-cinamon/commit/1e397e806de92a8eb7f8fbb9326ffdebdd75e6ea))
* **openspec:** satisfy strict purpose validation ([#552](https://github.com/CINEV/codex-lb-cinamon/issues/552)) ([1d88236](https://github.com/CINEV/codex-lb-cinamon/commit/1d882362bf9813488f1b2d9f40f32d67d491b453))
* **proxy:** emit text deltas for final response output ([#504](https://github.com/CINEV/codex-lb-cinamon/issues/504)) ([b9c2474](https://github.com/CINEV/codex-lb-cinamon/commit/b9c24748eb983a002c007fe5fbd8dbfc48135efa))
* **proxy:** expose drain status for graceful deploys ([#564](https://github.com/CINEV/codex-lb-cinamon/issues/564)) ([a2fca41](https://github.com/CINEV/codex-lb-cinamon/commit/a2fca41791bd62862a439b7562b7b69deefa615d))
* **proxy:** handle model fetch timeouts ([#541](https://github.com/CINEV/codex-lb-cinamon/issues/541)) ([d4520d7](https://github.com/CINEV/codex-lb-cinamon/commit/d4520d7ad7d15d3676b1ba46a91be149f7fe2854))
* **proxy:** inject SSE keepalive comment frames to prevent client stream hangs [Codex getting stuck issue] ([#524](https://github.com/CINEV/codex-lb-cinamon/issues/524)) ([66302c3](https://github.com/CINEV/codex-lb-cinamon/commit/66302c3efe026813fb4bd48c5754fc3b7926dfbd))
* **proxy:** inline-rewrite input_image file references using codex-faithful image pipeline ([#571](https://github.com/CINEV/codex-lb-cinamon/issues/571)) ([2848df7](https://github.com/CINEV/codex-lb-cinamon/commit/2848df7cdbea7089746f7b929ed2a6d49acfd2bb))
* **proxy:** narrow budget-safe gate to primary usage ([#561](https://github.com/CINEV/codex-lb-cinamon/issues/561)) ([3ed7834](https://github.com/CINEV/codex-lb-cinamon/commit/3ed78347e462c99f9b6950534b395e4850ae6e1b))
* **proxy:** retry transient stream timeouts ([#551](https://github.com/CINEV/codex-lb-cinamon/issues/551)) ([77944c9](https://github.com/CINEV/codex-lb-cinamon/commit/77944c93b61c516f205681e1b09bbba38c46f88e))
* **proxy:** slim oversized response.create history ([#560](https://github.com/CINEV/codex-lb-cinamon/issues/560)) ([e42af5e](https://github.com/CINEV/codex-lb-cinamon/commit/e42af5e5a0a21ce27a48af1bb4136dc015c092bf))
* **proxy:** use DEFAULT_HOME_DIR for oversized response.create dumps ([#575](https://github.com/CINEV/codex-lb-cinamon/issues/575)) ([ad5ebf8](https://github.com/CINEV/codex-lb-cinamon/commit/ad5ebf831731ac1aa05c47cd4a5f6738b8d14dd0))
* **release:** restore release-please baseline ([17572de](https://github.com/CINEV/codex-lb-cinamon/commit/17572ded1505562aad2259dfca307becc96d4fc4))
* **release:** restore release-please baseline ([4764930](https://github.com/CINEV/codex-lb-cinamon/commit/4764930a4d10d3d5d48621072740ca547d9e1fa5))
* there is no primary quota for free account, which cause the pie chart wrong on 5h ([#579](https://github.com/CINEV/codex-lb-cinamon/issues/579)) ([97b1de4](https://github.com/CINEV/codex-lb-cinamon/commit/97b1de44e437bc9ed7a5405ffc42474d18ac71bb))
* **types:** clear existing ty diagnostics ([#517](https://github.com/CINEV/codex-lb-cinamon/issues/517)) ([0cd5d4e](https://github.com/CINEV/codex-lb-cinamon/commit/0cd5d4ebe49e4507e4aaa937c940f198e77ce7b0))
* **upstream:** drop top_p because majority of gpt-5 don't support it, same as temperature ([#538](https://github.com/CINEV/codex-lb-cinamon/issues/538)) ([c7cc61e](https://github.com/CINEV/codex-lb-cinamon/commit/c7cc61e4a88467517912c901e483f09d0130e1bb))


### Documentation

* add e1ektr0 as a contributor for code, and test ([#581](https://github.com/CINEV/codex-lb-cinamon/issues/581)) ([26372cc](https://github.com/CINEV/codex-lb-cinamon/commit/26372cc273a45c07b84234799ae0da147e71c683))
* add Komzpa as a contributor for code ([#531](https://github.com/CINEV/codex-lb-cinamon/issues/531)) ([5bf5d94](https://github.com/CINEV/codex-lb-cinamon/commit/5bf5d944fc200833cec0f3b82391c3a3333396cb))

## [1.16.0](https://github.com/Soju06/codex-lb/compare/v1.15.0...v1.16.0) (2026-05-10)


### Features

* **accounts:** split compact quota row display ([#562](https://github.com/Soju06/codex-lb/issues/562)) ([9581fe7](https://github.com/Soju06/codex-lb/commit/9581fe7c65f025780943486757a0c8020d7b7917))
* add API key filter for dashboard request logs ([#497](https://github.com/Soju06/codex-lb/issues/497)) ([43cbdac](https://github.com/Soju06/codex-lb/commit/43cbdac318c3b84944f010c1bc8421b81a4cf605))
* **auth:** make dashboard session lifetime configurable ([#465](https://github.com/Soju06/codex-lb/issues/465)) ([386e0e9](https://github.com/Soju06/codex-lb/commit/386e0e93ca0bfb5d086e2a260c8e491c226f4f0a))
* **proxy:** add /backend-api/files upload protocol ([#515](https://github.com/Soju06/codex-lb/issues/515)) ([7ecb77a](https://github.com/Soju06/codex-lb/commit/7ecb77ae854591e1e6c4e50e785573c74b7ca68e))
* **proxy:** add OpenAI-compatible /v1/images API (gpt-image-2 via image_generation tool) ([#498](https://github.com/Soju06/codex-lb/issues/498)) ([359743d](https://github.com/Soju06/codex-lb/commit/359743d086e45b0b4ca14502d8d3fbfea628b939))
* **proxy:** make upstream response.create max bytes configurable via env var ([#476](https://github.com/Soju06/codex-lb/issues/476)) ([753c040](https://github.com/Soju06/codex-lb/commit/753c040dbd77634f6b281cbe4e1f1f6992fee1cf))


### Bug Fixes

* **api-limit:** Add fallback for api limit reset ([#475](https://github.com/Soju06/codex-lb/issues/475)) ([61386dc](https://github.com/Soju06/codex-lb/commit/61386dcc5d24147a46f30201fdb7d2879c9e8b9d))
* **auth:** preserve existing session expiry through TOTP and tighten hour input ([#511](https://github.com/Soju06/codex-lb/issues/511)) ([4b10807](https://github.com/Soju06/codex-lb/commit/4b1080730aa4bfd3ef9fd35b843ac0743bb6f8ae))
* **chat-completions:** normalize provider thinking aliases ([#424](https://github.com/Soju06/codex-lb/issues/424)) ([4419771](https://github.com/Soju06/codex-lb/commit/4419771c0c7791b20a899c07a65c74879c56f978))
* **db:** size background pool for burst traffic ([#563](https://github.com/Soju06/codex-lb/issues/563)) ([1e397e8](https://github.com/Soju06/codex-lb/commit/1e397e806de92a8eb7f8fbb9326ffdebdd75e6ea))
* **oauth:** make manual callback idempotent ([#481](https://github.com/Soju06/codex-lb/issues/481)) ([c72b68a](https://github.com/Soju06/codex-lb/commit/c72b68a74c9010a34e9503557f7fe027d6cfb922))
* **openspec:** satisfy strict purpose validation ([#552](https://github.com/Soju06/codex-lb/issues/552)) ([1d88236](https://github.com/Soju06/codex-lb/commit/1d882362bf9813488f1b2d9f40f32d67d491b453))
* **proxy:** reject `input_image.file_id` / `sediment://` with 400 `unsupported_input_image_format`, plus HTTP responses bridge hardening (close-code 1000 fail-fast classifier, payload-size HTTP transport auto-fallback, per-request bridge bypass for oversized payloads). The original inline-rewrite from #571 was narrowed in [#574](https://github.com/Soju06/codex-lb/pull/574) after upstream verification showed `input_image.file_id` is not an accepted shape on the Responses API. ([#571](https://github.com/Soju06/codex-lb/pull/571), [#574](https://github.com/Soju06/codex-lb/pull/574))
* **proxy:** load balancer filter ([#485](https://github.com/Soju06/codex-lb/issues/485)) ([b7b150d](https://github.com/Soju06/codex-lb/commit/b7b150d7bc91a375e65483dc896652d19d4595df))
* **proxy:** map unsupported reasoning effort 'minimal' to a supported value ([#494](https://github.com/Soju06/codex-lb/issues/494)) ([5278f84](https://github.com/Soju06/codex-lb/commit/5278f847c2dce72d7118761e152dc17f213b9854))
* **proxy:** pre-validate strict JSON schemas to surface invalid_json_schema ([#491](https://github.com/Soju06/codex-lb/issues/491)) ([#495](https://github.com/Soju06/codex-lb/issues/495)) ([ecc1bca](https://github.com/Soju06/codex-lb/commit/ecc1bcae17ad916684419a15ee440d475d21947d))
* **proxy:** retry transient stream timeouts ([#551](https://github.com/Soju06/codex-lb/issues/551)) ([77944c9](https://github.com/Soju06/codex-lb/commit/77944c93b61c516f205681e1b09bbba38c46f88e))
* **proxy:** return api-key limits from v1 usage ([#501](https://github.com/Soju06/codex-lb/issues/501)) ([694ec18](https://github.com/Soju06/codex-lb/commit/694ec180881cbd89c949e68d93e77fc4c9465a2d))
* **proxy:** use `DEFAULT_HOME_DIR` for oversized `response.create` dumps so non-container deploys (notably macOS `uv tool` / LaunchAgent installs) can write the debug dump path. Resolves [#556](https://github.com/Soju06/codex-lb/issues/556). ([#575](https://github.com/Soju06/codex-lb/pull/575))
* **proxy:** revert `slim oversized response.create history` from #560. The history-slimming approach conflicted with prompt-cache affinity, mis-trained the assistant on its own prior speech via the omission notice, and could break the WebSocket `previous_response_id` continuity. The portable dump-path slice from #560 was re-landed in #575; the broader design discussion is tracked in [#568](https://github.com/Soju06/codex-lb/issues/568). ([#569](https://github.com/Soju06/codex-lb/pull/569))
* **types:** clear existing ty diagnostics ([#517](https://github.com/Soju06/codex-lb/issues/517)) ([0cd5d4e](https://github.com/Soju06/codex-lb/commit/0cd5d4ebe49e4507e4aaa937c940f198e77ce7b0))


### Documentation

* add Komzpa as a contributor for code ([#531](https://github.com/Soju06/codex-lb/issues/531)) ([5bf5d94](https://github.com/Soju06/codex-lb/commit/5bf5d944fc200833cec0f3b82391c3a3333396cb))
* add mikabytes as a contributor for code, doc, and test ([#509](https://github.com/Soju06/codex-lb/issues/509)) ([22cc5f8](https://github.com/Soju06/codex-lb/commit/22cc5f8ef1e416ef6b374f484469edf4e5f24c0b))
* add rio-jeong as a contributor for code, bug, and test ([#492](https://github.com/Soju06/codex-lb/issues/492)) ([f1e2d90](https://github.com/Soju06/codex-lb/commit/f1e2d906f270a402a2c881885c51ae84fdc06fee))
* add stemirkhan as a contributor for bug ([#505](https://github.com/Soju06/codex-lb/issues/505)) ([7170b13](https://github.com/Soju06/codex-lb/commit/7170b1368070e0e9b5954d8a4da2c513f72f3442))
* add stemirkhan as a contributor for code, doc, and test ([#503](https://github.com/Soju06/codex-lb/issues/503)) ([dbda5c7](https://github.com/Soju06/codex-lb/commit/dbda5c74a188399190272b1a9a4c108a57678930))
* add tobwen as a contributor for code, test, and bug ([#489](https://github.com/Soju06/codex-lb/issues/489)) ([1ac1fe2](https://github.com/Soju06/codex-lb/commit/1ac1fe2f5771d6549e1e6c15a7add2ef38ac5912))

## [1.15.0](https://github.com/Soju06/codex-lb/compare/v1.14.1...v1.15.0) (2026-04-24)


### Features

* **proxy:** add GPT-5.5 and GPT-5.5 Pro model support ([#477](https://github.com/Soju06/codex-lb/issues/477)) ([9c2cd97](https://github.com/Soju06/codex-lb/commit/9c2cd972687ec717b53308b154ad1c0044391a87))

## [1.15.2](https://github.com/CINEV/codex-lb-cinamon/compare/v1.15.1...v1.15.2) (2026-04-29)


### Bug Fixes

* **proxy:** protect codex continuity fallback ([eb9caaf](https://github.com/CINEV/codex-lb-cinamon/commit/eb9caafe7d2108528335dfc873696a5a226ff060))
* **proxy:** protect codex continuity fallback ([1c9f7d3](https://github.com/CINEV/codex-lb-cinamon/commit/1c9f7d335fdaaedb31201d7cb5310e52e8892a72))

## [1.12.0](https://github.com/Soju06/codex-lb/compare/v1.11.0...v1.12.0) (2026-04-08)


### Features

* add accounts as pools for api to use ([#338](https://github.com/Soju06/codex-lb/issues/338)) ([659f7dc](https://github.com/Soju06/codex-lb/commit/659f7dcdb7156c6f384053d4734394da69ca0886))
* **config:** add model_context_window_overrides setting ([#340](https://github.com/Soju06/codex-lb/issues/340)) ([04da855](https://github.com/Soju06/codex-lb/commit/04da8553f764646bfcd52d087ea0a20a91c3995a))
* enable import-without-overwrite by default ([#362](https://github.com/Soju06/codex-lb/issues/362)) ([af9af6d](https://github.com/Soju06/codex-lb/commit/af9af6db3893e691842a8af43892adda4f9e9ccf))


### Bug Fixes

* **dashboard:** clarify donut usage breakdown ([#344](https://github.com/Soju06/codex-lb/issues/344)) ([87af885](https://github.com/Soju06/codex-lb/commit/87af8852c5d2e8bd3fdfe9d6e207745be7408c9c))
* **dashboard:** restore capacity-based usage donut totals ([#336](https://github.com/Soju06/codex-lb/issues/336)) ([1bcdcaa](https://github.com/Soju06/codex-lb/commit/1bcdcaacc1a51d3ce4f794b479383f6a9fe1158a))


### Documentation

* add comprehensive docstrings to select_account in logic.py ([#350](https://github.com/Soju06/codex-lb/issues/350)) ([36a4e7c](https://github.com/Soju06/codex-lb/commit/36a4e7cbd70fdb95d772d16aeded35ec1ae9a80d))
* add Daeroni as a contributor for doc ([#356](https://github.com/Soju06/codex-lb/issues/356)) ([15c4e54](https://github.com/Soju06/codex-lb/commit/15c4e54087089092478aaafe4bbfb6390fac0d84))
* add embogomolov as a contributor for code, and test ([#361](https://github.com/Soju06/codex-lb/issues/361)) ([d82cdf4](https://github.com/Soju06/codex-lb/commit/d82cdf4cdc8fd42ea5dfc3b43455ad857ab5421e))
* add Felix201209 as a contributor for code ([#360](https://github.com/Soju06/codex-lb/issues/360)) ([5e8cf21](https://github.com/Soju06/codex-lb/commit/5e8cf214f8e8ce8c516e15f7f3545cab6807aa7c))
* add Felix201209 as a contributor for doc ([#357](https://github.com/Soju06/codex-lb/issues/357)) ([6a7b8b2](https://github.com/Soju06/codex-lb/commit/6a7b8b27af6cc23b3f1a19802cc7b377489b2f49))

## [1.11.0](https://github.com/Soju06/codex-lb/compare/v1.10.1...v1.11.0) (2026-04-06)


### Features

* **accounts:** add refreshable browser OAuth link ([#316](https://github.com/Soju06/codex-lb/issues/316)) ([aeaf106](https://github.com/Soju06/codex-lb/commit/aeaf106a507b3b82ff305184ffae114faecf74f6))
* **dashboard:** add selectable overview timeframes ([#319](https://github.com/Soju06/codex-lb/issues/319)) ([d8d812f](https://github.com/Soju06/codex-lb/commit/d8d812f57f1463d8512dd6ac659f446e76bc5f94))
* deterministic failover & soft drain ([#328](https://github.com/Soju06/codex-lb/issues/328)) ([fc77c76](https://github.com/Soju06/codex-lb/commit/fc77c7604af6ed4d621fd4e7a8435507e0f3e21e))
* **v1-usage:** add credit-based Codex override windows ([#304](https://github.com/Soju06/codex-lb/issues/304)) ([6c3c556](https://github.com/Soju06/codex-lb/commit/6c3c5564c530d0670995577882038a00f5b46f8b))


### Bug Fixes

* **api:** for /backend-api/codex/model, return it in codex format ([#331](https://github.com/Soju06/codex-lb/issues/331)) ([c141a8a](https://github.com/Soju06/codex-lb/commit/c141a8ac963ebe25ed8e82ed7b9ab3057e4c083a))
* avoid Windows startup crash in memory monitor and add manual reg… ([#329](https://github.com/Soju06/codex-lb/issues/329)) ([5c2d26e](https://github.com/Soju06/codex-lb/commit/5c2d26e8f11abf5bdaed13aed7904f097cc18e3f))
* **dashboard:** show remaining totals in usage donuts ([#303](https://github.com/Soju06/codex-lb/issues/303)) ([7827941](https://github.com/Soju06/codex-lb/commit/78279417c1557753a93001a6586997fb204fe18d))
* **helm:** disable service links and use fully qualified image names ([#321](https://github.com/Soju06/codex-lb/issues/321)) ([c54edee](https://github.com/Soju06/codex-lb/commit/c54edeefa00b4271f6f80270462bb8ddcade5e92))
* **helm:** one-click external database setup improvements ([#322](https://github.com/Soju06/codex-lb/issues/322)) ([4c3c945](https://github.com/Soju06/codex-lb/commit/4c3c9453a48aaced5e023447446da00d6843c7cf))


### Documentation

* add Daltonganger as a contributor for bug ([#332](https://github.com/Soju06/codex-lb/issues/332)) ([1c8a7e5](https://github.com/Soju06/codex-lb/commit/1c8a7e5633b55dadeb8ccb2ae3791a23787b3a9f))
* add L1st3r as a contributor for bug ([#335](https://github.com/Soju06/codex-lb/issues/335)) ([05a77d8](https://github.com/Soju06/codex-lb/commit/05a77d857ec90b101feee675a1dfb20f556b0188))
* add mhughdo as a contributor for code, and test ([#333](https://github.com/Soju06/codex-lb/issues/333)) ([0fc01f6](https://github.com/Soju06/codex-lb/commit/0fc01f676fe826f6228140c529e75ca1e31076c2))
* add salwinh as a contributor for code, and test ([#334](https://github.com/Soju06/codex-lb/issues/334)) ([7fed142](https://github.com/Soju06/codex-lb/commit/7fed14284a0c6025cf615856b6ca123b2d8cf463))

## [1.10.1](https://github.com/Soju06/codex-lb/compare/v1.10.0...v1.10.1) (2026-04-03)


### Bug Fixes

* **ci:** lowercase Trivy image-ref and bump all actions to latest ([3b94de4](https://github.com/Soju06/codex-lb/commit/3b94de4457a93b2ff220a33ea9b7a164c02e0b37))
* **ci:** use exact tag v8.0.0 for setup-uv (no v8 major tag exists) ([c657c91](https://github.com/Soju06/codex-lb/commit/c657c91bf26b4d99bb783e7e4f3b4268d0a4028f))


### Documentation

* add L1st3r as a contributor for code, and test ([#318](https://github.com/Soju06/codex-lb/issues/318)) ([d0ff5a7](https://github.com/Soju06/codex-lb/commit/d0ff5a71212132f64ecf4e3b594059a7d648f45a))
* external DB secrets guide, ServiceMonitor alternatives, production deployment guide ([#315](https://github.com/Soju06/codex-lb/issues/315)) ([8d558f6](https://github.com/Soju06/codex-lb/commit/8d558f6a9b3beafcbca36c92ba694f099c9ca115))

## [1.10.0](https://github.com/Soju06/codex-lb/compare/v1.9.0...v1.10.0) (2026-04-02)


### Features

* **helm:** expose all caching subsystems in chart values ([cd39073](https://github.com/Soju06/codex-lb/commit/cd39073c4f2b9f086a00bf84c9cd80af27cc194a))


### Bug Fixes

* **ci:** lowercase GHCR owner in Helm OCI push ([03c14f6](https://github.com/Soju06/codex-lb/commit/03c14f61e132c81f483dd21f977e7f0dd32be083))
* **helm:** harden defaults for multi-replica and streaming deployments ([70a348e](https://github.com/Soju06/codex-lb/commit/70a348e80bc6f46ec616e3ff497f056277049156))
* **helm:** improve cache locality and align backpressure with capacity ([6c17201](https://github.com/Soju06/codex-lb/commit/6c1720189416da41a5c7c979ec8b523f0218c46a))


### Documentation

* **helm:** replace local-path install with OCI registry commands ([55ddeb7](https://github.com/Soju06/codex-lb/commit/55ddeb7300d6a1780ec748b3e1d940613333ab69))

## [1.9.0](https://github.com/Soju06/codex-lb/compare/v1.8.3...v1.9.0) (2026-04-02)


### Features

* add a "API" page to see details of the API keys ([#269](https://github.com/Soju06/codex-lb/issues/269)) ([938c734](https://github.com/Soju06/codex-lb/commit/938c7344b2cfc62ecbc7519abf60b04f9ddf9fcd))
* add stickysession selection box to select multiple sessions too be deleted ([#286](https://github.com/Soju06/codex-lb/issues/286)) ([c64b860](https://github.com/Soju06/codex-lb/commit/c64b8604afcf3afcdac040fed823a51b95cb4955))
* **api-keys:** add per-key enforced service tier ([#288](https://github.com/Soju06/codex-lb/issues/288)) ([cc851a5](https://github.com/Soju06/codex-lb/commit/cc851a5eedf8375f4df7e2a909d28b48023f08c4))
* **api-keys:** add self-service /v1/usage endpoint ([#295](https://github.com/Soju06/codex-lb/issues/295)) ([652f600](https://github.com/Soju06/codex-lb/commit/652f60080109ea1ac25f4a0d2bc5124f9587ca08))
* **balancer:** add capacity-weighted routing for tier-aware load distribution ([#297](https://github.com/Soju06/codex-lb/issues/297)) ([fa8eab4](https://github.com/Soju06/codex-lb/commit/fa8eab4eb6844e9b737d705327ea6b926cc49419))


### Bug Fixes

* **balancer:** trust usage data over stale runtime_reset for early quota resets ([#289](https://github.com/Soju06/codex-lb/issues/289)) ([a269b37](https://github.com/Soju06/codex-lb/commit/a269b3769a6a115921e3d54f9b32b535f9bb2f2b))
* **chat:** prevent duplicated tool-call arguments in chat completions ([#287](https://github.com/Soju06/codex-lb/issues/287)) ([41ceb4f](https://github.com/Soju06/codex-lb/commit/41ceb4f24d07cacfff9f8b21dad50c4458414278))
* **deploy:** restore Docker auto-migration, cache/rate-limiter fixes, Helm/K8s CI/CD ([#274](https://github.com/Soju06/codex-lb/issues/274)) ([16391ae](https://github.com/Soju06/codex-lb/commit/16391aec7c76096fb20218e353731d44a9cbc4f8))
* **docker:** resolve distroless ARM64 build by detecting arch-specific lib paths ([b21d4bd](https://github.com/Soju06/codex-lb/commit/b21d4bd498714aac3ab785c361008a3f2238b688))
* prevent sticky session thrashing when all accounts exceed budget threshold ([#279](https://github.com/Soju06/codex-lb/issues/279)) ([502db37](https://github.com/Soju06/codex-lb/commit/502db371232d6fc905985c140b0b80d96472aaea))
* **proxy:** resolve k8s-era TC regressions ([#290](https://github.com/Soju06/codex-lb/issues/290)) ([020784a](https://github.com/Soju06/codex-lb/commit/020784a38b731381e05e4c8fef7505525c60fd84))
* **tests:** stabilize proxy retry logging assertions ([0f86737](https://github.com/Soju06/codex-lb/commit/0f867376df870516551416b3df650adedd85ed05))


### Performance Improvements

* **usage:** replace DISTINCT ON with lateral join in latest_by_account ([#277](https://github.com/Soju06/codex-lb/issues/277)) ([8be87a6](https://github.com/Soju06/codex-lb/commit/8be87a64f1576f770b11de171f947b68e74420b3))


### Documentation

* add Daltonganger as a contributor for code, and test ([#298](https://github.com/Soju06/codex-lb/issues/298)) ([7f17d72](https://github.com/Soju06/codex-lb/commit/7f17d72ecfd26aa20877c4d6ec37f71417e48897))

## [1.8.3](https://github.com/Soju06/codex-lb/compare/v1.8.2...v1.8.3) (2026-03-30)


### Bug Fixes

* **proxy:** complete cache-locality fix for prompt cache hit rate restoration ([#273](https://github.com/Soju06/codex-lb/issues/273)) ([aa971fa](https://github.com/Soju06/codex-lb/commit/aa971fa96c6789f079aa98c67205e1263f3c7598))

## [1.8.2](https://github.com/Soju06/codex-lb/compare/v1.8.1...v1.8.2) (2026-03-26)


### Bug Fixes

* **api-keys:** normalize timezone-aware expirations before persistence ([#249](https://github.com/Soju06/codex-lb/issues/249)) ([abf96f8](https://github.com/Soju06/codex-lb/commit/abf96f85a265cf3d45eed7f47ecfb10de6979b01))
* graph do not render when primary = [], even secondary have data ([#253](https://github.com/Soju06/codex-lb/issues/253)) ([98434c4](https://github.com/Soju06/codex-lb/commit/98434c491698747c5c0dbb69f2f4c471affdd86a))
* **middleware:** handle disconnects and body read failures ([#263](https://github.com/Soju06/codex-lb/issues/263)) ([8188c31](https://github.com/Soju06/codex-lb/commit/8188c31110b7e284a97d83777728ed54b7e83593))


### Documentation

* add huzky-v as a contributor for question, and maintenance ([#257](https://github.com/Soju06/codex-lb/issues/257)) ([337db69](https://github.com/Soju06/codex-lb/commit/337db69b7a138f43cae4dd857dd08196d06e4cff))
* add yigitkonur as a contributor for bug, and code ([#258](https://github.com/Soju06/codex-lb/issues/258)) ([a5ffdf3](https://github.com/Soju06/codex-lb/commit/a5ffdf307f161672f74bd44e6ccbd286bbbe8faa))

## [1.8.1](https://github.com/Soju06/codex-lb/compare/v1.8.0...v1.8.1) (2026-03-22)


### Documentation

* add ink-splatters as a contributor for code, and bug ([#247](https://github.com/Soju06/codex-lb/issues/247)) ([eb968b9](https://github.com/Soju06/codex-lb/commit/eb968b9d53b8fdd856f36d07714c93b4eb7dd61f))

## [1.8.0](https://github.com/Soju06/codex-lb/compare/v1.7.0...v1.8.0) (2026-03-21)


### Features

* **proxy:** split service tier logging and pricing ([#238](https://github.com/Soju06/codex-lb/issues/238)) ([04c9304](https://github.com/Soju06/codex-lb/commit/04c93044aa061051d0ea404795078e44b6241360))


### Bug Fixes

* fail closed when HTTP bridge loses previous_response continuity ([#239](https://github.com/Soju06/codex-lb/issues/239)) ([a87e0ca](https://github.com/Soju06/codex-lb/commit/a87e0ca342981263d33668d97eac5cdc9c86842b))
* improve native Codex websocket parity ([#242](https://github.com/Soju06/codex-lb/issues/242)) ([fb0e759](https://github.com/Soju06/codex-lb/commit/fb0e7595f46984d26c97a761dd339af4ade83223))
* **proxy:** support desktop Codex originators ([#240](https://github.com/Soju06/codex-lb/issues/240)) ([ac38bd1](https://github.com/Soju06/codex-lb/commit/ac38bd186dd4eb51947ad9b7e83ecb6addd6ca99))
* tighten dashboard database indexes ([#241](https://github.com/Soju06/codex-lb/issues/241)) ([f2469a2](https://github.com/Soju06/codex-lb/commit/f2469a2b8102dd1efe7f4948ee1e82d461f30e93))

## [1.7.0](https://github.com/Soju06/codex-lb/compare/v1.6.3...v1.7.0) (2026-03-20)


### Features

* add GPT-5.4 mini pricing ([#234](https://github.com/Soju06/codex-lb/issues/234)) ([3236119](https://github.com/Soju06/codex-lb/commit/323611940387057cc70e474219240c225b40d33b))


### Bug Fixes

* bridge backend HTTP responses through websocket sessions ([#236](https://github.com/Soju06/codex-lb/issues/236)) ([2723d97](https://github.com/Soju06/codex-lb/commit/2723d9720af184cd875de8ca3d5ed8d89171c30c))

## [1.6.3](https://github.com/Soju06/codex-lb/compare/v1.6.2...v1.6.3) (2026-03-19)


### Bug Fixes

* preserve v1 responses session continuity over HTTP ([#232](https://github.com/Soju06/codex-lb/issues/232)) ([7ba5b75](https://github.com/Soju06/codex-lb/commit/7ba5b751f90e619bb396afa1ed650d837bba9308))

## [1.6.2](https://github.com/Soju06/codex-lb/compare/v1.6.1...v1.6.2) (2026-03-19)


### Bug Fixes

* **proxy:** restore token cache affinity routing ([#228](https://github.com/Soju06/codex-lb/issues/228)) ([ab8f820](https://github.com/Soju06/codex-lb/commit/ab8f820f2e8adbfb0c1f9ebc43c17acd4333441c))

## [1.6.1](https://github.com/Soju06/codex-lb/compare/v1.6.0...v1.6.1) (2026-03-18)


### Bug Fixes

* clarify account quota labels and dashboard masking ([#215](https://github.com/Soju06/codex-lb/issues/215)) ([ec00fa8](https://github.com/Soju06/codex-lb/commit/ec00fa84071976a5b6484bb819975dbd1ff5d4f2))
* **dashboard:** cap primary donut remaining by secondary absolute credits ([#222](https://github.com/Soju06/codex-lb/issues/222)) ([d0e286a](https://github.com/Soju06/codex-lb/commit/d0e286af931e1d7bbe7c62583857c34ae611b57d))
* **proxy:** add transient 500 retry with same-account affinity and failover ([#225](https://github.com/Soju06/codex-lb/issues/225)) ([c1ed531](https://github.com/Soju06/codex-lb/commit/c1ed531a3d58003e00ca5dff562bc761ef93fc48))
* **proxy:** preserve sticky sessions during temporary account unavailability ([#226](https://github.com/Soju06/codex-lb/issues/226)) ([68b3bc0](https://github.com/Soju06/codex-lb/commit/68b3bc08a24fbb5914776a689996950ce29f502f))


### Documentation

* add minpeter as a contributor for code, and test ([#223](https://github.com/Soju06/codex-lb/issues/223)) ([3b2c1d4](https://github.com/Soju06/codex-lb/commit/3b2c1d406d2aaff5e9b941d89169dfad8f5e4002))

## [1.6.0](https://github.com/Soju06/codex-lb/compare/v1.5.3...v1.6.0) (2026-03-18)


### Features

* **proxy:** improve token cache affinity for codex and v1/responses endpoints ([#220](https://github.com/Soju06/codex-lb/issues/220)) ([dfc3aa7](https://github.com/Soju06/codex-lb/commit/dfc3aa714e0ec8ae4b6443abc262795875926320))


### Bug Fixes

* move the trend back to secondary instead of primary for free accounts ([#190](https://github.com/Soju06/codex-lb/issues/190)) ([944ea93](https://github.com/Soju06/codex-lb/commit/944ea93db600b004e1ff8df29397e47114af65b9))
* the account page select param is not respected ([#198](https://github.com/Soju06/codex-lb/issues/198)) ([6036184](https://github.com/Soju06/codex-lb/commit/6036184af2696dadc157bc6590bcc9e95d183177))

## [1.5.3](https://github.com/Soju06/codex-lb/compare/v1.5.2...v1.5.3) (2026-03-13)


### Bug Fixes

* **proxy:** match Codex CLI header fingerprint for transcribe upstream requests ([#199](https://github.com/Soju06/codex-lb/issues/199)) ([2a89631](https://github.com/Soju06/codex-lb/commit/2a8963143515da25bf718ede913fac14dbd918ee))


### Documentation

* add huzky-v as a contributor for code, and bug ([#201](https://github.com/Soju06/codex-lb/issues/201)) ([d1410c6](https://github.com/Soju06/codex-lb/commit/d1410c60a99e8b36c2464412c0e1b5db50f01914))

## [1.5.2](https://github.com/Soju06/codex-lb/compare/v1.5.1...v1.5.2) (2026-03-13)


### Bug Fixes

* **proxy:** close stream immediately after terminal SSE events ([#196](https://github.com/Soju06/codex-lb/issues/196)) ([dcf1ae3](https://github.com/Soju06/codex-lb/commit/dcf1ae3675346d75b571a29644c2722f776dc436))

## [1.5.1](https://github.com/Soju06/codex-lb/compare/v1.5.0...v1.5.1) (2026-03-13)


### Bug Fixes

* **proxy:** raise timeout defaults and remove getattr anti-pattern ([#193](https://github.com/Soju06/codex-lb/issues/193)) ([77dbc8a](https://github.com/Soju06/codex-lb/commit/77dbc8a123c5ef3db122923d3a80d3e5b5e86ce2))

## [1.5.0](https://github.com/Soju06/codex-lb/compare/v1.4.1...v1.5.0) (2026-03-13)


### Features

* **frontend:** add privacy email blur toggle ([#180](https://github.com/Soju06/codex-lb/issues/180)) ([356edcb](https://github.com/Soju06/codex-lb/commit/356edcbb7f0624e71a10035315b71577c02e73d3))
* **proxy:** add upstream websocket transport control ([#189](https://github.com/Soju06/codex-lb/issues/189)) ([fb6b6cf](https://github.com/Soju06/codex-lb/commit/fb6b6cf616319fc4b72b0200e31499c84cb5c34a))
* **responses:** add websocket transport and request log tracing ([#169](https://github.com/Soju06/codex-lb/issues/169)) ([ceb1746](https://github.com/Soju06/codex-lb/commit/ceb17465d12186e19bff4e9ea984e482dd109f8b))


### Bug Fixes

* **proxy:** decouple stream duration from proxy request budget ([#187](https://github.com/Soju06/codex-lb/issues/187)) ([aa65e97](https://github.com/Soju06/codex-lb/commit/aa65e97d6f9f2c5014e4d032a7d81b3e8af8d618))
* **proxy:** preserve dedicated responses compact contract ([#175](https://github.com/Soju06/codex-lb/issues/175)) ([7442743](https://github.com/Soju06/codex-lb/commit/7442743662c9a6889507d339adebf0388d9761e6))
* **ui:** the label color in the trend does not show on dark mode ([#188](https://github.com/Soju06/codex-lb/issues/188)) ([8e62c4a](https://github.com/Soju06/codex-lb/commit/8e62c4ad724005df414cb7fa06becda00da8e807))


### Documentation

* add flokosti96 as a contributor for code, and test ([#192](https://github.com/Soju06/codex-lb/issues/192)) ([c2b105a](https://github.com/Soju06/codex-lb/commit/c2b105a3e545838e6b791692782c49f767e77647))

## [1.4.1](https://github.com/Soju06/codex-lb/compare/v1.4.0...v1.4.1) (2026-03-12)


### Bug Fixes

* **db:** fail fast on startup schema drift ([#174](https://github.com/Soju06/codex-lb/issues/174)) ([b7086b9](https://github.com/Soju06/codex-lb/commit/b7086b9f79f63d99d103ba6bf952f97b20137bb4))
* **proxy:** add sticky session controls and cleanup ([#176](https://github.com/Soju06/codex-lb/issues/176)) ([1116b3f](https://github.com/Soju06/codex-lb/commit/1116b3f73c54161b55e99dbd66cba1a189d67197))
* **proxy:** canonicalize additional quota routing ([#182](https://github.com/Soju06/codex-lb/issues/182)) ([b33264f](https://github.com/Soju06/codex-lb/commit/b33264f8d44f8619d8ba0fcbf763f064390ec1e3))


### Documentation

* add defin85 as a contributor for bug, and test ([#184](https://github.com/Soju06/codex-lb/issues/184)) ([ecad9e4](https://github.com/Soju06/codex-lb/commit/ecad9e4ae3c0346b9f5dad5fb59f00146f5aa2d9))

## [1.4.0](https://github.com/Soju06/codex-lb/compare/v1.3.2...v1.4.0) (2026-03-11)


### Features

* **proxy:** bound request latency across proxy paths ([#178](https://github.com/Soju06/codex-lb/issues/178)) ([3ca7124](https://github.com/Soju06/codex-lb/commit/3ca71249b20971f0f9d3ab86fe45d8d5bbf2ccaa))


### Bug Fixes

* **proxy:** route gated models by additional usage ([#173](https://github.com/Soju06/codex-lb/issues/173)) ([73bf90c](https://github.com/Soju06/codex-lb/commit/73bf90cc477628e780a95c5e22c09406f3d7c62d))

## [1.3.2](https://github.com/Soju06/codex-lb/compare/v1.3.1...v1.3.2) (2026-03-10)


### Bug Fixes

* **db:** add migration to normalize postgresql enum value casing ([#170](https://github.com/Soju06/codex-lb/issues/170)) ([e597fd6](https://github.com/Soju06/codex-lb/commit/e597fd6af983481acfdbe489bbd73bb39a2d6b7c))

## [1.3.1](https://github.com/Soju06/codex-lb/compare/v1.3.0...v1.3.1) (2026-03-10)


### Bug Fixes

* **proxy:** avoid refresh blocking and dedupe stale refreshes ([#162](https://github.com/Soju06/codex-lb/issues/162)) ([3b2fbd5](https://github.com/Soju06/codex-lb/commit/3b2fbd526711dee3eb09a60321a8972fe33baefd))
* **proxy:** decouple usage refresh from request selection ([#155](https://github.com/Soju06/codex-lb/issues/155)) ([dddd961](https://github.com/Soju06/codex-lb/commit/dddd961555727fa529b16750bc65eea49e6bbef8))
* safe line rendering, additional quotas relocation, and screenshot updates ([#166](https://github.com/Soju06/codex-lb/issues/166)) ([a1c788d](https://github.com/Soju06/codex-lb/commit/a1c788d612860c23eafe75a75d5ebdba5dc3ef52))


### Documentation

* add defin85 as a contributor for code ([#168](https://github.com/Soju06/codex-lb/issues/168)) ([703a2c9](https://github.com/Soju06/codex-lb/commit/703a2c92fb97fa408f057c8152dca805177d9fa1))

## [1.3.0](https://github.com/Soju06/codex-lb/compare/v1.2.0...v1.3.0) (2026-03-10)


### Features

* additional rate limits (Spark quotas), EWMA depletion indicator, and quotas UI ([#151](https://github.com/Soju06/codex-lb/issues/151)) ([13cc1ce](https://github.com/Soju06/codex-lb/commit/13cc1cee7ac19c032e9ffbdef820d02b4e400573))
* **db:** optimize SQLite startup and query paths ([#145](https://github.com/Soju06/codex-lb/issues/145)) ([316e9b6](https://github.com/Soju06/codex-lb/commit/316e9b69ee250d4b1af84eb360d297f7e99b932d))
* **proxy:** add upstream request tracing ([#144](https://github.com/Soju06/codex-lb/issues/144)) ([c530d24](https://github.com/Soju06/codex-lb/commit/c530d248dd268abb0466ddba55abbc8176c99dbb))


### Bug Fixes

* **proxy:** add request logging to compact and transcribe paths ([#153](https://github.com/Soju06/codex-lb/issues/153)) ([368853a](https://github.com/Soju06/codex-lb/commit/368853a87efaede5cd8ae826fb67f6dd7c5fc8f6))
* **proxy:** align compact retry account header after refresh ([#150](https://github.com/Soju06/codex-lb/issues/150)) ([b7aaef0](https://github.com/Soju06/codex-lb/commit/b7aaef03901fcf618a1dcded2aa6b19ef4c863bd))
* **proxy:** match Codex CLI compact timeout defaults ([#160](https://github.com/Soju06/codex-lb/issues/160)) ([799791c](https://github.com/Soju06/codex-lb/commit/799791cd4bb52211bfd442aa9334a845a4d65014))
* **proxy:** preserve v1 prompt cache affinity ([#161](https://github.com/Soju06/codex-lb/issues/161)) ([855c92e](https://github.com/Soju06/codex-lb/commit/855c92e03810c5adf9cf476325e41df22991a37a))
* **proxy:** scope codex session routing affinity ([#143](https://github.com/Soju06/codex-lb/issues/143)) ([28411b2](https://github.com/Soju06/codex-lb/commit/28411b2ef8a913eb92f13146cb7882921904045d))
* **proxy:** skip error backoff for transient upstream 5xx errors ([#152](https://github.com/Soju06/codex-lb/issues/152)) ([9819c0b](https://github.com/Soju06/codex-lb/commit/9819c0babb3796659ed86b62d673a8172cf185d7))


### Documentation

* add aaiyer as a contributor for bug, code, and test ([#149](https://github.com/Soju06/codex-lb/issues/149)) ([270d152](https://github.com/Soju06/codex-lb/commit/270d152fb017b1d8df1a732c19afca29b128c57b))
* **agents:** remove invalid deployment topology ([165d221](https://github.com/Soju06/codex-lb/commit/165d2216ddcacda237180c3c8dd81bff80225d14))
* **readme:** update opencode provider setup ([064efd9](https://github.com/Soju06/codex-lb/commit/064efd905b118e69b23a59eea2214c0c716f5083))

## [1.2.0](https://github.com/Soju06/codex-lb/compare/v1.1.1...v1.2.0) (2026-03-08)


### Features

* add manual OAuth callback URL paste for remote server deployments ([#136](https://github.com/Soju06/codex-lb/issues/136)) ([7651336](https://github.com/Soju06/codex-lb/commit/7651336a4ab867e06784f6b307666e5488dab259))
* enforce model/effort per API key and add real usage+cost visibility in settings; fixes; layout ([#135](https://github.com/Soju06/codex-lb/issues/135)) ([f014136](https://github.com/Soju06/codex-lb/commit/f014136fc9cf3c63cf6a1567c7f7f0967fb9af7a))
* **proxy:** support service_tier forwarding ([#137](https://github.com/Soju06/codex-lb/issues/137)) ([8bde95a](https://github.com/Soju06/codex-lb/commit/8bde95a33445149a4310a71f10d494d1c62bf7fc))


### Bug Fixes

* **app-header:** apply desktop nav pill classes to NavLink ([#133](https://github.com/Soju06/codex-lb/issues/133)) ([c6b801e](https://github.com/Soju06/codex-lb/commit/c6b801e3e5c8ce90326f6c145c8914d1f036fe0e))
* **proxy:** finalize v1 responses non-stream reservations ([#146](https://github.com/Soju06/codex-lb/issues/146)) ([a8ebe6c](https://github.com/Soju06/codex-lb/commit/a8ebe6cd6612417d90750b9c72d0046875bc1f1d))
* **proxy:** preserve v1 response reasoning output ([#138](https://github.com/Soju06/codex-lb/issues/138)) ([0327279](https://github.com/Soju06/codex-lb/commit/032727968628610617b72925d7c76f68c9c8ef67))
* **usage:** avoid deactivating accounts on usage 403 ([#147](https://github.com/Soju06/codex-lb/issues/147)) ([fec1256](https://github.com/Soju06/codex-lb/commit/fec1256010ffb0b7318e9eef933345b0fcd6023a))


### Documentation

* add mws-weekend-projects as a contributor for code, and test ([#141](https://github.com/Soju06/codex-lb/issues/141)) ([7cbb181](https://github.com/Soju06/codex-lb/commit/7cbb181da441ec38251b9d370fe5c1d6050cd921))
* add quangdo126 as a contributor for code, and test ([#142](https://github.com/Soju06/codex-lb/issues/142)) ([b44f63d](https://github.com/Soju06/codex-lb/commit/b44f63d16b984ad7c420607aa65711f16c63bb21))
* add xCatalitY as a contributor for code, and test ([#139](https://github.com/Soju06/codex-lb/issues/139)) ([c68231b](https://github.com/Soju06/codex-lb/commit/c68231bdfbd5ed5ebef7ed394981318505f8969b))

## [1.1.1](https://github.com/Soju06/codex-lb/compare/v1.1.0...v1.1.1) (2026-03-03)


### Bug Fixes

* **responses:** strip unsupported safety_identifier before upstream ([#130](https://github.com/Soju06/codex-lb/issues/130)) ([528e7fd](https://github.com/Soju06/codex-lb/commit/528e7fd85152f8e6f39c5551b5ae085e90935356))

## [1.1.0](https://github.com/Soju06/codex-lb/compare/v1.0.4...v1.1.0) (2026-03-02)


### Features

* **codex-review:** add re-review loop with convergence termination ([a4e0832](https://github.com/Soju06/codex-lb/commit/a4e08326ebe8e5431d9a012e4608e75811add0c6))
* **db:** adopt timestamp alembic revisions with auto remap ([#123](https://github.com/Soju06/codex-lb/issues/123)) ([57e840c](https://github.com/Soju06/codex-lb/commit/57e840c37e9327726ddf9fc5acad10a0e12b670e))
* migrate firewall module and React dashboard page ([#84](https://github.com/Soju06/codex-lb/issues/84)) ([a35348a](https://github.com/Soju06/codex-lb/commit/a35348a0e5b1b40c573aa24aaf866b7e74dd4042))
* **proxy:** add transcription compatibility routes ([#111](https://github.com/Soju06/codex-lb/issues/111)) ([0b591df](https://github.com/Soju06/codex-lb/commit/0b591df57989b74004a345cb2ced630b8241b9f2))


### Bug Fixes

* **app-routing:** add routing strategy setting and fix true round-robin runtime rotation ([#100](https://github.com/Soju06/codex-lb/issues/100)) ([df4cceb](https://github.com/Soju06/codex-lb/commit/df4cceb695e20d629d2b2655e547ccff4df87fae))
* **oauth-ui:** start device polling immediately after device start ([#108](https://github.com/Soju06/codex-lb/issues/108)) ([faf3535](https://github.com/Soju06/codex-lb/commit/faf3535de528b3cd45ce5544540becf44c72ff37))
* **responses:** strip unsupported prompt params before upstream ([#128](https://github.com/Soju06/codex-lb/issues/128)) ([0f50c6f](https://github.com/Soju06/codex-lb/commit/0f50c6f11d5739b5e66badec45d50391f69c2760))
* **round-robin:** harden runtime locking and per-app balancer state ([#112](https://github.com/Soju06/codex-lb/issues/112)) ([7e5df87](https://github.com/Soju06/codex-lb/commit/7e5df8799598d4ef22efc1ff87ac40aaf258725d))


### Documentation

* add DOCaCola as a contributor for bug, test, and doc ([#106](https://github.com/Soju06/codex-lb/issues/106)) ([8fdab9f](https://github.com/Soju06/codex-lb/commit/8fdab9ff301038d1d4a9c6822ad1f66db1cfd498))
* add ink-splatters as a contributor for doc ([#122](https://github.com/Soju06/codex-lb/issues/122)) ([2607cb9](https://github.com/Soju06/codex-lb/commit/2607cb90beb8bd7c0e201b9d32af271e8e9cdc98))
* add joeblack2k as a contributor for code, bug, and test ([#109](https://github.com/Soju06/codex-lb/issues/109)) ([6dfb74a](https://github.com/Soju06/codex-lb/commit/6dfb74a6cde036f341056b25f91f249ebfa02f16))
* add pcy06 as a contributor for code, and test ([#121](https://github.com/Soju06/codex-lb/issues/121)) ([4290fb0](https://github.com/Soju06/codex-lb/commit/4290fb0eb85a8d1102819e4194a02a0bc6c1200f))
* fix codex defaults / add migration note ([#120](https://github.com/Soju06/codex-lb/issues/120)) ([6bfab1c](https://github.com/Soju06/codex-lb/commit/6bfab1c2bc8b2701b2a36f867bdb6975aaf56ac9))
* **git-workflow:** update PR title guidelines and workflow steps ([d88ab86](https://github.com/Soju06/codex-lb/commit/d88ab86e3a655c0d928cc35b275f7a5c1d0bf2dc))
* **git-workflow:** update pushing guidelines for forked PRs ([ef29f71](https://github.com/Soju06/codex-lb/commit/ef29f712ec00358977f10a64e5a4f6a1db3bceff))

## [1.0.4](https://github.com/Soju06/codex-lb/compare/v1.0.3...v1.0.4) (2026-02-20)


### Bug Fixes

* handle free-plan quota quirks (weekly-only windows, stale plan type after upgrade) ([#71](https://github.com/Soju06/codex-lb/issues/71)) ([c5f6ea8](https://github.com/Soju06/codex-lb/commit/c5f6ea8eabe7cbfb81f0f75bac46d398b46bb9d2))
* **proxy:** align message coercion and response mapping with OpenAI API spec ([#87](https://github.com/Soju06/codex-lb/issues/87)) ([d9fee7a](https://github.com/Soju06/codex-lb/commit/d9fee7a2a283c52438a18d9692ed20a7be69623c))
* **proxy:** OpenCode compatibility and better usage ([#86](https://github.com/Soju06/codex-lb/issues/86)) ([c243630](https://github.com/Soju06/codex-lb/commit/c2436307ac59d199aa48b1b1a29c98be6bc9debd))
* support non-overwrite import for same account across multiple team plans ([#72](https://github.com/Soju06/codex-lb/issues/72)) ([82e7cc7](https://github.com/Soju06/codex-lb/commit/82e7cc750a35fe5b200ade2ca210051dfee140ae))


### Documentation

* add azkore as a contributor for code, bug, and test ([#90](https://github.com/Soju06/codex-lb/issues/90)) ([5c3cbb7](https://github.com/Soju06/codex-lb/commit/5c3cbb77c19e2e792784cf1d459507fc8225b003))
* add hhsw2015 as a contributor for bug ([#91](https://github.com/Soju06/codex-lb/issues/91)) ([3262d50](https://github.com/Soju06/codex-lb/commit/3262d5083d43460e684b2acd09a2504bf4501b21))
* add JordxnBN as a contributor for code, bug, and test ([#92](https://github.com/Soju06/codex-lb/issues/92)) ([537b3cf](https://github.com/Soju06/codex-lb/commit/537b3cf9feb85d538202a6b4fd68b81b1a5b800c))

## [1.0.3](https://github.com/Soju06/codex-lb/compare/v1.0.2...v1.0.3) (2026-02-18)


### Bug Fixes

* **proxy:** expose models regardless of supported_in_api ([#82](https://github.com/Soju06/codex-lb/issues/82)) ([aac71d9](https://github.com/Soju06/codex-lb/commit/aac71d9d29632e7d1cc290d980b5b7f178f0dcc3))

## [1.0.2](https://github.com/Soju06/codex-lb/compare/v1.0.1...v1.0.2) (2026-02-18)


### Bug Fixes

* **proxy:** strip forwarded identity headers before upstream ([#78](https://github.com/Soju06/codex-lb/issues/78)) ([9d39486](https://github.com/Soju06/codex-lb/commit/9d394868ba8970809ed836e255bf59ece69e85fb))

## [1.0.1](https://github.com/Soju06/codex-lb/compare/v1.0.0...v1.0.1) (2026-02-18)


### Bug Fixes

* **deps:** add brotli for upstream response decompression ([#77](https://github.com/Soju06/codex-lb/issues/77)) ([52026f2](https://github.com/Soju06/codex-lb/commit/52026f28a1d54069ca9cfa30eea99aee383340e5))


### Documentation

* standardize logo sizes and alignment in README client section ([7e53625](https://github.com/Soju06/codex-lb/commit/7e536252ab10a3cc69349665d70a7fc3107a04c4))
* update README to enhance client logo visibility and improve layout ([2b9851a](https://github.com/Soju06/codex-lb/commit/2b9851afe36889e4ba5211a69d5a6dc19f80716c))

## [1.0.0](https://github.com/Soju06/codex-lb/compare/v0.6.0...v1.0.0) (2026-02-18)


### ⚠ BREAKING CHANGES

* hard-cut migration to Alembic replaces all prior schema history; legacy weeklyToken* API key fields removed; React SPA replaces Jinja dashboard; static MODEL_CATALOG replaced by dynamic upstream model registry with plan-aware routing.

### Features

* password auth, API keys, React frontend, Alembic migrations, dynamic model registry ([#68](https://github.com/Soju06/codex-lb/issues/68)) ([35eb981](https://github.com/Soju06/codex-lb/commit/35eb9817cbd81878ee0dd5ed286094ab76eb189a))


### Bug Fixes

* **proxy:** prevent API key reservation leak on stream retry and compact errors ([#74](https://github.com/Soju06/codex-lb/issues/74)) ([592d47b](https://github.com/Soju06/codex-lb/commit/592d47b3df7b0e8c830d531b5625dcccb9c3f919))

## [0.6.0](https://github.com/Soju06/codex-lb/compare/v0.5.2...v0.6.0) (2026-02-10)


### Features

* **api:** OpenAI compatibility layers for Responses support ([#56](https://github.com/Soju06/codex-lb/issues/56)) ([3e95eb1](https://github.com/Soju06/codex-lb/commit/3e95eb134fc6066c6891830d6dd62a876b4526ee))
* **dashboard:** refactor load path and usage refresh ([#59](https://github.com/Soju06/codex-lb/issues/59)) ([899de74](https://github.com/Soju06/codex-lb/commit/899de74e48c8bace2fbbac92a0f9f6b5c699d15f))
* TOTP AUTH FOR WEB PANEL ([#61](https://github.com/Soju06/codex-lb/issues/61)) ([d05df1e](https://github.com/Soju06/codex-lb/commit/d05df1e6f658f6397c2ddaf7c0297814722839f0)), closes [#62](https://github.com/Soju06/codex-lb/issues/62)


### Documentation

* add dwnmf as a contributor for code, and test ([#63](https://github.com/Soju06/codex-lb/issues/63)) ([26bd133](https://github.com/Soju06/codex-lb/commit/26bd1334e727129a0e51168e222753ce485c737e))
* **openspec:** add context docs policy ([#57](https://github.com/Soju06/codex-lb/issues/57)) ([8a491f8](https://github.com/Soju06/codex-lb/commit/8a491f88637d3b4eb28e24aa5063f495350ecca1))

## [0.5.2](https://github.com/Soju06/codex-lb/compare/v0.5.1...v0.5.2) (2026-02-04)


### Bug Fixes

* **docker:** default data dir in containers ([#52](https://github.com/Soju06/codex-lb/issues/52)) ([e065f80](https://github.com/Soju06/codex-lb/commit/e065f804a8cc1c9ddb1e1076de169c833d8640a6))

## [0.5.1](https://github.com/Soju06/codex-lb/compare/v0.5.0...v0.5.1) (2026-02-03)


### Bug Fixes

* **core:** support gzip/deflate request decompression ([#49](https://github.com/Soju06/codex-lb/issues/49)) ([1db79aa](https://github.com/Soju06/codex-lb/commit/1db79aaef8d65af4b9246fad2b0687be17daba6b))


### Documentation

* add choi138 as a contributor for code, bug, and test ([#50](https://github.com/Soju06/codex-lb/issues/50)) ([80d5aae](https://github.com/Soju06/codex-lb/commit/80d5aaefd5c61ea420fda90744e8ffda69eaecf6))

## [0.5.0](https://github.com/Soju06/codex-lb/compare/v0.4.0...v0.5.0) (2026-01-29)


### Features

* **db:** add configurable pool settings ([#44](https://github.com/Soju06/codex-lb/issues/44)) ([e2e553d](https://github.com/Soju06/codex-lb/commit/e2e553debfac1ab51c691a883b16812db6acdd9e))
* **proxy:** add v1 chat and models endpoints ([#39](https://github.com/Soju06/codex-lb/issues/39)) ([c242304](https://github.com/Soju06/codex-lb/commit/c242304304583821afebb9e2c0b2803012d4a7aa))


### Bug Fixes

* **accounts:** update upsert for duplicate email ([#35](https://github.com/Soju06/codex-lb/issues/35)) ([5f68773](https://github.com/Soju06/codex-lb/commit/5f6877342d81abca82e800dbf0b21458e78cb1d9))
* **core:** support zstd request decompression and modularize middleware ([#42](https://github.com/Soju06/codex-lb/issues/42)) ([d0eebb7](https://github.com/Soju06/codex-lb/commit/d0eebb7b9c8c16b1a1293279db42633ba75b1867))
* **proxy:** use short-lived sessions for streaming ([#38](https://github.com/Soju06/codex-lb/issues/38)) ([cb48757](https://github.com/Soju06/codex-lb/commit/cb48757bfbf66d3fb2598523d66c6b5bda44a55d))
* **usage:** coalesce refresh requests ([#36](https://github.com/Soju06/codex-lb/issues/36)) ([04d8fab](https://github.com/Soju06/codex-lb/commit/04d8fab891236e4d4b6bb46c5219730acbabd822))


### Documentation

* add hhsw2015 as a contributor for maintenance ([#43](https://github.com/Soju06/codex-lb/issues/43)) ([1651968](https://github.com/Soju06/codex-lb/commit/1651968e2c8605190fe8647c755f2ab97a7db3d3))

## [0.4.0](https://github.com/Soju06/codex-lb/compare/v0.3.1...v0.4.0) (2026-01-26)


### Features

* **proxy:** add v1 responses compatibility for OpenCode ([#28](https://github.com/Soju06/codex-lb/issues/28)) ([04d58d2](https://github.com/Soju06/codex-lb/commit/04d58d2430e4ba88f28e9e811f08b628e9a4674c))


### Bug Fixes

* **dashboard:** remove rounding in avgPerHour calculation ([#29](https://github.com/Soju06/codex-lb/issues/29)) ([b432939](https://github.com/Soju06/codex-lb/commit/b432939d6ea832d917658dfdbcb935f88f9e08a6)), closes [#26](https://github.com/Soju06/codex-lb/issues/26)


### Documentation

* add hhsw2015 as a contributor for code, and test ([#31](https://github.com/Soju06/codex-lb/issues/31)) ([a1f0e79](https://github.com/Soju06/codex-lb/commit/a1f0e796e45862e520953f60716d2b5eaab3a0d9))
* add opencode setup guide ([#32](https://github.com/Soju06/codex-lb/issues/32)) ([9330619](https://github.com/Soju06/codex-lb/commit/93306198902e558e6bce89719d7cd6b1e797ddc5))
* add pcy06 as a contributor for doc ([#34](https://github.com/Soju06/codex-lb/issues/34)) ([506b7b1](https://github.com/Soju06/codex-lb/commit/506b7b160b11b558533fafb39793870ceefd9131))

## [0.3.1](https://github.com/Soju06/codex-lb/compare/v0.3.0...v0.3.1) (2026-01-22)


### Documentation

* add Quack6765 as a contributor for design ([7a5ec08](https://github.com/Soju06/codex-lb/commit/7a5ec084b9a8d32c844127739f826a5f83bf1440))
* update .all-contributorsrc ([14ea9da](https://github.com/Soju06/codex-lb/commit/14ea9da361a978a56c4d1f7facefe789193c7b91))
* update README.md ([f283d60](https://github.com/Soju06/codex-lb/commit/f283d60ae359585cd128a965ca6fba2a14249a11))

## [0.3.0](https://github.com/Soju06/codex-lb/compare/v0.2.0...v0.3.0) (2026-01-21)


### Features

* add cached input tokens handling and update related metrics in … ([5bf6609](https://github.com/Soju06/codex-lb/commit/5bf66095b8000ffc8fbdf8d989f60171604f69d3))
* add cached input tokens handling and update related metrics in logs and usage schemas ([c965036](https://github.com/Soju06/codex-lb/commit/c9650367c1a2d14e63e3440788b7cd44b08ebd9a))
* add formatting for cached input tokens metadata in metrics display ([53feaa6](https://github.com/Soju06/codex-lb/commit/53feaa62f7c5c282508f37c3fd42d9af655c2fa9))
* add secondary usage tracking and selection logic for accounts in load balancer ([d66cf69](https://github.com/Soju06/codex-lb/commit/d66cf69b2834b42fefbbfa646d82477f9832fdda))
* add ty type checking and refactors ([41fa811](https://github.com/Soju06/codex-lb/commit/41fa8112ba9b900ffa5dbee3a39d94267e2caa75))
* **app:** add migrations and reasoning effort support ([9eae590](https://github.com/Soju06/codex-lb/commit/9eae5903a08363291e397f983a531ddf325658d7))
* implement dashboard settings for sticky threads and reset preferences ([cd04812](https://github.com/Soju06/codex-lb/commit/cd0481247f0ceffdd92173ea84773960e52a7253))


### Bug Fixes

* **app:** tune sqlite pragmas and usage UI ([a44a4fd](https://github.com/Soju06/codex-lb/commit/a44a4fd6fe5771282a12ee62a34c9be819254322))
* **app:** update effort display format in history ([0796740](https://github.com/Soju06/codex-lb/commit/0796740ab570cf476b2285a615559a9a6318082f))
* **app:** update effort display format to include parentheses ([6fbae96](https://github.com/Soju06/codex-lb/commit/6fbae960f393ff92cae0feb614ca0e811a855851))
* **dashboard:** fallback primary remaining to summary ([02b3d39](https://github.com/Soju06/codex-lb/commit/02b3d39c2b734271af7c420fc52b7e87350177e1))
* **db:** avoid leaked async connection in migration ([9aa1d03](https://github.com/Soju06/codex-lb/commit/9aa1d0395481a96a21db2d0add18ee1753f183b2))
* **db:** use returning for dml checks ([4ec7c7a](https://github.com/Soju06/codex-lb/commit/4ec7c7a6615e6e5852b0865e09184544f09ebedc))
* **ui:** style and label settings checkboxes ([722cad8](https://github.com/Soju06/codex-lb/commit/722cad851706e2784815dad4069902cc95b3f662))


### Documentation

* expand 0.2.0 changelog ([32148dc](https://github.com/Soju06/codex-lb/commit/32148dc2d195cec0dd85f61fc0a13d8cbef24e24))

## [0.2.0](https://github.com/Soju06/codex-lb/compare/v0.1.5...v0.2.0) (2026-01-19)


### Features

* add ty type checking and pre-commit hook
* add health response schema and typed context cleanup


### Bug Fixes

* normalize stored plan types (pro/team/business/enterprise/edu) so accounts no longer show as unknown
* prevent rate-limit status when usage is below 100% by using cooldown/backoff and primary-window quota checks
* surface per-account quota reset times by applying primary/secondary reset windows with fallbacks


### Refactor

* move auth/usage helpers into module boundaries and extract proxy helpers
* tighten typing across services and tests

## [0.1.5](https://github.com/Soju06/codex-lb/compare/v0.1.4...v0.1.5) (2026-01-14)


### Bug Fixes

* align rate-limit backoff and reset handling ([4d59650](https://github.com/Soju06/codex-lb/commit/4d596508e5ad13e68aa6e64f9cb32324bd38f07b))

## [0.1.4](https://github.com/Soju06/codex-lb/compare/v0.1.3...v0.1.4) (2026-01-13)


### Bug Fixes

* **db:** harden session cleanup on cancellation ([dee3916](https://github.com/Soju06/codex-lb/commit/dee3916efa83dedec1d5ad43e1e14950b8c6e4a7))

## [0.1.3](https://github.com/Soju06/codex-lb/compare/v0.1.2...v0.1.3) (2026-01-12)


### Documentation

* use absolute image URLs for PyPI ([5fa65a5](https://github.com/Soju06/codex-lb/commit/5fa65a572980f356738f49be3adf2c62fdc38466))

## [0.1.2](https://github.com/Soju06/codex-lb/compare/v0.1.1...v0.1.2) (2026-01-12)


### Bug Fixes

* sync package __version__ ([3dd97e6](https://github.com/Soju06/codex-lb/commit/3dd97e6397a8ea9d3528c166d1e729936f98f737))

## [0.1.1](https://github.com/Soju06/codex-lb/compare/v0.1.0...v0.1.1) (2026-01-12)


### Bug Fixes

* address lint warnings ([7c3cc06](https://github.com/Soju06/codex-lb/commit/7c3cc06c9a6a9a9a8895c1dd5fcc57b3c0eebdb3))
* reactivate accounts when secondary quota clears ([58a4263](https://github.com/Soju06/codex-lb/commit/58a42630d644559f96f045a96c25d0126810542e))
* skip project install in docker build ([64e9156](https://github.com/Soju06/codex-lb/commit/64e9156075c256ef48c0587ea1abb7cc092b97a5))


### Documentation

* add dashboard hero and accounts view ([3522654](https://github.com/Soju06/codex-lb/commit/3522654fe5d09adbe32895d4b24e8b00faac9dfe))

## [0.1.0](https://github.com/Soju06/codex-lb/releases/tag/v0.1.0) (2026-01-07)


### Bug Fixes

* address lint warnings ([7c3cc06](https://github.com/Soju06/codex-lb/commit/7c3cc06c9a6a9a8895c1dd5fcc57b3c0eebdb3))
* skip project install in docker build ([64e9156](https://github.com/Soju06/codex-lb/commit/64e9156075c256ef48c0587ea1abb7cc092b97a5))
