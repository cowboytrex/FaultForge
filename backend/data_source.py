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

def get_services():
    """Retrieve service records from our simulated database."""
    return SERVICES