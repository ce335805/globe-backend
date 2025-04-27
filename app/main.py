from fastapi import FastAPI

# Create the FastAPI app
app = FastAPI()

# Basic "root" route for testing
@app.get("/")
def read_root():
    return {"message": "Welcome to the Data Globe API!"}