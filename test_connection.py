from sqlalchemy import create_engine, text

# Database connection string
DB_CONNECTION = "mssql+pyodbc://adminuser:Password1234!@videoappservereastus2.database.windows.net/videoAppDB?driver=ODBC+Driver+17+for+SQL+Server"

# Create the engine
engine = create_engine(DB_CONNECTION)

try:
    # Attempt to connect to the database
    with engine.connect() as conn:
        print("Connected to the database successfully.")
except Exception as e:
    print(f"Database connection error: {e}")
