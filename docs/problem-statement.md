# Problem Statement

The objective of this case study is to design and implement a platform capable of ingesting and analyzing real-time, unstructured data to generate actionable financial risk signals.

The primary deliverable is KAIROS, a unified AI/NLP Risk Engine with the
tagline **Signal Over Noise**. KAIROS serves as the central processing unit,
parsing text-based data from sources such as news feeds and social media and
converting it into structured output.

Upon completion of the core engine, teams are required to implement at least one of the following downstream modules to demonstrate a practical application of the generated risk intelligence:

Module A: A tactical, high-frequency stock index rebalancer.  
Module B: A strategic, event-driven portfolio stress-testing tool.

The project is structured modularly to allow for focused development on distinct components within the specified timeframe.

## 2. The Core Challenge: The AI/NLP Risk Engine

Your primary task is to build a robust data pipeline and NLP model that can ingest text from various sources and output structured, machine-readable risk signals.

**Engine Requirements:**

- **Data Ingestion:** The engine must be able to process text from at least two different sources (e.g., financial news articles and Twitter/X posts).
- **NLP-Driven Analysis:** The engine must analyze the text and, for a given company or event, output structured data with the following fields:
  - **Sentiment Score:** A numerical score indicating positive, negative, or neutral sentiment (e.g., from -1.0 to 1.0).
  - **Event Classification:** A categorical label for the type of event discussed (e.g., Geopolitical, Macroeconomic, Credit Event, Merger/Acquisition, Product Launch).
  - **Impact Score:** A predicted severity score (e.g., 1-10) indicating the potential market impact of the event.
- **Output:** The engine should make these structured signals available for consumption by downstream applications, for example, through a simple API or by writing to a file.

## 3. Downstream Applications (Choose at least ONE)

Once your AI/NLP Risk Engine is operational, you must build at least one of the following modules to demonstrate its capabilities.

### Module A: Tactical Index Rebalancing

**Objective:** Create a system that dynamically rebalances a mock stock index (e.g., a selection of 10-20 stocks from the S&P 100) based on real-time sentiment.

**Functionality:**

- This module will subscribe to the Sentiment Score from your NLP Risk Engine.
- For each stock in your mock index, the system will adjust the stock's weight in the portfolio.
  - **Positive Sentiment:** Increase the weight of the stock.
  - **Negative Sentiment:** Decrease the weight of the stock.
- **Visualization:** Create a simple dashboard that visualizes the changing weights of the stocks in your index over time.

### Module B: Strategic Portfolio Stress Testing

**Objective:** Design a conceptual tool that simulates the impact of major real-world events on a synthetic portfolio of wholesale banking assets.

**Functionality:**

- This module will subscribe to the Event Classification and Impact Score from your NLP Risk Engine.
- Define a synthetic portfolio using the provided sample transaction data. The portfolio should include a mix of asset types (e.g., loans, bonds, derivatives).
- When a high-impact event is detected (e.g., Geopolitical with an Impact Score > 7), the module will trigger a "stress test."
- **Stress Test Simulation:** For the purpose of the hackathon, the stress test can be a simplified model. For example, you can define a set of shocks (e.g., a 10% drop in all equity prices, a 2% increase in interest rates) that are applied to your portfolio when a specific event type is detected.
- **Visualization:** Create a dashboard that shows the portfolio's value before and after the stress test, highlighting the impact of the simulated event.

## 4. Open-Source Datasets and Resources

To ensure this case study is implementable, here are several free, open-source datasets and APIs that you can use. You are encouraged to use these as a starting point and augment them with other sources you find. All listed resources have free tiers and do not require payment.

### Unstructured Data for NLP (News & Social Media)

| Resource | Description | Use Case |
|---|---|---|
| The GDELT Project | A massive, open database that monitors global news media in over 100 languages, updated every 15 minutes. It categorizes events and themes, making it perfect for the NLP Risk Engine. | Ingesting a real-time, categorized feed of global events to power the Event Classification and Impact Score in your NLP engine. |
| Financial News Sentiment Datasets (Kaggle) | Kaggle hosts numerous datasets with financial news headlines and articles, often pre-labeled with sentiment. A popular example is the "Sentiment Analysis for Financial News" dataset. | Training or fine-tuning your Sentiment Score model. Can also be used for back-testing your strategies. |
| News API (newsapi.org) | Provides a free developer plan to fetch recent news articles from thousands of sources. It's great for getting real-time headlines and articles for your demo. | A live source of news for your NLP engine. |
| Historical Stock Tweets (Kaggle) | Datasets like "Tweet Sentiment's Impact on Stock Returns" contain millions of tweets related to specific stocks, often with sentiment polarity scores. | A rich source for training your sentiment model and understanding the relationship between social media and stock returns. |

### Financial Data (Transactions & Market Prices)

| Resource | Description | Use Case |
|---|---|---|
| yfinance Python Library | An extremely popular and easy-to-use library to download historical market data for stocks, indices, and currencies directly from Yahoo Finance. | Fetching historical price data for Module A (Index Rebalancing) and Module B (Stress Testing). |
| Alpha Vantage | Offers a free API for real-time and historical data on stocks, forex, and cryptocurrencies, including technical indicators. | An alternative or supplement to yfinance for fetching market data. |
| Salad Money Open Banking Transaction Data | A secure dataset containing anonymized transaction-level data from UK key workers. It includes spending categories, amounts, and demographic information. | An excellent source for creating a realistic synthetic portfolio for Module B, with varied transaction types and user profiles. |
| Financial Transactions Dataset (Kaggle) | This dataset combines transaction records, customer information, and card data, designed for fraud detection and customer behavior analysis. | Another great option for building the synthetic portfolio in Module B, providing a rich set of features for analysis. |

## Required Deliverables

The following items must be submitted for evaluation:

- **Source Code:** A link to a public source code repository (e.g., GitHub) containing the complete implementation.
- **Live Demonstration:** A functional, live demonstration of the application, not to exceed 5 minutes.
- **Presentation Materials:** A brief presentation (maximum 7 slides) summarizing the project architecture, challenges, and results.

# S&P Global & Crisil Campus Hackathon 2026

## Submission Guidelines

### How to Package & Ship Your Case Study Deliverables

We recommend keeping your entire submission self-contained inside a single Public GitHub repository. If you prefer cloud storage for your slides or video walkthrough, you may host them on YouTube (unlisted), provided permissions are explicitly configured for public access (see Section 6).

| # | Deliverable | What to Submit | Where to Put It | Key Requirements |
|---|---|---|---|---|
| 1 | Source Code & Architecture | Working code + architecture flow/diagram | Public GitHub repo | Include dependencies and clear setup + run commands. |
| 2 | Presentation Deck | 5–7 slides (PDF or PPTX) | /docs/presentation.pdf in repo, link in README | Cover problem approach, system design, key results, and domain impact. |
| 3 | Demo Video Walkthrough | 10 mins screen recording | Link in README.md — YouTube (unlisted) | Quick end-to-end working demonstration of your prototype or dashboard. |
| 4 | All data to be submitted | CSV/JSON used to run your prototype | /data folder in repo | Submit all data and data sources used, including synthetic data. Do not use proprietary data. |

Finalists will pitch their solutions and demonstrate their innovation to the jury panel.

| # | Deliverable | What to Submit | Where to Put It | Key Requirements |
|---|---|---|---|---|
| 1 | Live Jury Pitch | Live demo + Q&A | Virtual jury panel session | Present your solution and answer technical questions. |

### Content Guidance for Deck, Video & Pitch

**Presentation Deck (5–7 slides) — suggested outline**

| Slide | Topic | What to show |
|---|---|---|
| 1 | Title | Project title, candidate name, college |
| 2 | Problem & Approach | Business problem in your own words; your solution approach |
| 3 | System Design | Architecture diagram and data flow |
| 4 | Implementation Highlights | Key modules, tech choices and why |
| 5 | Key Results | Outputs, metrics, screenshots, efficiency gains vs. naive approach |
| 6 | Domain Impact | Why it matters from a use case or business standpoint |
| 7 | Limitations & Next Steps | (Optional) Assumptions, gaps, future work |

**Demo Video (10 mins) suggested flow**

- Intro (≈30s): Problem and what the prototype does.
- Setup/Run (≈30s): Show the app starting from the README commands.
- End-to-end walkthrough (≈2–3 min): Input data → processing → output/dashboard.
- Results & impact (≈30–60s): Key outputs and why they matter.

**Live Jury Pitch (recommended: presentation + Q&A)**

For selected candidates, we will have a live jury pitch round as well.  
Expect technical questions on your design choices, code, data assumptions, and use case interpretation.  
Have the prototype running and ready to demo live.

### Suggested Repository Structure

A clean, standardized folder structure helps the review team evaluate and run your code efficiently:

```text
<college>-<candidate-name>-hackathon/
├── README.md                <-- Overview, setup steps, architecture & demo link
├── requirements.txt         <-- Dependencies (or package.json / pom.xml)
├── LICENSE                  <-- Mandatory (MIT recommended; repo must be public)
├── src/                     <-- Application, data pipelines, and model source code
├── data/                    <-- Sample or synthetic dataset used for demo
└── docs/
    ├── presentation.pdf     <-- 5–7 slide presentation deck
    └── architecture.png     <-- High-resolution architecture diagram
```

**Naming convention:** `<college>-<candidate-name>-hackathon` (avoid generic names like my-hackathon-project to prevent collisions).  
**Entry point:** Any entry point is allowed, but the exact run command must be stated in the README Quickstart.

### Mandatory README.md Template

Every repository must contain a README.md at the root folder. Please use the structure below to make your submission easy to review and run.

````markdown
# [Project Title] - S&P Global & Crisil Campus Hackathon

**Candidate Name:** [Your Full Name]
**College Email ID:** [your_id@college.ac.in]
**College / Campus:** [Your College Name]
**Demo Video Link:** [YouTube / Unlisted]
**Slide Deck Link (if hosted externally):**

## 1. Project Overview / Problem Statement & Approach
A concise 2–3 paragraph summary explaining the business/technical problem you
solved and your solution approach.

## 2. Architecture & Tech Stack
- Overview of system design and data flow (embed your architecture diagram here).
- Key frameworks, databases, and AI/ML libraries used.

## 3. Dataset Used
- Source/nature of sample data (synthetic or publicly available).
- Any assumptions made about the data.

## 4. Quickstart & Installation
Runtime: [e.g., Python 3.11 / Node 20 / Java 17] on [OS tested]

Step-by-step commands to set up the environment and run your code locally:
```bash
git clone <your-repo-url>
cd <repo-folder>
pip install -r requirements.txt
<your run command, e.g. python main.py>
```

## 5. Key Results & Domain Impact
- What your prototype outputs/demonstrates.
- Why it matters from a use case or business standpoint.
````

### Access & Permissions Checklist: before submitting your links, verify:

- **GitHub Visibility:** Repository must be Public. Private repositories cannot be accessed or evaluated by the review team.
- **Demo Video:** Must be on YouTube as Unlisted. Confirm it plays in an incognito/private window.
- **Cloud Storage Access for slides (No Google Drive / OneDrive Please):**
  - Do not leave permissions as "Restricted to your university/organization domain".
  - Set link access explicitly to "Anyone with the link can view".
  - Test the link in an incognito/private browser window before submitting.

### AI Usage & Academic Integrity

**AI Usage:** Use of AI assistance is generally allowed for building your solution, provided it is used with integrity and full academic/professional honesty.

### Team Composition

**Team Size:** 1 (individual submissions only).

### IP Ownership & Confidentiality

This case study is a simulated exercise for learning and assessment purposes only.  
All work you submit (code, deck, video) is your own for portfolio/demonstration use.  
Do not source, reference, or reuse any real/confidential client data, names, or engagement details from S&P Global or Crisil. Use only synthetic or publicly available data.

### Dataset Source Clarity

No restriction on dataset source — you may use synthetic data you generate yourself or publicly available datasets, as long as it reasonably represents the problem you're solving.  
Clearly state the dataset source and any assumptions in the "Dataset Used" section of your README.

### Disqualification Criteria

A submission will be disqualified if any of the following apply:

- Repository is private or inaccessible at review time.
- Demo video or slide deck links are broken, expired, or restricted (not publicly viewable).
- No live jury pitch attendance with no prior communication/valid reason.
- Evidence of plagiarism or submission of a pre-existing/copied project.
- Use of real confidential client data in violation of Section 9.

### Tie-Breaker Rule

If two or more participants receive the same total score, ranking will be decided by (in order):

1. Higher score in Domain Understanding.
2. Higher score in Presentation & Communication.
3. Earlier submission timestamp.

### Live Pitch Logistics

Live jury pitch sessions will be pre-scheduled; participants will be informed of their date/time slot in advance, so no separate booking is needed.

### Support & Contact

For submission issues or queries, contact: [support-email@placeholder.com]

### Additional Guidelines

**Repository hygiene:** Keep the repo free of large binary/data dumps.  
**Commit history:** Prefer incremental commits showing your build process over a single final commit.  
**Final submission version:** Ensure all final files and links are submitted before the deadline. Updates made after the deadline may not be considered.

### Submission Deadline & Format

Please submit your final GitHub repository link, demo video link, and presentation deck by the communicated deadline through the official submission form. Live jury pitch slots will be shared with shortlisted participants in advance.
