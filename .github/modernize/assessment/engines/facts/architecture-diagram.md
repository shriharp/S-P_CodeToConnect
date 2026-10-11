# Architecture Diagram

KAIROS is a containerized modular monolith: a React dashboard is served by
Nginx, while a FastAPI backend owns live ingestion, NLP interpretation,
portfolio policy, persistence, and server-sent events.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart TD
    subgraph Client["Client Layer"]
        Browser["Browser"]
        Dashboard["React dashboard"]
    end
    subgraph Runtime["Container Runtime"]
        Nginx["Nginx static host"]
        Api["FastAPI backend"]
        Scheduler["Background scheduler"]
    end
    subgraph Pipeline["Risk Pipeline"]
        Adapters["Provider adapters"]
        Queue["Durable raw item queue"]
        NLP["NLP interpretation"]
        Contract["Signal contract"]
        Policy["Module A policy"]
    end
    subgraph Data["SQLite Persistence"]
        Signals[("Signals database")]
        Ledger[("Decision ledger")]
        Ingestion[("Ingestion and queue state")]
    end
    subgraph External["Free External Sources"]
        News["GDELT and RSS news"]
        Social["StockTwits and Reddit RSS"]
        Filings["SEC EDGAR"]
        Prices["yfinance"]
    end

    Browser -->|"loads"| Nginx
    Nginx -->|"serves"| Dashboard
    Dashboard -->|"REST and SSE"| Api
    Scheduler -->|"polls"| Adapters
    News -->|"source items"| Adapters
    Social -->|"source items"| Adapters
    Filings -->|"filing metadata"| Adapters
    Prices -->|"market data"| Api
    Adapters -->|"normalized items"| Queue
    Queue -->|"claimed batches"| NLP
    NLP -->|"interpreted signals"| Contract
    Contract -->|"validated signals"| Signals
    Contract -->|"eligible signals"| Policy
    Policy -->|"recorded decisions"| Ledger
    Queue -->|"health and cursors"| Ingestion
    Signals -->|"dashboard data"| Api
    Ledger -->|"dashboard data"| Api
    Ingestion -->|"observability"| Api
~~~

### Technology Stack Summary

| Layer | Technology | Version | Purpose |
|---|---|---:|---|
| Frontend | React and Vite | React 18, Vite 5 | Dashboard views and client interactions |
| Frontend hosting | Nginx Alpine | 1.27 | Static assets, SPA fallback, API and SSE proxy |
| Backend | FastAPI and Uvicorn | FastAPI 0.143, Uvicorn 0.54 | REST API, SSE, lifecycle and scheduler |
| Validation | Pydantic | 2.14 | Signal and request contract validation |
| NLP | CPU-first hybrid pipeline | Application code | Entity resolution, sentiment, event interpretation |
| Portfolio | Deterministic Module A policy | Application code | Gates, caps, normalization, decision ledger |
| Persistence | SQLite | Python standard library | Signals, ledger, queue, cursors, provider health |
| Runtime | Docker Compose | Compose specification | One-command judge startup and named volumes |

### Data Storage & External Services

The backend persists operational state in SQLite databases under a Docker named
volume. The image seeds replay and market files on first startup, while runtime
databases remain durable across container recreation. Live providers are free and
keyless: GDELT and public RSS feeds provide news, StockTwits and Reddit RSS
provide social signals, SEC EDGAR provides filing metadata, and yfinance provides
market prices. Provider failures remain visible in Observability rather than
being silently replaced.

### Key Architectural Decisions

- The backend scheduler is enabled by default in Compose so polling continues
  independently of the browser.
- The frontend and backend remain separate containers with a narrow HTTP and SSE
  boundary, preserving the modular monolith while keeping deployment simple.
- Live, historical replay, and read-only synthetic scenarios remain explicitly
  separated by provenance and dashboard scope.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart LR
    subgraph cPresentation["Presentation"]
        cOverview["Overview"]
        cFeed["Signal Feed"]
        cPortfolio["Portfolio"]
        cLab["Strategy Lab"]
        cObs["Observability"]
    end
    subgraph cApi["API Boundary"]
        cRoutes["FastAPI routes"]
        cSse["SSE event hub"]
    end
    subgraph cBusiness["Business Logic"]
        cPoller["Live poller"]
        cPipeline["NLP pipeline"]
        cRebalancer["Portfolio rebalancer"]
        cReplay["Replay engine"]
    end
    subgraph cData["Data Access"]
        cSignalStore["Signal store"]
        cLedgerStore["Ledger store"]
        cQueueStore["Queue and health stores"]
    end
    subgraph cInfra["Infrastructure"]
        cScheduler["Ingestion scheduler"]
        cSources["External source adapters"]
        cCompose["Docker Compose runtime"]
    end

    cOverview -->|"reads history"| cRoutes
    cFeed -->|"reads signals"| cRoutes
    cPortfolio -->|"reads ledger"| cRoutes
    cLab -->|"counterfactual request"| cRoutes
    cObs -->|"reads health"| cRoutes
    cRoutes -->|"publishes updates"| cSse
    cRoutes -->|"triggers"| cPoller
    cRoutes -->|"runs"| cReplay
    cScheduler -->|"starts cycles"| cPoller
    cSources -->|"feeds"| cPoller
    cPoller -->|"queues items"| cQueueStore
    cPoller -->|"analyzes"| cPipeline
    cPipeline -->|"persists"| cSignalStore
    cPipeline -->|"eligible signals"| cRebalancer
    cReplay -->|"uses"| cPipeline
    cRebalancer -->|"persists decisions"| cLedgerStore
    cQueueStore -->|"health state"| cRoutes
    cSignalStore -->|"signal data"| cRoutes
    cLedgerStore -->|"ledger data"| cRoutes
    cCompose -.->|"hosts"| cScheduler
~~~

### Component Inventory

| Component | Layer | Type | Responsibility |
|---|---|---|---|
| Overview | Presentation | React view | Weight timeline, causal evidence, and event filters |
| Signal Feed | Presentation | React view | Signal ranking, evidence, provenance, and detail |
| Portfolio | Presentation | React view | Holdings, sector exposure, performance, and ledger |
| Strategy Lab | Presentation | React view | Read-only article and counterfactual simulation |
| Observability | Presentation | React view | Scheduler, provider, queue, and model health |
| FastAPI routes | API Boundary | HTTP API | REST resource and command endpoints |
| SSE event hub | API Boundary | Event stream | Pushes completed live ingestion notifications |
| Live poller | Business Logic | Orchestrator | Coordinates provider fetch, deduplication, and analysis |
| NLP pipeline | Business Logic | Analyzer | Resolves entities, sentiment, event, evidence, and impact |
| Portfolio rebalancer | Business Logic | Policy engine | Applies gates, caps, direction, and normalization |
| Replay engine | Business Logic | Deterministic runner | Replays committed historical text through fresh inference |
| Signal store | Data Access | SQLite repository | Persists validated company-specific signals |
| Ledger store | Data Access | SQLite repository | Persists before and after allocation decisions |
| Queue and health stores | Data Access | SQLite repositories | Persists raw items, retries, cursors, and provider health |
| Ingestion scheduler | Infrastructure | Background worker | Runs periodic ingestion independent of the browser |
| External source adapters | Infrastructure | Provider integrations | Normalizes live news, social, filing, and market sources |
| Docker Compose runtime | Infrastructure | Container orchestration | Starts frontend and backend with persistent volumes |
