import uvicorn

if __name__ == "__main__":
    print("Starting Subscription Churn Prediction FastAPI Server...")
    print("API documentation will be available at: http://localhost:8000/api/docs")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
