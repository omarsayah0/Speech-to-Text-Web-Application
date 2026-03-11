# 🎙️ Speech-to-Text Web Application

A Dockerized Speech-to-Text web application built with **FastAPI** that allows users to upload audio files and convert them into text using AI transcription models. The project demonstrates backend architecture concepts such as authentication, role-based access control, job processing, and containerized deployment.

---

## 📖 Introduction

This project demonstrates how to build a **production-style backend system** for audio transcription. Users can upload audio files through a web interface, and the system processes them using speech-to-text models to generate text output.

The system also includes authentication, role management, and an admin dashboard for managing users and transcription jobs.

---

## 🧾 Table of Contents

- [Introduction](#-introduction)
- [Features](#-Features)
- [Installation](#Installation)
- [Usage](#-Usage)
- [System Architecture](#-System-Architecture)
- [Configuration](#-Configuration)
- [Examples](#-Examples)
- [Troubleshooting](#-Troubleshooting)
- [Dependencies](#-Dependencies)
- [Project Structure](#-Project-Structure)
- [Output Snapshots](#-Output-Snapshots)
- [Contributors](#-Contributors)
- [License](#-License)

---

## 📁 Project Structure

```text
.
├── backend/              # FastAPI backend (API, authentication, STT processing)
├── frontend/             # Web interface and templates
├── Dockerfile            # Docker image configuration
├── docker-compose.yml    # Container orchestration
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## ✨ Features

- Audio file upload and transcription
- Speech-to-Text processing pipeline
- JWT-based authentication system
- Role-Based Access Control (Admin / User)
- Admin dashboard for user and subscription management
- Job-based transcription processing
- Dockerized deployment environment

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/your-username/speech-to-text-app.git
cd speech-to-text-app
```

Build and start the application using Docker:

```bash
docker compose up --build
```

The application will start locally.

---

## Usage

1. Open your browser and navigate to:

```text
http://localhost:8000
```

2. Upload an audio file.
3. The system processes the audio and returns the generated transcription.
4. Admin users can access the dashboard to manage users and transcription jobs.

---

## System Architecture

The application follows a typical **backend + frontend architecture**:

### Frontend
- Handles user interface and file uploads

### Backend (FastAPI)
- API endpoints
- Authentication
- Job management
- Speech-to-text processing

### Database
- Stores users, transcription jobs, and results

### Docker
- Provides consistent development and deployment environments

---

## Configuration

Key components used in the system:

- Python backend using **FastAPI**
- Database integration for storing jobs and users
- Docker containers for isolated environments
- JWT authentication for secure user sessions

---

## Examples

Typical workflow:

1. User uploads an audio file
2. Backend processes the file
3. Speech-to-text model generates transcription
4. Result is stored and displayed to the user

---

## Troubleshooting

If the application does not start:

- Ensure Docker is installed and running
- Check that port **8000** is available
- Rebuild containers using:

```bash
docker compose up --build
```

If dependencies fail:

```bash
pip install -r requirements.txt
```

---

## 📦 Dependencies

From `requirements.txt`:

- FastAPI
- Uvicorn
- PostgreSQL client libraries
- Speech-to-text model dependencies
- Jinja2
- Python standard libraries

---

## Output Snapshots

<img width="1892" height="942" alt="dd1d4528-aa22-4fc8-a4ea-f78402f41370" src="https://github.com/user-attachments/assets/0833800c-6b5e-4513-a83b-f75b0af90517" />
<img width="1899" height="952" alt="2c454d57-42c1-4f09-8ef6-ee7b1a24c23a" src="https://github.com/user-attachments/assets/bca08c94-a96c-4d3e-a9c9-d8cbaa73dc2d" />
<img width="1901" height="952" alt="205c69f0-cf3e-444a-be23-1420550b7295" src="https://github.com/user-attachments/assets/25e7584f-72d1-485a-b5ce-20ca402d40e6" />
<img width="1908" height="941" alt="2347183a-5f6d-43fa-8c47-60aecf5503ba" src="https://github.com/user-attachments/assets/0a7995a5-c55e-4e10-bdc5-7ff9aa4292c9" />
<img width="1904" height="938" alt="e4ff223c-b65d-4c9a-870f-067249971ccd" src="https://github.com/user-attachments/assets/88db68ea-3643-4b92-8d63-66aa3aad30ef" />
<img width="1890" height="937" alt="a897d97a-7f65-461e-bdaf-e5ded174ed6b" src="https://github.com/user-attachments/assets/f5756d71-a862-4277-b0dc-5f2ac13b5755" />
<img width="1898" height="934" alt="fe1b76d1-3e80-4e03-9342-9a706e800da2" src="https://github.com/user-attachments/assets/3e407424-842a-4266-aae4-9f8aea141c99" />
<img width="1910" height="941" alt="55f61f8a-4da3-451e-ac32-8d6db4ff7374" src="https://github.com/user-attachments/assets/d7f97500-fc3d-4957-9a90-c0962e215eea" />
<img width="1903" height="942" alt="6d8addf2-8ccc-453d-980c-882817779d1c" src="https://github.com/user-attachments/assets/588e80d9-a86e-43f4-8d39-12392be7d3dc" />
<img width="1912" height="955" alt="73fa01f7-f4c9-4691-bfa1-1f53d328538c" src="https://github.com/user-attachments/assets/26bf9d03-58e7-4b29-ae14-58bbdc3a404e" />
<img width="1919" height="1132" alt="18388957-6942-465e-a7a6-31ac0cbafe40" src="https://github.com/user-attachments/assets/e45754bd-a536-44a0-aa6e-0df5cdcb23bd" />

---

## 👥 Contributors

**Omar Alethamat** – AI Engineer

Feel free to open issues or pull requests to contribute.

---

## 📄 License

This project is licensed under the MIT License.
