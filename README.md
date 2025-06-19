# ProcurementAnalyser

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