# utils.py
import re
import cv2
import numpy as np
from datetime import datetime
import pytesseract
from typing import List, Tuple, Optional

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocess the input image to enhance OCR performance.

    Steps:
        1. Convert the image from BGR to grayscale.
        2. Apply adaptive thresholding to create a binary image.
        3. Denoise the image using fast Non-Local Means Denoising.
        4. Add a white border around the image to prevent text from being cut off.

    Args:
        image (np.ndarray): Input image in BGR format.

    Returns:
        np.ndarray: The processed image ready for OCR.
    """
    # Convert the image to grayscale.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding to highlight text.
    thresh = cv2.adaptiveThreshold(
        gray,  # Source image in grayscale.
        255,  # Maximum value to use with THRESH_BINARY.
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # Adaptive method: Gaussian weighted sum.
        cv2.THRESH_BINARY,  # Threshold type: Binary.
        11, # Block size: Size of the neighborhood used for thresholding.
        2 # Constant subtracted from the mean.
    )
    
    # Denoise the image to remove small artifacts.
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    # Add a white border around the image.
    # Borders can help improve OCR results by preventing text at the edge from being cut off.
    bordered = cv2.copyMakeBorder(
        denoised, # Source image.
        10, 10, 10, 10, # Border sizes: top, bottom, left, right.
        cv2.BORDER_CONSTANT, # Border type: constant value.
        value=[255, 255, 255] # Border color: white.
    )
    
    return bordered

def extract_text_regions(image: np.ndarray, ocr_config: str) -> List[Tuple[str, np.ndarray]]:
    """
    Identify and extract regions of text from a preprocessed binary image using contour detection.

    Args:
        image (np.ndarray): A preprocessed binary image.
        ocr_config (str): OCR configuration string for Tesseract.

    Returns:
        List[Tuple[str, np.ndarray]]:
            A list of tuples where each tuple contains:
                - The text extracted from the region.
                - The corresponding image region as a numpy array.
    """
    # Find external contours.
    contours, _ = cv2.findContours(
        image, # Input binary image.
        cv2.RETR_EXTERNAL, # Retrieve only the outer contours.
        cv2.CHAIN_APPROX_SIMPLE # Compress horizontal, vertical, and diagonal segments.
    )
    
    text_regions = []
    # Loop through each contour found.
    for contour in contours:
        # Obtain the bounding rectangle coordinates (x, y, width, height) for the contour.
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter out regions that are too small (likely noise).
        if w * h > 100:  # Filter out small regions.
            # Crop the region from the image.
            region = image[y:y+h, x:x+w]
            # Use Tesseract OCR to extract text from the cropped region.
            text = pytesseract.image_to_string(region, config=ocr_config)
            # If the region contains any text (after stripping whitespace), add it to the list.
            if text.strip():
                text_regions.append((text, region))
                
    return text_regions

def parse_price(text: str) -> Optional[float]:
    """
    Parse a price value from text.

    The function searches for price patterns such as "€12,34" or "EUR 12.34",
    replaces commas with dots, and converts the result to a float.

    Args:
        text (str): The text containing price information.

    Returns:
        Optional[float]: The price as a float if found, else None.
    """
    price_pattern = r'(?:€|EUR)?\s*(\d+[,.]\d{2})'
    match = re.search(price_pattern, text) # Search for a price using the defined price_pattern.
    if match:
        # Replace comma with dot to match Python's float format.
        price_str = match.group(1).replace(',', '.')
        return float(price_str)
    return None

def extract_date_range(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Extract start and end dates from the text.

    Dates are expected in the format dd.mm.yyyy or dd.mm.yy. If at least two dates
    are found, they are converted to datetime objects.

    Args:
        text (str): Text containing date information.

    Returns:
        Tuple[Optional[datetime], Optional[datetime]]:
            A tuple containing the start and end dates or (None, None) if extraction fails.
    """
    date_pattern = r'(\d{1,2}\.\d{1,2}\.(?:\d{2}|\d{4}))'
    dates = re.findall(date_pattern, text) # Find all date matches in the text.
    if len(dates) >= 2:
        try:
            # Convert the first date to a datetime object.
            start_date = datetime.strptime(dates[0], '%d.%m.%Y')
            # Convert the second date to a datetime object.
            end_date = datetime.strptime(dates[1], '%d.%m.%Y')
            return start_date, end_date
        except ValueError:
            # If date conversion fails, ignore and return None.
            pass
    return None, None

def parse_promotion(text: str) -> Tuple[str, dict]:
    """
    Identify the type of promotion in the text and extract relevant details.

    Checks for:
        - "Buy X get Y free" promotions (e.g., "2+1 GRATIS").
        - Percentage discounts (e.g., "-20%").
        - Direct price reductions indicated by "statt".

    Args:
        text (str): The text containing promotion information.

    Returns:
        Tuple[str, dict]:
            A tuple with:
                - The promotion type as a string.
                - A dictionary of additional promotion details.
    """
    # Define patterns for promotion detection.
    discount_pattern = r'-(\d+)%'
    promotion_patterns = {
        'gratis': r'(\d+\s*\+\s*\d+)\s*GRATIS',
        'statt': r'statt\s*(?:€|EUR)?\s*(\d+[,.]\d{2})',
        'ersparnis': r'Ersparnis[^\d]*(\d+[,.]\d{2})'
    }
    
    # Check for "buy X get Y free" promotions.
    gratis_match = re.search(promotion_patterns['gratis'], text)
    if gratis_match:
        # Split the matched numbers separated by '+' (e.g., "2+1").
        numbers = gratis_match.group(1).split('+')
        return 'buy_x_get_y', {
            'buy': int(numbers[0].strip()),
            'get': int(numbers[1].strip())
        }
    
    # Check for percentage discount promotions (e.g., "-20%").
    discount_match = re.search(discount_pattern, text)
    if discount_match:
        return 'percentage_off', {
            'discount_percentage': int(discount_match.group(1))
            }
    
    # Check for direct price reduction promotions.
    statt_match = re.search(promotion_patterns['statt'], text)
    if statt_match:
        price = parse_price(statt_match.group(0))
        return 'direct_reduction', {'original_price': price}
    
    return 'unknown', {}
