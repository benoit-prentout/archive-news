# 📬 Newsletter Archiver

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-orange)](https://pages.github.com/)

An automated DevOps solution that captures incoming newsletters from Gmail, sanitizes them (removing forward history), and archives them as a static website hosted on GitHub Pages.

**🔗 [Accéder à l'archive en ligne / Access Online Archive](https://benoit-prentout.github.io/archive-news/)**

---

## 🚀 Features

* **Smart Ingestion:** Fetches emails from Gmail via IMAP (Label: `Github/archive-newsletters`).
* **Advanced Processing:**
    * **Sanitization:** Automatically removes "Forward" headers (`Fwd:`, `Tr:`) and history blocks (quotes) to keep only the original content.
    * **Structure:** Organizes each newsletter in its own dedicated folder to prevent asset conflicts.
    * **Metadata:** Extracts the original email date (not the archiving date) for accurate sorting.
* **Asset Management:** Downloads remote images locally to ensure long-term preservation.
* **Static Site Generation:** Auto-generates a responsive `index.html` with a clean footer and legal notices.
* **CI/CD Pipeline:** Runs automatically every 30 minutes via GitHub Actions.

---

## 🛠️ Tech Stack

* **Language:** Python 3.9
* **Libraries:**
    * `imaplib` & `email`: For email server interaction.
    * `BeautifulSoup4`: For HTML parsing and DOM manipulation.
    * `Requests`: For downloading assets.
* **Automation:** GitHub Actions (CRON scheduler).
* **Hosting:** GitHub Pages.

## 🛠️ Architecture

```mermaid
graph LR
A[Gmail (Alias + Filter)] -- IMAP --> B(Python Script via GitHub Actions)
B -- Extract HTML & Clean History --> C[Sanitize & Download Images]
C -- Commit changes --> D[GitHub Repository (/docs)]
D -- Auto Deploy --> E[GitHub Pages Website]


