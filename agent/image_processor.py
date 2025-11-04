"""
Image processing utilities for workflow screenshot refinement.
Implements 3x3 grid-based cropping system for focusing on relevant UI elements.
"""
import os
import logging
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Handles image cropping and processing for workflow screenshots.
    Uses a 3x3 grid system to identify and extract relevant UI regions.
    """

    def __init__(self, grid_size: int = 3, padding_percent: float = 0.05):
        """
        Initialize image processor.

        Args:
            grid_size: Size of grid (3 = 3x3 grid)
            padding_percent: Percentage of padding to add around cropped region (0.05 = 5%)
        """
        self.grid_size = grid_size
        self.padding_percent = padding_percent
        logger.info(f"[IMAGE_PROCESSOR] Initialized with {grid_size}x{grid_size} grid, {padding_percent*100}% padding")

    def crop_to_grid(
        self,
        image_path: str,
        grid_locations: List[Tuple[int, int]],
        output_path: str
    ) -> bool:
        """
        Crop image to specified grid locations with padding.

        Args:
            image_path: Path to input image
            grid_locations: List of (row, col) tuples indicating cells to include
            output_path: Path to save cropped image

        Returns:
            True if successful, False otherwise

        Example:
            crop_to_grid("step_003.png", [(3, 2), (3, 3)], "step_003_refined.png")
            # Crops to bottom-middle and bottom-right cells
        """
        logger.info(f"[IMAGE_PROCESSOR] Cropping {image_path} to grid cells: {grid_locations}")

        try:
            # Load image
            if not os.path.exists(image_path):
                logger.error(f"[IMAGE_PROCESSOR] Image not found: {image_path}")
                return False

            image = Image.open(image_path)
            width, height = image.size
            logger.debug(f"[IMAGE_PROCESSOR] Image dimensions: {width}x{height}")

            # Validate grid locations
            if not self._validate_grid_locations(grid_locations):
                logger.warning(f"[IMAGE_PROCESSOR] Invalid grid locations: {grid_locations}, using center region")
                grid_locations = [(2, 1), (2, 2), (2, 3)]  # Fallback to middle row for context

            # Calculate bounding box
            bbox = self._calculate_bounding_box(
                grid_locations,
                width,
                height
            )
            logger.debug(f"[IMAGE_PROCESSOR] Bounding box before padding: {bbox}")

            # Add padding
            bbox_padded = self._add_padding(bbox, width, height)
            logger.debug(f"[IMAGE_PROCESSOR] Bounding box with padding: {bbox_padded}")

            # Crop image
            cropped = image.crop(bbox_padded)
            logger.debug(f"[IMAGE_PROCESSOR] Cropped dimensions: {cropped.size}")

            # Save cropped image
            cropped.save(output_path, quality=95)
            logger.info(f"[IMAGE_PROCESSOR] Saved cropped image: {output_path}")

            return True

        except Exception as e:
            logger.error(f"[IMAGE_PROCESSOR] Crop failed: {str(e)}", exc_info=True)
            return False

    def _validate_grid_locations(self, grid_locations: List[Tuple[int, int]]) -> bool:
        """
        Validate that grid locations are within bounds.

        Args:
            grid_locations: List of (row, col) tuples

        Returns:
            True if all locations are valid
        """
        if not grid_locations:
            logger.warning("[IMAGE_PROCESSOR] No grid locations provided")
            return False

        for row, col in grid_locations:
            if not (1 <= row <= self.grid_size and 1 <= col <= self.grid_size):
                logger.warning(f"[IMAGE_PROCESSOR] Invalid grid location: ({row}, {col})")
                return False

        return True

    def _calculate_bounding_box(
        self,
        grid_locations: List[Tuple[int, int]],
        width: int,
        height: int
    ) -> Tuple[int, int, int, int]:
        """
        Calculate bounding box encompassing all grid locations.

        Args:
            grid_locations: List of (row, col) tuples
            width: Image width
            height: Image height

        Returns:
            Tuple of (x_min, y_min, x_max, y_max)

        Grid System:
            (1,1) (1,2) (1,3)
            (2,1) (2,2) (2,3)
            (3,1) (3,2) (3,3)
        """
        cell_width = width / self.grid_size
        cell_height = height / self.grid_size

        x_coords = []
        y_coords = []

        for row, col in grid_locations:
            # Calculate cell boundaries
            # Note: col determines x, row determines y
            x_start = (col - 1) * cell_width
            x_end = col * cell_width
            y_start = (row - 1) * cell_height
            y_end = row * cell_height

            x_coords.extend([x_start, x_end])
            y_coords.extend([y_start, y_end])

        # Find bounding box
        x_min = int(min(x_coords))
        x_max = int(max(x_coords))
        y_min = int(min(y_coords))
        y_max = int(max(y_coords))

        logger.debug(f"[IMAGE_PROCESSOR] Calculated bbox: ({x_min}, {y_min}, {x_max}, {y_max})")

        return (x_min, y_min, x_max, y_max)

    def _add_padding(
        self,
        bbox: Tuple[int, int, int, int],
        width: int,
        height: int
    ) -> Tuple[int, int, int, int]:
        """
        Add padding around bounding box, ensuring it stays within image bounds.

        Args:
            bbox: Original bounding box (x_min, y_min, x_max, y_max)
            width: Image width
            height: Image height

        Returns:
            Padded bounding box (x_min, y_min, x_max, y_max)
        """
        x_min, y_min, x_max, y_max = bbox

        # Calculate padding in pixels
        bbox_width = x_max - x_min
        bbox_height = y_max - y_min

        x_padding = int(bbox_width * self.padding_percent)
        y_padding = int(bbox_height * self.padding_percent)

        logger.debug(f"[IMAGE_PROCESSOR] Adding padding: x={x_padding}px, y={y_padding}px")

        # Apply padding with bounds checking
        x_min_padded = max(0, x_min - x_padding)
        y_min_padded = max(0, y_min - y_padding)
        x_max_padded = min(width, x_max + x_padding)
        y_max_padded = min(height, y_max + y_padding)

        return (x_min_padded, y_min_padded, x_max_padded, y_max_padded)

    def get_grid_visualization(
        self,
        image_path: str,
        output_path: str
    ) -> bool:
        """
        Generate visualization of grid overlay on image (for debugging).

        Args:
            image_path: Path to input image
            output_path: Path to save visualization

        Returns:
            True if successful
        """
        logger.info(f"[IMAGE_PROCESSOR] Creating grid visualization: {output_path}")

        try:
            from PIL import ImageDraw

            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            width, height = image.size

            cell_width = width / self.grid_size
            cell_height = height / self.grid_size

            # Draw vertical lines
            for i in range(1, self.grid_size):
                x = int(i * cell_width)
                draw.line([(x, 0), (x, height)], fill='red', width=3)

            # Draw horizontal lines
            for i in range(1, self.grid_size):
                y = int(i * cell_height)
                draw.line([(0, y), (width, y)], fill='red', width=3)

            # Draw grid labels
            for row in range(1, self.grid_size + 1):
                for col in range(1, self.grid_size + 1):
                    x = int((col - 0.5) * cell_width)
                    y = int((row - 0.5) * cell_height)
                    draw.text((x, y), f"({row},{col})", fill='red')

            image.save(output_path)
            logger.info(f"[IMAGE_PROCESSOR] Grid visualization saved: {output_path}")

            return True

        except Exception as e:
            logger.error(f"[IMAGE_PROCESSOR] Grid visualization failed: {str(e)}", exc_info=True)
            return False
