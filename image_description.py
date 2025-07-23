from transformers import BlipProcessor, BlipForConditionalGeneration, AutoProcessor, Blip2ForConditionalGeneration
from PIL import Image
import sys
import time
import torch
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_model_info(model_size):
    """Return model name and type based on size argument"""
    models = {
        'base': {
            'processor': BlipProcessor,
            'model': BlipForConditionalGeneration,
            'name': "Salesforce/blip-image-captioning-base",
            'description': "BLIP Base - Fast, good quality"
        },
        'large': {
            'processor': BlipProcessor,
            'model': BlipForConditionalGeneration, 
            'name': "Salesforce/blip-image-captioning-large",
            'description': "BLIP Large - Slower, better quality"
        },
        'blip2': {
            'processor': AutoProcessor,
            'model': Blip2ForConditionalGeneration,
            'name': "Salesforce/blip2-opt-2.7b",
            'description': "BLIP-2 - Most advanced, slowest"
        }
    }
    
    if model_size not in models:
        available = list(models.keys())
        raise ValueError(f"Invalid model size '{model_size}'. Choose from: {available}")
    
    return models[model_size]

def describe_image(image_path, model_size='base'):
    """Generate image description using specified model size"""
    
    # Get model configuration
    model_info = get_model_info(model_size)
    logger.info(f"Loading {model_info['description']}...")
    
    # Load model and processor
    processor = model_info['processor'].from_pretrained(model_info['name'])
    
    if model_size == 'blip2':
        # BLIP-2 uses float16 for efficiency
        model = model_info['model'].from_pretrained(
            model_info['name'], 
            torch_dtype=torch.float16
        )
    else:
        model = model_info['model'].from_pretrained(model_info['name'])
    
    # Load and process image
    image = Image.open(image_path)
    inputs = processor(image, return_tensors="pt")
    
    # Generate caption with appropriate parameters
    if model_size == 'blip2':
        # BLIP-2 generation
        generated_ids = model.generate(**inputs, max_new_tokens=50)
        caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    else:
        # BLIP generation
        out = model.generate(**inputs, max_length=100, num_beams=5)
        caption = processor.decode(out[0], skip_special_tokens=True)
    
    return caption

def print_usage():
    """Print usage information"""
    logger.info("Usage: python image_caption.py <image_path> [model_size]")
    logger.info("\nModel sizes:")
    logger.info("  base   - BLIP Base (default) - Fast, good quality")
    logger.info("  large  - BLIP Large - Slower, better quality") 
    logger.info("  blip2  - BLIP-2 - Most advanced, slowest")
    logger.info("\nExamples:")
    logger.info("  python image_caption.py photo.jpg")
    logger.info("  python image_caption.py photo.jpg base")
    logger.info("  python image_caption.py photo.jpg large")
    logger.info("  python image_caption.py photo.jpg blip2")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print_usage()
        sys.exit(1)
    
    image_path = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) == 3 else 'base'
    
    try:
        ts = time.time()
        caption = describe_image(image_path, model_size)
        latency = time.time() - ts
        logger.info(f"Model: {model_size}")
        logger.info(f"Latency: {latency:.2f}s")
        logger.info(f"Caption: {caption}")
        
    except ValueError as e:
        logger.info(f"Error: {e}")
        print_usage()
        sys.exit(1)
    except FileNotFoundError:
        logger.info(f"Error: Image file '{image_path}' not found")
        sys.exit(1)
    except Exception as e:
        logger.info(f"Error processing image: {e}")
        sys.exit(1)