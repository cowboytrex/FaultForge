# simulated data source for testing purposes
SERVICES = [
    {
        "id": 1,
        "name": "Authentication",
        "status": "active",

    },
    {
        "id": 2,
        "name": "Notifications",
        "status": "active"
    },
    {
        "id": 3,
        "name": "Reporting",
        "status": "Maintenance"
    }
]

def get_services(database_available=True):
    """
    Simulate retrieving service records from a database.

    Raises ConnectionError when the database is unavailable.
    """

    if not database_available:
        raise ConnectionError("Database conncection failed")
    
    return SERVICES