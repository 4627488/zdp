# Software Reliability Prediction System

This project is a web-based application for software reliability prediction, implementing GO, JM, and BP Neural Network models.

## Structure

- `backend/`: FastAPI backend for model training and prediction.
- `frontend/`: Vue 3 + Vite + Vuetify frontend for data visualization and interaction.

## Prerequisites

- Python 3.11+
- Node.js 18+

## Setup & Run

### 1. Backend

Open a terminal in `backend/`:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 2. Frontend

Open a new terminal in `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`.

## Usage

1. Open the frontend URL.
2. Upload `sample_data.csv` (located in the root folder).
3. Select the algorithms you want to use.
4. Adjust the training ratio if needed.
5. Click "Analyze & Predict".
6. View the results in the chart and metrics table.
