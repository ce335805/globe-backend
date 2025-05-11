from fastapi import FastAPI
from app.service.population_service import get_population_data

# Create the FastAPI app
app = FastAPI()

# Root route to display the entire population dataset
@app.get("/")
def read_population_data():
    try:
        # Retrieve the population data as a dictionary
        population_data = get_population_data()
        return {"population_data": population_data}

    except Exception as e:
        # Handle potential errors gracefully
        return {"error": str(e)}
