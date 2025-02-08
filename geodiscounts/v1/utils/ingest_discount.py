from geodiscounts.models import Discount, Retailer
from typing import Dict

def ingest_discount_data(data: Dict[str, str]) -> None:
    """
    Ingest discount data into the database.

    This function creates or updates a retailer and a discount based on the provided data.

    Args:
        data (Dict[str, str]): A dictionary containing discount information, including:
            - retailer_name: The name of the retailer.
            - description: A detailed description of the discount.
            - discount_code: Unique code for redeeming the discount.
            - expiration_date: Expiration date of the discount.
            - location: Geographical location where the discount is valid (Point object).

    Returns:
        None
    """
    try:
        retailer_name = data.get('retailer_name')
        discount_description = data.get('description')
        discount_code = data.get('discount_code')
        expiration_date = data.get('expiration_date')
        location = data.get('location')  # Ensure this is a Point object

        # Create or get the retailer
        retailer, created = Retailer.objects.get_or_create(name=retailer_name)

        # Create the discount
        discount = Discount(
            retailer=retailer,
            description=discount_description,
            discount_code=discount_code,
            expiration_date=expiration_date,
            location=location  # Ensure this is a Point object
        )
        discount.save()
        print(f"Saved discount: {discount.description} for retailer: {retailer.name}")
    except Exception as e:
        print(f"Error ingesting discount data: {e}")
