import re
import pytesseract
import pdf2image
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime

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
    promotion_type: str  #"percentage_off", "buy_1_get_2", "direct_reduction"
    additional_info: dict

class DiscountExtractor:
    """
    Class to handle the extraction of discount information from a PDF file.
    
    This class converts PDF pages into images, preprocesses these images for improved OCR accuracy,
    extracts text regions using contour detection, and applies regular expressions to parse discount data.
    """

    def __init__(self):
        """
        Initialize the DiscountExtractor with OCR configuration and regular expression patterns.
        
        The OCR configuration is set up to use Tesseract's default engine in a mode that is best
        for reading blocks of text, and it is configured for the German language.
        """
        # Tesseract OCR configuration: 
        # --oem 3: Use the default OCR engine
        # --psm 6: Assume a uniform block of text
        # -l deu: Use German language for OCR
        self.ocr_config = r'--oem 3 --psm 6 -l deu'
        
        # Regular expression pattern for matching price values.
        # Matches prices with an optional Euro symbol or 'EUR', followed by a number with two decimals.
        self.price_pattern = r'(?:€|EUR)?\s*(\d+[,.]\d{2})'
        
        # Pattern for matching discount percentages (e.g., "-20%")
        self.discount_pattern = r'-(\d+)%'
        
        # Pattern for matching dates in the format dd.mm.yy or dd.mm.yyyy.
        self.date_pattern = r'(\d{1,2}\.\d{1,2}\.(?:\d{2}|\d{4}))'
        
        # Dictionary of patterns for various promotion types.
        # 'gratis': Pattern for promotions such as "2 + 1 GRATIS" (buy 2, get 1 free).
        # 'statt': Pattern for "statt" promotions indicating direct price reductions.
        # 'ersparnis': Pattern for promotions that mention savings (Ersparnis).
        self.promotion_patterns = {
            'gratis': r'(\d+\s*\+\s*\d+)\s*GRATIS',
            'statt': r'statt\s*' + self.price_pattern,
            'ersparnis': r'Ersparnis[^\d]*(\d+[,.]\d{2})'
        }

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess the input image to enhance OCR performance.
        
        The preprocessing steps include converting the image to grayscale, applying adaptive
        thresholding to create a binary image, denoising the image, and adding a white border.
        
        Args:
            image (np.ndarray): The input image in BGR format.
            
        Returns:
            np.ndarray: The processed image, which is ready for OCR.
        """
        # Convert the BGR image to a grayscale image.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to convert the grayscale image to a binary image.
        # This step helps in highlighting the text against the background.
        thresh = cv2.adaptiveThreshold(
            gray,                    # Source image in grayscale.
            255,                     # Maximum value to use with THRESH_BINARY.
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # Adaptive method: Gaussian weighted sum.
            cv2.THRESH_BINARY,       # Threshold type: Binary.
            11,                      # Block size: Size of the neighborhood used for thresholding.
            2                        # Constant subtracted from the mean.
        )
        
        # Denoise the image using fast Non-Local Means Denoising.
        # This removes small artifacts and noise which may interfere with OCR.
        denoised = cv2.fastNlMeansDenoising(thresh)
        
        # Add a white border around the image.
        # Borders can help improve OCR results by preventing text at the edge from being cut off.
        bordered = cv2.copyMakeBorder(
            denoised,  # Source image.
            10, 10, 10, 10,  # Border sizes: top, bottom, left, right.
            cv2.BORDER_CONSTANT,  # Border type: constant value.
            value=[255, 255, 255]  # Border color: white.
        )
        
        return bordered

    def extract_text_regions(self, image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Identify and extract regions of text within an image using contour detection.
        
        The method locates external contours in the processed binary image. For each contour,
        it extracts a bounding rectangle and applies OCR to retrieve the text. Only regions with
        sufficient area (to avoid noise) and non-empty OCR results are returned.
        
        Args:
            image (np.ndarray): A preprocessed binary image.
            
        Returns:
            List[Tuple[str, np.ndarray]]: A list of tuples where each tuple contains:
                - The text extracted from the region.
                - The image region (as a numpy array) that produced the text.
        """
        # Find external contours in the binary image.
        contours, _ = cv2.findContours(
            image,                  # Input binary image.
            cv2.RETR_EXTERNAL,      # Retrieve only the outer contours.
            cv2.CHAIN_APPROX_SIMPLE # Compress horizontal, vertical, and diagonal segments.
        )
        
        text_regions = []
        # Loop through each contour found.
        for contour in contours:
            # Obtain the bounding rectangle coordinates (x, y, width, height) for the contour.
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter out regions that are too small (likely noise).
            if w * h > 100:
                # Crop the region from the image.
                region = image[y:y+h, x:x+w]
                # Use Tesseract OCR to extract text from the cropped region.
                text = pytesseract.image_to_string(region, config=self.ocr_config)
                # If the region contains any text (after stripping whitespace), add it to the list.
                if text.strip():
                    text_regions.append((text, region))
        
        return text_regions

    def parse_price(self, text: str) -> Optional[float]:
        """
        Parse a price value from a given text using a regular expression.
        
        The function looks for patterns that resemble a price (e.g., "€12,34" or "EUR 12.34"),
        replaces a comma with a dot for correct float conversion, and returns the price as a float.
        
        Args:
            text (str): The text containing the price information.
            
        Returns:
            Optional[float]: The extracted price as a float, or None if no price was found.
        """
        # Search for a price using the defined price_pattern.
        match = re.search(self.price_pattern, text)
        if match:
            # Replace comma with dot to match Python's float format.
            price_str = match.group(1).replace(',', '.')
            return float(price_str)
        return None

    def extract_date_range(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Extract start and end dates from the text.
        
        The function uses a regular expression to find all dates in the text. If two or more dates
        are found, it attempts to convert the first two into datetime objects assuming the format
        'dd.mm.yyyy'. If successful, the start and end dates are returned.
        
        Args:
            text (str): The text containing date information.
            
        Returns:
            Tuple[Optional[datetime], Optional[datetime]]:
                A tuple containing the start date and end date, or (None, None) if extraction fails.
        """
        # Find all date matches in the text.
        dates = re.findall(self.date_pattern, text)
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

    def parse_promotion(self, text: str) -> Tuple[str, dict]:
        """
        Determine the type of promotion present in the text and extract relevant details.
        
        The method checks for various promotion patterns such as "GRATIS" offers,
        percentage discounts (e.g., "-20%"), and direct price reductions indicated by "statt".
        It returns the promotion type along with any additional details.
        
        Args:
            text (str): The text from which promotion details should be extracted.
            
        Returns:
            Tuple[str, dict]:
                - A string indicating the promotion type ('buy_x_get_y', 'percentage_off',
                  'direct_reduction', or 'unknown').
                - A dictionary containing additional extracted information.
        """
        # Check for "buy X get Y free" promotions using the 'gratis' pattern.
        gratis_match = re.search(self.promotion_patterns['gratis'], text)
        if gratis_match:
            # Split the matched numbers separated by '+' (e.g., "2+1").
            numbers = gratis_match.group(1).split('+')
            return 'buy_x_get_y', {
                'buy': int(numbers[0].strip()),
                'get': int(numbers[1].strip())
            }
            
        # Check for percentage discount promotions (e.g., "-20%").
        discount_match = re.search(self.discount_pattern, text)
        if discount_match:
            return 'percentage_off', {
                'discount_percentage': int(discount_match.group(1))
            }
            
        # Check for direct price reduction promotions using the 'statt' pattern.
        statt_match = re.search(self.promotion_patterns['statt'], text)
        if statt_match:
            return 'direct_reduction', {
                'original_price': self.parse_price(statt_match.group(0))
            }
            
        # If no known promotion patterns are found, return 'unknown' with empty details.
        return 'unknown', {}

    def extract_discount_info(self, text: str, region: np.ndarray) -> Optional[DiscountInfo]:
        """
        Extract comprehensive discount information from a text region.
        
        The function first checks if the text contains any price-like patterns. It then attempts
        to extract the product name (assuming it is the first line of the text), finds all prices,
        determines the original and discounted prices, identifies promotion details, and extracts any
        valid date ranges. If an explicit discount percentage is not available, it calculates one.
        
        Args:
            text (str): The OCR-extracted text from a specific region.
            region (np.ndarray): The image region corresponding to the text.
            
        Returns:
            Optional[DiscountInfo]: A DiscountInfo object containing the parsed discount information,
                                    or None if the text does not contain price information.
        """
        # Check if the text contains any price-like patterns; if not, skip processing.
        if not re.search(self.price_pattern, text):
            return None
            
        # Split the text into lines; assume the first line contains the product name.
        lines = text.split('\n')
        product_name = lines[0].strip()
        
        # Extract prices from each line and filter out any None values.
        prices = [self.parse_price(line) for line in lines]
        prices = [p for p in prices if p is not None]
        
        # Sort the prices in descending order; the highest price is often the original price.
        prices.sort(reverse=True)
        original_price = prices[0] if len(prices) > 1 else None
        discounted_price = prices[-1] if prices else None
        
        # Determine the promotion type and extract additional details using the promotion parser.
        promotion_type, promotion_details = self.parse_promotion(text)
        
        # Extract the start and end dates (if any) from the text.
        start_date, end_date = self.extract_date_range(text)
        
        # If there is no explicit discount percentage, calculate it from the original and discounted prices.
        if original_price and discounted_price and 'discount_percentage' not in promotion_details:
            discount_percentage = ((original_price - discounted_price) / original_price) * 100
            promotion_details['calculated_discount_percentage'] = round(discount_percentage, 1)
        
        # Return a DiscountInfo object populated with the extracted information.
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
        # Iterate over each page image.
        for image in images:
            # Convert the PIL image to a numpy array for processing with OpenCV.
            image_np = np.array(image)
            
            # Preprocess the image to enhance text detection and OCR accuracy.
            processed = self.preprocess_image(image_np)
            
            # Extract regions that potentially contain text.
            text_regions = self.extract_text_regions(processed)
            
            # Process each detected text region to extract discount information.
            for text, region in text_regions:
                discount_info = self.extract_discount_info(text, region)
                if discount_info:
                    all_discounts.append(discount_info)
        
        return all_discounts
