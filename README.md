# ProcurementAnalyser
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/celery-%2337814A.svg?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/redis-CC0000.svg?&style=for-the-badge&logo=redis&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)

An automated monitoring and analysis system for Ukrainian public tenders. This project integrates with Prozorro public procurement APIs to track tender updates, analyzes tender complaints using Natural Language Processing (NLP) to identify potential violations, and notifies subscribed users of significant changes.

### Key Features

*   **Tender Monitoring:** Browse, search, and view comprehensive data for public tenders.
*   **Change History Tracking:** Access a detailed, versioned history of all modifications for any given tender.
*   **Automated Complaint Analysis:** View the results of an NLP-based analysis on tender complaints, which scores and categorizes potential procurement violations.
*   **User Subscriptions:** Authenticated users can subscribe to specific tenders to receive email notifications about any tracked changes.
*   **On-Demand Tracking:** Users can add new tenders to the system by providing an OCID, initiating the monitoring process.

### System Architecture

The application is built on a monolithic architecture that emphasizes separation of concerns through distinct layers. This design ensures the system is robust, maintainable, and relatively easy to extend despite being a single deployable unit.

*   **Asynchronous Task Processing:** The core of the system relies on **Celery** with Redis for managing background tasks. A `celery beat` scheduler automates periodic jobs like data crawling, synchronization, and sending notifications. Tasks are routed to dedicated queues (`default` for general processing, `email_queue` for notifications) to prioritize and isolate workloads, ensuring the system remains responsive.
*   **Service Layer:** Business logic is encapsulated within specialized services. For example, the `CrawlerService` fetches data from external APIs, the `DataProcessor` handles data synchronization and validation, the `ComplaintAnalysisService` performs NLP, and the `NotificationService` manages user alerts.
*   **Repository Pattern:** Database interactions are abstracted away using the Repository Pattern, with `TenderRepository` as the primary one. This decouples the business logic from the data access layer, improving modularity and making the system easier to test and maintain.
*   **Data Flow:** The process begins with scheduled crawlers (`CrawlerService`) fetching data from the Prozorro public APIs. The `DataProcessor` service then syncs this data with the local database, meticulously recording every change. When modifications are detected, the `NotificationService` generates a report and dispatches an email task to the `email_queue`, alerting subscribed users.

### Core Concept: NLP-Powered Complaint Analysis

The most important feature of this project is its ability to analyze unstructured text from tender complaints to automatically identify and score potential procurement violations. This turns qualitative complaint data into quantitative, actionable insights. The process is divided into two main phases: an offline topic discovery phase and a real-time analysis and scoring phase.

#### 1. Topic Discovery and Keyword Extraction (Offline Analysis)

The foundation of the analysis is a set of domain-specific keywords. These were not manually created but were discovered through an unsupervised machine learning approach:

*   **Corpus Creation:** A large corpus of historical complaint descriptions was gathered from public tender data. The `TextProcessingService` was used to clean and normalize this raw text, preparing it for analysis.
*   **Topic Modeling:** Using `scikit-learn`, topic modeling using `CountVectorizer` and `NMF` was applied to the corpus. The goal was to identify thematic structures in the complaint texts.
*   **Keyword Identification:** After methodically determining the optimal number of topics via `topic_modeling/topic_n_elbow`, the most representative keywords for each topic were extracted. These topics were then manually interpreted and mapped to specific "violation domains". The resulting keywords are stored in `keywords.json`.

This data-driven approach ensures that the analysis is based on patterns found in real-world data, rather than on predefined assumptions.

#### 2. Real-Time Analysis and Scoring

When a new complaint is added to a tender in the system, an asynchronous Celery task triggers the `ComplaintAnalysisService` to perform the following steps:

*   **Linguistic Processing:** The complaint's text is processed using a `spaCy` NLP pipeline. The primary step is **lemmatization**, which reduces words to their base or dictionary form (e.g., "changing," "changed" -> "change"). This standardizes the text for accurate keyword matching.
*   **Keyword Matching:** The system compares the lemmatized tokens from the complaint against the pre-computed list of keywords for each violation domain.
*   **Logarithmic Scoring:** A score is calculated for each domain based on the keywords found. Instead of simply counting occurrences, the system uses a logarithmic weighting function (`math.log1p`). This means the first occurrence of a keyword adds a significant value to the score, while each subsequent occurrence of the same keyword provides a diminishing return. This approach rewards complaints that contain a diverse set of violation-related keywords over those that simply repeat the same term.
*   **Cumulative Score Update:** The calculated scores from the new complaint are added to the tender's existing `ViolationScore`. This cumulative model allows the system to build a dynamic risk profile for a tender over time, as multiple complaints can progressively increase the score in one or more violation domains. The results, including highlighted keywords in the original text, are then displayed to the user.

### Tech Stack

*   **Backend:** Python, Flask
*   **Database:** PostgreSQL with SQLAlchemy ORM
*   **Asynchronous Tasks:** Celery with Redis as the message broker
*   **NLP & Machine Learning:** spaCy, scikit-learn, langtools
*   **Frontend Templating:** Jinja2
*   **Containerization:** Docker, Docker Compose

### Setup & Installation

This project is fully containerized using Docker, so you do not need to install Python or PostgreSQL on your host machine.

**Prerequisites:**
*   Docker
*   Docker Compose

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/demianchuk-o/ProcurementAnalyser.git
    cd ProcurementAnalyser
    ```

2.  **Configure environment variables:**
    Create a `.env` file by copying the example file.
    ```bash
    cp .env.example .env
    ```
    Open the new `.env` file and fill in the required values, especially:
    *   `SECRET_KEY` and `JWT_SECRET_KEY` for the Flask application.
    *   `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for the PostgreSQL database.
    *   `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` for email notifications.

3.  **Build and run the application:**
    Use Docker Compose to build the images and start all the services (web app, database, Redis, and Celery workers).
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs the containers in detached mode. The first time you run this, Docker will download the necessary base images and build the application image, which may take a few minutes.

    Database migrations are applied automatically when the `web` container starts.

### Usage

#### Web Application
Once the containers are running, the web application will be accessible at `http://localhost:5000`.

#### Background Services
The `docker-compose.yml` configuration automatically starts all necessary background services:
*   **`celery_beat`**: Schedules periodic tasks like crawling for new tender data.
*   **`celery_default`**: A worker that processes general tasks, including data processing and NLP analysis.
*   **`celery_email`**: A dedicated worker for sending email notifications.

You can view the logs for any service using `docker-compose logs -f <service_name>`, for example: `docker-compose logs -f celery_default`.

#### Running Integration Tests
The project includes a separate Docker Compose configuration for running integration tests against a dedicated test database.

1.  **Run tests:**
    ```bash
    make integration-test
    ```
    This command will spin up a test environment, run the `pytest` suite, and then shut down.

2.  **Clean up test environment:**
    If you need to manually stop and remove the test containers and volumes, run:
    ```bash
    make integration-clean
    ```