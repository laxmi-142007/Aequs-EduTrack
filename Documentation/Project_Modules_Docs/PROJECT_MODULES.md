# Aequs EduTrack — System Overview & Module Guide

## Executive Summary
**Aequs EduTrack** is an integrated enterprise platform designed to manage educational empowerment initiatives across partner schools, student enrollments, academic performance, warehouse/laptop inventory, volunteer activities, and system analytics.

---

## Database Architecture & SQL Connection

The platform is designed with flexible database connectivity to support local development, enterprise database servers, and cloud production environments.

### 1. Local Enterprise SQL Server Connection
* **Database Engine**: Microsoft SQL Server (`mssql`)
* **Host / Instance**: `.\SQLEXPRESS` (Microsoft SQL Server Express)
* **Database Name**: `Aequs_EduTrack`
* **Driver**: ODBC Driver 18 for SQL Server (configured with `TrustServerCertificate=yes`)

### 2. Local File-Based Database Option
* **Database Engine**: SQLite 3
* **File Location**: Local root database file (`db.sqlite3`)

### 3. Production Cloud Database Connection
* **Database Engine**: PostgreSQL
* **Environment Configuration**: Connected dynamically via `DATABASE_URL` (configured for cloud deployments on Render.com)

---

## 1. Academics Module (Academic Records & Performance Tracking)

### Overview
Manages student academic progress, exam scores, percentage calculations, class rankings, promotion statuses, and course catalog structures.

### Key Capabilities & Features

* **Interactive Academic Portal**
  * Serves as the primary operational dashboard for academic records.
  * Displays real-time metrics for total academic records, promoted students, conditional promotions, and non-promoted students.

* **Record & Grade Management**
  * Complete lifecycle management for adding, updating, searching, and removing student academic records.
  * Automatic calculation of percentages, grade standings, and student rankings.

* **Course Catalog (Course Master)**
  * Maintains an active catalog of courses and subject streams, categorized by educational levels and display ordering.

* **Batch Operations & CSV Uploads**
  * Automated batch uploading of academic performance files.
  * Validation rules ensuring valid marks, non-negative totals, and proper promotion statuses, backed by atomic database transactions that roll back cleanly if errors occur.

---

## 2. Schools Module (Partner School Administration)

### Overview
Tracks partner educational institutions, contact personnel, headmasters, grade-wise student strengths, milestones achieved, and allocated infrastructure resources.

### Key Capabilities & Features

* **School Directory & Administration**
  * Comprehensive database of partner schools, geographical locations, UDISE codes, and operational statuses.

* **Contact & Headmaster Tracking**
  * Manages contact personnel information, primary phone numbers, emails, and assigned headmasters for each school.

* **Student Enrollment Strength**
  * Tracks grade-by-grade student headcount breakdown across Grades 1 through 10.
  * Export options to download enrollment statistics as CSV reports.

* **Milestones & Resource Tracker**
  * Records major institutional achievements, grants, and infrastructure expansions.
  * Tracks equipment and facilities allocated to each institution, such as computer labs, smart classrooms, and libraries.

---

## 3. Inventory Module (Supply Chain & Laptop Distribution)

### Overview
Oversees warehouse supplies (stationery, school bags, kits) and tracks the lifecycle of laptops issued to students.

### Key Capabilities & Features

* **Inventory & Warehouse Dashboard**
  * Real-time visibility into current stock levels, low-stock thresholds, supply distributions, and hardware allocations.

* **Stock Management & Movements**
  * Tracks stock-in (receipt of items from donors/vendors) and stock-out (distribution to schools/students) with a complete audit history.
  * Triggers low-stock alerts when inventory drops below predefined safety thresholds.

* **Laptop Lifecycle & Handover**
  * Registers laptop inventory with serial numbers, hardware specifications, and current status.
  * Manages student laptop assignments, handover records, and hardware return processing.

* **Export & Inventory Reporting**
  * Generates downloadable inventory summaries and stock balance reports.

---

## 4. Students Module (Student Roster & Enrollment)

### Overview
Maintains central student identity records across all partner schools.

### Key Capabilities & Features

* **Student Roster & Profiles**
  * Searchable table of enrolled students, admission numbers, gender, current class, and assigned schools.

* **Enrollment Workflows**
  * Supports both single student enrollment forms and bulk CSV batch importing for mass student onboarding.

---

## 5. Volunteers Module (Volunteer Engagement)

### Overview
Tracks community volunteer participation, contribution hours, and event assignments.

### Key Capabilities & Features

* **Volunteer Directory & Profiles**
  * Manages volunteer contact info, skills, availability, and engagement histories.

* **Service Hour & Impact Logging**
  * Logs volunteer service hours, task contributions, and activity records.

* **Event Deployment**
  * Assigns volunteers to educational workshops, supply distribution drives, and school visits.

---

## 6. Core System & Analytics Module (Global Metrics & Reporting)

### Overview
Provides system-wide analytics, executive dashboards, user authentication, and audit tracking.

### Key Capabilities & Features

* **Executive Dashboard**
  * Consolidates high-level KPIs: active school count, total enrolled students, laptop allocation totals, and recent activity timelines.

* **Audit Logging & System Reports**
  * Maintains system-wide activity logs and compliance reports for tracking changes across all modules.

---

## 7. Database Utilities & Initializer

### Overview
Development tools for environment initialization and data seeding.

### Key Capabilities & Features

* **Automated Data Seeder**
  * Initializes structured mock datasets across schools, students, academic performance, and laptop inventory for local development and testing.
