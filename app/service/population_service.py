import pandas as pd

def get_population_data():
    try:
        # Define the file path
        file_path = "app/data/WPP2024_GEN_F01_DEMOGRAPHIC_INDICATORS_COMPACT.xlsx"

        # Read the Excel file, specifying the correct header row
        df = pd.read_excel(file_path, header=16)

        # Filter for countries and the year 2023
        filtered_df = df[
            (df["Type"] == "Country/Area") & 
            (df["Year"] == 2023)
        ]

        # Select the required columns
        country_population = filtered_df[
            ["Region, subregion, country or area *", "Total Population, as of 1 January (thousands)"]
        ]

        # Build dictionary: {country_name: population}
        population_dict = dict(
            zip(
                country_population["Region, subregion, country or area *"],
                country_population["Total Population, as of 1 January (thousands)"]
            )
        )

        return population_dict

    except FileNotFoundError:
        print("Error: Data file not found.")
        return {}

    except Exception as e:
        print(f"Error processing data: {e}")
        return {}
