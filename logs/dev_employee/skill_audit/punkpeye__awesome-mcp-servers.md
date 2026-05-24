# Skill Candidate Audit — Awesome MCP Servers

- Repo: `https://github.com/punkpeye/awesome-mcp-servers.git`
- Commit: `39b5e990fe94734de271a2b13ec1513811da9cdd`
- Audit time: `2026-05-25T05:29:45+08:00`
- Rough risk score: `74`

## Manifest files

- `README.md`

## Finding counts

- `credential_keywords`: 37
- `sensitive_paths`: 37

## Sample findings

- `sensitive_paths` `README-zh_TW.md:66` — `* 📂 - [瀏覽器自動化](#browser-automation)`
- `sensitive_paths` `README-zh_TW.md:103` — `### 📂 <a name="browser-automation"></a>瀏覽器自動化`
- `sensitive_paths` `README-zh_TW.md:106` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - 由 Rust 打造的輕量級瀏覽器自動化 MCP 伺服器，無需任何外部相依。`
- `credential_keywords` `README-zh_TW.md:274` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - 用於PTY操作的AI助手，使智慧體能夠通過有狀態會話、SSH連接和後台進程管理來控制互動式終端`
- `credential_keywords` `README-zh_TW.md:379` — `- [SecretiveShell/MCP-timeserver](https://github.com/SecretiveShell/MCP-timeserver) 🐍 🏠 - 訪問任意時區的時間並獲取當前本地時間`
- `sensitive_paths` `README-zh_TW.md:421` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - 一個用於 Apify 的 RAG Web 瀏覽器 Actor 的 MCP 伺服器，可以執行網頁搜尋、抓取 URL，並以 Markdown 格式返回內容。`
- `credential_keywords` `README-zh_TW.md:422` — `- [SecretiveShell/MCP-searxng](https://github.com/SecretiveShell/MCP-searxng) 🐍 🏠 - 用於連接到 searXNG 實例的 MCP 伺服器`
- `credential_keywords` `README-zh_TW.md:560` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 - OpenAI 中間件代理，用於在任何現有的 OpenAI 相容用戶端中使用 MCP`
- `credential_keywords` `README-pt_BR.md:120` — `- [YangLiangwei/PersonalizationMCP](https://github.com/YangLiangwei/PersonalizationMCP) 🐍 ☁️ 🏠 🍎 🪟 🐧 - Servidor MCP abrangente de agregação de dados pessoais com integrações Steam, YouTube, Bilibili, Spotify, Reddit e outras plataformas. Po`
- `sensitive_paths` `README-pt_BR.md:151` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - Servidor MCP leve de automação de navegador em Rust, sem dependências externas.`
- `sensitive_paths` `README-pt_BR.md:155` — `- [browserbase/mcp-server-browserbase](https://github.com/browserbase/mcp-server-browserbase) 🎖️ 📇 - Automatize interações do navegador na nuvem (por exemplo, navegação web, extração de dados, preenchimento de formulários e mais)`
- `sensitive_paths` `README-pt_BR.md:156` — `- [browsermcp/mcp](https://github.com/browsermcp/mcp) 📇 🏠 - Automatize seu navegador Chrome local`
- `sensitive_paths` `README-pt_BR.md:158` — `- [co-browser/browser-use-mcp-server](https://github.com/co-browser/browser-use-mcp-server) 🐍 - browser-use empacotado como um servidor MCP com transporte SSE. Inclui um dockerfile para executar o chromium em docker + um servidor vnc.`
- `sensitive_paths` `README-pt_BR.md:160` — `- [eyalzh/browser-control-mcp](https://github.com/eyalzh/browser-control-mcp) 📇 🏠 - Um servidor MCP pareado com uma extensão de navegador que permite clientes LLM controlar o navegador do usuário (Firefox).`
- `sensitive_paths` `README-pt_BR.md:168` — `- [ndthanhdev/mcp-browser-kit](https://github.com/ndthanhdev/mcp-browser-kit) 📇 🏠 - Um servidor MCP para interagir com navegadores compatíveis com manifest v2.`
- `credential_keywords` `README-pt_BR.md:302` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - Piloto de IA para operações PTY que permite aos agentes controlar terminais interativos com sessões com estado, conexões SSH e gerenciamento de processos em segundo plano`
- `credential_keywords` `README-pt_BR.md:304` — `- [freema/mcp-design-system-extractor](https://github.com/freema/mcp-design-system-extractor) 📇 🏠 - Extrai informações de componentes de sistemas de design Storybook. Fornece HTML, estilos, propriedades, dependências, tokens de tema e metad`
- `credential_keywords` `README-pt_BR.md:335` — `- [8b-is/smart-tree](https://github.com/8b-is/smart-tree) 🦀 🏠 🍎 🪟 🐧 - Visualização de diretório nativa para IA com análise semântica, formatos ultra-comprimidos para consumo de IA e redução de tokens 10x. Suporta modo quântico-semântico com`
- `credential_keywords` `README-pt_BR.md:353` — `- [bankless/onchain-mcp](https://github.com/Bankless/onchain-mcp/) 📇 ☁️ - API Bankless Onchain para interagir com contratos inteligentes, consultar informações de transações e tokens`
- `credential_keywords` `README-pt_BR.md:414` — `- [rossshannon/Weekly-Weather-mcp](https://github.com/rossshannon/weekly-weather-mcp.git) 🐍 ☁️ - Servidor MCP para previsão meteorológica semanal que retorna 7 dias completos de previsões meteorológicas detalhadas em qualquer lugar do mundo`
- `credential_keywords` `README-pt_BR.md:415` — `- [SecretiveShell/MCP-timeserver](https://github.com/SecretiveShell/MCP-timeserver) 🐍 🏠 - Acesse o horário em qualquer fuso horário e obtenha o horário local atual`
- `sensitive_paths` `README-pt_BR.md:447` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - Um servidor MCP para o Ator RAG Web Browser de código aberto da Apify para realizar pesquisas na web, raspar URLs e retornar conteúdo em Markdo`
- `credential_keywords` `README-pt_BR.md:551` — `- [tumf/web3-mcp](https://github.com/tumf/web3-mcp) 🐍 ☁️ - Uma implementação de servidor MCP que envolve a Ankr Advanced API. Acesso a NFT, token e dados de blockchain em várias redes, incluindo Ethereum, BSC, Polygon, Avalanche e mais.`
- `credential_keywords` `README-pt_BR.md:565` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 – um proxy middleware openAI para usar mcp em qualquer cliente compatível com openAI`
- `sensitive_paths` `README-th.md:75` — `* 📂 - [การทำงานอัตโนมัติของเบราว์เซอร์](#browser-automation)`
- `sensitive_paths` `README-th.md:139` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - เซิร์ฟเวอร์ MCP สำหรับการทำงานอัตโนมัติของเบราว์เซอร์ที่มีน้ำหนักเบา เขียนด้วย Rust และไม่มีการพึ่งพาภายนอก.`
- `sensitive_paths` `README-th.md:143` — `- [browserbase/mcp-server-browserbase](https://github.com/browserbase/mcp-server-browserbase) 🎖️ 📇 - ทำงานอัตโนมัติกับเบราว์เซอร์บนคลาวด์ (เช่น การนำทางเว็บ การดึงข้อมูล การกรอกแบบฟอร์ม และอื่นๆ)`
- `sensitive_paths` `README-th.md:307` — `- [Jktfe/serveMyAPI](https://github.com/Jktfe/serveMyAPI) 📇 🏠 🍎 - เซิร์ฟเวอร์ MCP (Model Context Protocol) ส่วนบุคคลสำหรับจัดเก็บและเข้าถึงคีย์ API อย่างปลอดภัยในโปรเจ็กต์ต่างๆ โดยใช้ macOS Keychain`
- `credential_keywords` `README-th.md:317` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - นักบิน AI สำหรับการดำเนินงาน PTY ที่ช่วยให้เอเจนต์สามารถควบคุมเทอร์มินัลแบบโต้ตอบด้วยเซสชันที่มีสถานะ การเชื่อมต่อ SSH และการจัดการกระบวนการพื้นหลัง`
- `sensitive_paths` `README-th.md:398` — `- [getalby/nwc-mcp-server](https://github.com/getalby/nwc-mcp-server) 📇 🏠 - การผสานรวมกระเป๋าเงิน Bitcoin Lightning ขับเคลื่อนโดย Nostr Wallet Connect`
- `credential_keywords` `README-th.md:412` — `- [kukapay/token-minter-mcp](https://github.com/kukapay/token-minter-mcp) 🐍 ☁️ - เซิร์ฟเวอร์ MCP ที่มีเครื่องมือสำหรับตัวแทน AI เพื่อสร้างโทเค็น ERC-20 ในบล็อกเชนหลายตัว`
- `credential_keywords` `README-th.md:413` — `- [kukapay/token-revoke-mcp](https://github.com/kukapay/token-revoke-mcp) 🐍 ☁️ - เซิร์ฟเวอร์ MCP สำหรับตรวจสอบและเพิกถอนการอนุญาตโทเค็น ERC-20 ในบล็อกเชนหลายตัว`
- `credential_keywords` `README-th.md:477` — `- [SecretiveShell/MCP-timeserver](https://github.com/SecretiveShell/MCP-timeserver) 🐍 🏠 - เข้าถึงเวลาในเขตเวลาใดก็ได้และรับเวลาท้องถิ่นปัจจุบัน`
- `sensitive_paths` `README-th.md:509` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - เซิร์ฟเวอร์ MCP สำหรับ RAG Web Browser Actor แบบโอเพ่นซอร์สของ Apify เพื่อทำการค้นหาเว็บ สแครป URL และส่งคืนเนื้อหาในรูปแบบ Markdown`
- `credential_keywords` `README-th.md:531` — `- [SecretiveShell/MCP-searxng](https://github.com/SecretiveShell/MCP-searxng) 🐍 🏠 - เซิร์ฟเวอร์ MCP เพื่อเชื่อมต่อกับอินสแตนซ์ searXNG`
- `credential_keywords` `README-th.md:663` — `- [SecretiveShell/MCP-wolfram-alpha](https://github.com/SecretiveShell/MCP-wolfram-alpha) 🐍 ☁️ - เซิร์ฟเวอร์ MCP สำหรับสอบถาม API ของ Wolfram Alpha`
- `credential_keywords` `README-th.md:725` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 – พร็อกซี่ middleware OpenAI เพื่อใช้ MCP ในไคลเอนต์ที่เข้ากันได้กับ OpenAI ใดๆ`
- `sensitive_paths` `README-ko.md:73` — `* 📂 - [브라우저 자동화](#browser-automation)`
- `sensitive_paths` `README-ko.md:111` — `### 📂 <a name="browser-automation"></a>브라우저 자동화`
- `sensitive_paths` `README-ko.md:114` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - Rust로 작성된 의존성 없는 경량 브라우저 자동화 MCP 서버.`
- `sensitive_paths` `README-ko.md:124` — `- [@co-browser/browser-use-mcp-server](https://github.com/co-browser/browser-use-mcp-server) 🌐🔮 - SSE 전송을 지원하는 MCP 서버로 패키징된 browser-use. Docker에서 Chromium을 실행하기 위한 Dockerfile + VNC 서버 포함.`
- `credential_keywords` `README-ko.md:330` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - 상태 유지 세션, SSH 연결, 백그라운드 프로세스 관리로 AI 에이전트가 대화형 터미널을 제어할 수 있게 하는 PTY 작업용 AI 파일럿`
- `credential_keywords` `README-ko.md:384` — `- [kukapay/token-minter-mcp](https://github.com/kukapay/token-minter-mcp) 🐍 ☁️ - 여러 블록체인에서 ERC-20 토큰을 발행하는 도구를 AI 에이전트에게 제공하는 MCP 서버.`
- `credential_keywords` `README-ko.md:432` — `- [SecretiveShell/MCP-timeserver](https://github.com/SecretiveShell/MCP-timeserver) 🐍 🏠 - 모든 시간대의 시간에 접근하고 현재 현지 시간 확인`
- `sensitive_paths` `README-ko.md:476` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - Apify의 오픈 소스 RAG 웹 브라우저 액터를 위한 MCP 서버로 웹 검색, URL 스크래핑 및 마크다운 형식으로 콘텐츠 반환 수행.`
- `credential_keywords` `README-ko.md:477` — `- [SecretiveShell/MCP-searxng](https://github.com/SecretiveShell/MCP-searxng) 🐍 🏠 - searXNG 인스턴스에 연결하기 위한 MCP 서버`
- `credential_keywords` `README-ko.md:593` — `- [SecretiveShell/MCP-wolfram-alpha](https://github.com/SecretiveShell/MCP-wolfram-alpha) 🐍 ☁️ - Wolfram Alpha API 쿼리를 위한 MCP 서버.`
- `credential_keywords` `README-ko.md:653` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 – 기존의 모든 openAI 호환 클라이언트에서 mcp를 사용하기 위한 openAI 미들웨어 프록시`
- `sensitive_paths` `README-zh.md:83` — `* 📂 - [浏览器自动化](#browser-automation)`
- `sensitive_paths` `README-zh.md:123` — `### 📂 <a name="browser-automation"></a>浏览器自动化`
- `sensitive_paths` `README-zh.md:126` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - 使用 Rust 构建的轻量级浏览器自动化 MCP 服务器，无任何外部依赖。`
- `sensitive_paths` `README-zh.md:139` — `- [@co-browser/browser-use-mcp-server](https://github.com/co-browser/browser-use-mcp-server) 🌐🔮 - browser-use是一个封装了SSE传输协议的MCP服务器。包含一个dockerfile用于在docker中运行chromium浏览器+VNC服务器。`
- `credential_keywords` `README-zh.md:337` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - 用于PTY操作的AI助手，使智能体能够通过有状态会话、SSH连接和后台进程管理来控制交互式终端`
- `credential_keywords` `README-zh.md:420` — `- [kukapay/token-minter-mcp](https://github.com/kukapay/token-minter-mcp) 🐍 ☁️ -  一个MCP服务器，为AI代理提供工具以跨多个区块链铸造ERC-20代币。`
- `credential_keywords` `README-zh.md:471` — `- [SecretiveShell/MCP-timeserver](https://github.com/SecretiveShell/MCP-timeserver) 🐍 🏠 - 访问任意时区的时间并获取当前本地时间`
- `sensitive_paths` `README-zh.md:519` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - 一个用于 Apify 的 RAG Web 浏览器 Actor 的 MCP 服务器，可以执行网页搜索、抓取 URL，并以 Markdown 格式返回内容。`
- `credential_keywords` `README-zh.md:520` — `- [SecretiveShell/MCP-searxng](https://github.com/SecretiveShell/MCP-searxng) 🐍 🏠 - 用于连接到 searXNG 实例的 MCP 服务器`
- `credential_keywords` `README-zh.md:645` — `- [SecretiveShell/MCP-wolfram-alpha](https://github.com/SecretiveShell/MCP-wolfram-alpha) 🐍 ☁️ - 用于查询Wolfram Alpha API的MCP服务器。`
- `credential_keywords` `README-zh.md:710` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 - OpenAI 中间件代理，用于在任何现有的 OpenAI 兼容客户端中使用 MCP`
- `sensitive_paths` `README-ja.md:77` — `* 📂 - [ブラウザ自動化](#browser-automation)`
- `credential_keywords` `README-ja.md:231` — `- [tufantunc/ssh-mcp](https://github.com/tufantunc/ssh-mcp) 📇 🏠 🐧 🪟 - モデルコンテキストプロトコル経由でLinuxおよびWindowsサーバーのSSH制御を公開するMCPサーバー。パスワードまたはSSHキー認証でリモートシェルコマンドを安全に実行。`
- `credential_keywords` `README-ja.md:332` — `- [yiwenlu66/PiloTY](https://github.com/yiwenlu66/PiloTY) 🐍 🏠 - AIエージェントが状態保持セッション、SSH接続、バックグラウンドプロセス管理を使ってインタラクティブターミナルを制御できるPTY操作のAIパイロット`
- `credential_keywords` `README-ja.md:388` — `- [kukapay/token-minter-mcp](https://github.com/kukapay/token-minter-mcp) 🐍 ☁️ - AIエージェントが複数のブロックチェーンでERC-20トークンをミントするためのツールを提供するMCPサーバー`
- `credential_keywords` `README-ja.md:389` — `- [kukapay/token-revoke-mcp](https://github.com/kukapay/token-revoke-mcp) 🐍 ☁️ - 複数のブロックチェーンでERC-20トークンの許可をチェックおよび取り消すためのMCPサーバー`
- `sensitive_paths` `README-ja.md:516` — `- [apify/mcp-server-rag-web-browser](https://github.com/apify/mcp-server-rag-web-browser) 📇 ☁️ - Apify の RAG Web Browser Actor 用の MCP サーバーで、ウェブ検索を実行し、URL をスクレイピングし、Markdown 形式でコンテンツを返します。`
- `sensitive_paths` `README-ja.md:540` — `- [co-browser/attestable-mcp-server](https://github.com/co-browser/attestable-mcp-server) 🐍 🏠 ☁️ 🐧 - Gramine経由で信頼実行環境（TEE）内で実行されるMCPサーバー。[RA-TLS](https://gramine.readthedocs.io/en/stable/attestation.html)を使用したリモート証明を紹介。MCPクライアントが接続前にサーバーを検証`
- `credential_keywords` `README-ja.md:665` — `- [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge) 🐍 既存のOpenAI互換クライアントでMCPを使用するためのOpenAIミドルウェアプロキシ`
- `sensitive_paths` `README-ja.md:697` — `### 📂 <a name="browser-automation"></a>ブラウザ自動化`
- `sensitive_paths` `README-ja.md:701` — `- [BB-fat/browser-use-rs](https://github.com/BB-fat/browser-use-rs) 🦀 - Rust製で依存関係ゼロの軽量ブラウザ自動化 MCP サーバー。`
- `sensitive_paths` `README-ja.md:706` — `- [browserbase/mcp-server-browserbase](https://github.com/browserbase/mcp-server-browserbase) 🎖️ 📇 - クラウドでのブラウザ相互作用の自動化（ウェブナビゲーション、データ抽出、フォーム入力など）`
- `sensitive_paths` `README-ja.md:707` — `- [browsermcp/mcp](https://github.com/browsermcp/mcp) 📇 🏠 - ローカルChromeブラウザを自動化`
- `sensitive_paths` `README-ja.md:709` — `- [co-browser/browser-use-mcp-server](https://github.com/co-browser/browser-use-mcp-server) 🐍 - SSEトランスポートでMCPサーバーとしてパッケージ化されたbrowser-use。dockerでchromiumを実行するdockerファイル + vncサーバーを含む`
- `sensitive_paths` `README-ja.md:711` — `- [eyalzh/browser-control-mcp](https://github.com/eyalzh/browser-control-mcp) 📇 🏠 - LLMクライアントがユーザーのブラウザ（Firefox）を制御できるブラウザ拡張機能と組み合わせたMCPサーバー`
- `sensitive_paths` `README-ja.md:718` — `- [ndthanhdev/mcp-browser-kit](https://github.com/ndthanhdev/mcp-browser-kit) 📇 🏠 - manifest v2互換ブラウザとの相互作用のためのMCPサーバー`
