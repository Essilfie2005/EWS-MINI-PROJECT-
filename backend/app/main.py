from fastapi import FastAPI

app = FastAPI(Title="DropOut Prediction System", version="1.0.0")


@app.get("/")
def Home():
    return {"message": "Welcome to the DropOut Prediction System API!"}
