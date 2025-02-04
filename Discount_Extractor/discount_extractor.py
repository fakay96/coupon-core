import re
import pytesseract
import pdf2image
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from utils import (
    preprocess_image,
    extract_text_regions,
    parse_price,
    extract_date_range,
    parse_promotion
)

@dataclass
class DiscountInfo:
    """
    Data class to store extracted discount information for a product.
    
    Attributes:
        product_name (str): Name or description of the product.
        original_price (Optional[float]): The original (higher) price before discount.
        discounted_price (Optional[float]): The lower price after discount.
        discount_percentage (Optional[float]): The percentage discount, if available.
        start_date (Optional[datetime]): Start date of the discount promotion.
        end_date (Optional[datetime]): End date of the discount promotion.
        promotion_type (str): The type of promotion detected. 
    """
    product_name: str
    original_price: Optional[float]
    discounted_price: Optional[float]
    discount_percentage: Optional[float]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    promotion_type: str
    additional_info: dict

class DiscountExtractor:
    """
    Extracts discount information from PDF files.
    
    Class to handle the extraction of discount information from a PDF file.
    
    This class converts PDF pages into images, preprocesses these images for improved OCR accuracy,
    extracts text regions using contour detection, and applies regular expressions to parse discount data.
    """
    def __init__(self):
        # OCR configuration for Tesseract (configured for German)
        self.ocr_config = r'--oem 3 --psm 6 -l deu'

    def extract_discount_info(self, text: str) -> Optional[DiscountInfo]:
        """
        Extract comprehensive discount information from a text region.
        """
        # Skip if no price-like pattern is found.
        if not re.search(r'(?:€|EUR)?\s*(\d+[,.]\d{2})', text):
            return None

        # Assume the first line is the product name.
        lines = text.split('\n')
        product_name = lines[0].strip()
        
        # Extract prices from all lines.
        prices = [parse_price(line) for line in lines]
        prices = [p for p in prices if p is not None]
        prices.sort(reverse=True)
        original_price = prices[0] if len(prices) > 1 else None
        discounted_price = prices[-1] if prices else None
        
        # Get promotion type and details.
        promotion_type, promotion_details = parse_promotion(text)
        
        # Extract valid date range.
        start_date, end_date = extract_date_range(text)
        
        # Calculate discount percentage if not explicitly provided.
        if original_price and discounted_price and 'discount_percentage' not in promotion_details:
            discount_percentage = ((original_price - discounted_price) / original_price) * 100
            promotion_details['calculated_discount_percentage'] = round(discount_percentage, 1)
        
        return DiscountInfo(
            product_name=product_name,
            original_price=original_price,
            discounted_price=discounted_price,
            discount_percentage=promotion_details.get('discount_percentage'),
            start_date=start_date,
            end_date=end_date,
            promotion_type=promotion_type,
            additional_info=promotion_details
        )

    def process_pdf(self, pdf_path: str) -> List[DiscountInfo]:
        """
        Process the entire PDF file and extract discount information from each page.
        
        The PDF file is converted into individual images (one per page). For each page,
        the image is preprocessed to enhance OCR results, text regions are identified via
        contour detection, and discount information is extracted from each text region.
        
        Args:
            pdf_path (str): The file path to the PDF containing discount leaflets.
            
        Returns:
            List[DiscountInfo]: A list of DiscountInfo objects extracted from the PDF.
        """
        # Convert each page of the PDF into an image using pdf2image.
        images = pdf2image.convert_from_path(pdf_path)
        
        all_discounts = []
        #  Iterate over each page image.
        for image in images:
            # Convert the PIL image to a numpy array for processing with OpenCV.
            image_np = np.array(image)
            
            # Preprocess the image to enhance text detection and OCR accuracy.
            processed = preprocess_image(image_np)
            
            # Extract regions that potentially contain text.
            text_regions = extract_text_regions(processed, self.ocr_config)
            
            # Process each detected text region to extract discount information.
            for text, _ in text_regions:
                discount_info = self.extract_discount_info(text)
                if discount_info:
                    all_discounts.append(discount_info)
        return all_discounts
