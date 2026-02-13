**Generator**

Generator is a production-grade market data and analytics pipeline powering SPXVisuals. It automates the ingestion, transformation, quantitative and fundamental analysis, chart generation, and multi-channel distribution of equity market insights related to the S&P 500 index and its constituients. The pipeline provides both technical and fundamental perspectives in a fully automated workflow.

**Core Responsibilities**
1. Data Ingestion
- Programmatically retrieves historical and daily equity data, including price, volume, and fundamentals
- Handles scheduled runs via CI/CD automation
- Produces reproducible snapshots for downstream analytics

2. Data Engineering & Transformation
- Cleans, normalizes, and aggregates raw market data
- Structures cross-sectional datasets
- Computes derived metrics
- Serializes structured outputs into JSON for front-end consumption
- Publishes version-controlled artifacts to SPXVisuals.github.io

3. Quantitative Analytics
- Cross-Sectional Analysis
- Leader/laggard identification
- Relative performance ranking
- Volume concentration and contribution metrics
- Time-Series Analysis
- Rolling return and momentum calculations
- Trend metrics and smoothing
- Relative strength evaluation

4. Fundamental & Valuation Analytics
- Extracts company-level financial metrics:  Trailing and forward price-to-earnings (P/E) ratios and market capitalization
- Performs cross-sectional fundamental ranking and screening
- Analyzes valuation dispersion across the market
- Integrates price and fundamental factors into unified analytics outputs

5. Visualization & Narrative Generation
- Programmatically generates publication-ready charts
- Dynamically creates descriptive summaries tied to quantitative and fundamental analysis
- Ensures consistency between the data, analysis, and visuals

6. Distribution & Front-End Integration
- Publishes charts to social media platforms automatically
- Generates structured JSON metadata for each visualization
- Pushes chart images and metadata to SPXVisuals.github.io
- Supports dynamic front-end rendering powered by structured, versioned data

**Tech Stack**
- Python
- Pandas
- NumPy
- JSON
- Matplotlib
- Seaborn

**Infrastructure**
- GitHub Actions automated CI/CD scheduling and workflow orchestration
- Static-site deployment via SPXVisuals.github.io
- Git-based version-controlled chart and metadata publishing
