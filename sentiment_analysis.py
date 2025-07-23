import os
import sys
import time
import torch
import clip
from PIL import Image
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_clip_model = None
_clip_processor = None

def load_clip_model_once():
    """Load CLIP model only once and store globally"""
    global _clip_model, _clip_processor
    
    if _clip_model is None:
        logger.info("Loading CLIP model ViT-B/32 on cpu (one time only)")
        _clip_model, _clip_processor = clip.load("ViT-B/32", device="cpu")
        logger.info("CLIP model loaded successfully")
    
    return _clip_model, _clip_processor

class CLIPSentimentAnalyzer:
    def __init__(self, model_name="ViT-B/32"):
        """Initialize CLIP model for sentiment analysis"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.model, self.preprocess = load_clip_model_once()
        # self.model, self.preprocess = clip.load(model_name, device=self.device)
        
        # For open-ended sentiment analysis
        self.sentiment_adjectives = [
            # Basic emotions
            "happy", "joyful", "cheerful", "euphoric", "blissful", "content", "elated", "ecstatic",
            "sad", "melancholic", "sorrowful", "gloomy", "wistful", "bittersweet", "mournful",
            "angry", "frustrated", "tense", "agitated", "fierce", "hostile", "irritated",
            "fearful", "anxious", "nervous", "worried", "startled", "apprehensive",
            
            # Aesthetic & mood
            "peaceful", "calm", "serene", "tranquil", "zen", "meditative", "soothing", "relaxing",
            "exciting", "thrilling", "exhilarating", "dynamic", "electrifying", "stimulating", "energetic",
            "mysterious", "enigmatic", "cryptic", "intriguing", "mystical", "eerie", "haunting",
            "romantic", "intimate", "tender", "passionate", "loving", "dreamy", "enchanting",
            "dramatic", "intense", "powerful", "striking", "bold", "theatrical", "cinematic",
            
            # Visual qualities
            "bright", "luminous", "radiant", "glowing", "vibrant", "dazzling", "brilliant",
            "dark", "shadowy", "moody", "somber", "dim", "subdued", "muted",
            "colorful", "vivid", "saturated", "rich", "lush", "rainbow", "prismatic",
            "minimalist", "clean", "simple", "sparse", "uncluttered", "geometric", "abstract",
            "busy", "chaotic", "crowded", "overwhelming", "complex", "cluttered", "frantic",
            
            # Atmospheres & environments
            "urban", "metropolitan", "cosmopolitan", "industrial", "architectural", "futuristic",
            "natural", "organic", "earthy", "wild", "pristine", "untouched", "raw",
            "rustic", "vintage", "retro", "nostalgic", "classic", "timeless", "antique",
            "modern", "contemporary", "sleek", "sophisticated", "polished", "refined",
            "cozy", "warm", "inviting", "homey", "comfortable", "intimate", "snug",
            
            # Activity & energy
            "playful", "whimsical", "fun", "lighthearted", "carefree", "spirited", "mischievous",
            "serious", "formal", "professional", "businesslike", "stern", "solemn", "grave",
            "artistic", "creative", "expressive", "imaginative", "innovative", "inspired",
            "adventurous", "exploratory", "daring", "brave", "courageous", "bold",
            "lazy", "leisurely", "slow", "gentle", "soft", "mild", "subtle",
            
            # Special occasions & moods
            "festive", "celebratory", "holiday", "party", "carnival", "jubilant", "ceremonial",
            "spiritual", "sacred", "divine", "heavenly", "ethereal", "transcendent",
            "luxurious", "opulent", "lavish", "elegant", "fancy", "glamorous", "prestigious",
            "humble", "modest", "simple", "plain", "ordinary", "everyday", "common",
            
            # Weather & seasonal
            "sunny", "bright", "summery", "tropical", "warm", "hot", "blazing",
            "cold", "chilly", "freezing", "icy", "wintry", "frosty", "crisp",
            "stormy", "tempestuous", "turbulent", "windy", "breezy", "gusty",
            "foggy", "misty", "hazy", "cloudy", "overcast", "dreary",
            
            # Textures & qualities
            "smooth", "rough", "textured", "grainy", "silky", "velvety", "crisp",
            "fresh", "new", "pristine", "clean", "pure", "untainted",
            "aged", "weathered", "worn", "distressed", "patinated", "faded",
            "sharp", "focused", "clear", "detailed", "precise", "crisp",
            "blurry", "soft", "dreamy", "hazy", "impressionistic", "abstract"
        ]
    
    def _prepare_text_embeddings(self):
        """Pre-compute text embeddings for all sentiment descriptions"""
        all_texts = []
        self.label_mapping = []
        
        for sentiment, descriptions in self.sentiment_labels.items():
            for desc in descriptions:
                all_texts.append(desc)
                self.label_mapping.append(sentiment)
        
        # Tokenize and encode all texts
        text_tokens = clip.tokenize(all_texts).to(self.device)
        
        with torch.no_grad():
            self.text_embeddings = self.model.encode_text(text_tokens)
            self.text_embeddings = self.text_embeddings / self.text_embeddings.norm(dim=-1, keepdim=True)
    
    def analyze_sentiment(self, image_path, top_k, confidence_threshold):
        """Analyze sentiment of an image using CLIP"""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Get image embedding
            with torch.no_grad():
                image_embedding = self.model.encode_image(image_input)
                image_embedding = image_embedding / image_embedding.norm(dim=-1, keepdim=True)
        
            # Open-ended sentiment analysis
            text_queries = [f"this image feels {adj}" for adj in self.sentiment_adjectives]
            text_tokens = clip.tokenize(text_queries).to(self.device)
            
            with torch.no_grad():
                text_embeddings = self.model.encode_text(text_tokens)
                text_embeddings = text_embeddings / text_embeddings.norm(dim=-1, keepdim=True)
            
            # Calculate similarities
            similarities = torch.matmul(image_embedding, text_embeddings.T)
            similarities = similarities.cpu().numpy()[0]
            
            # Create sentiment-score pairs and filter by threshold
            sentiment_scores = list(zip(self.sentiment_adjectives, similarities))
            sorted_sentiments = sorted(sentiment_scores, key=lambda x: x[1], reverse=True)
            filtered_sentiments = [(sentiment, score) for sentiment, score in sorted_sentiments 
                                    if score >= confidence_threshold]
            
            return filtered_sentiments[:top_k] if filtered_sentiments else [('uncertain', 0.0)]
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for {image_path}: {e}")
            return [('unknown', 0.0)]

def generate_sentiment_with_clip(image_path, confidence_threshold):
    """Generate sentiment using CLIP model"""
    analyzer = CLIPSentimentAnalyzer()
    sentiments = analyzer.analyze_sentiment(image_path, top_k=1, confidence_threshold=confidence_threshold)
    
    # Get the top sentiment
    top_sentiment, confidence = sentiments[0]
    
    logger.info(f"Sentiment: {top_sentiment} (confidence: {confidence:.3f})")
    return top_sentiment, confidence

def analyze_single_image(image_path, confidence_threshold):
    """Analyze sentiment for a single image"""
    image_path = Path(image_path)
    
    if not image_path.exists():
        logger.error(f"Image {image_path} does not exist")
        return None
    
    # Initialize analyzer
    analyzer = CLIPSentimentAnalyzer()
    
    logger.info(f"Analyzing image: {image_path.name}")
    
    sentiments = analyzer.analyze_sentiment(image_path, top_k=3, confidence_threshold=confidence_threshold)
    
    if not sentiments or sentiments[0][0] in ['uncertain', 'unknown']:
        logger.warning(f"No confident sentiment found (threshold: {confidence_threshold})")
        print(f"\nSentiment Analysis Results for: {image_path.name}")
        print("=" * 50)
        print(f"No confident sentiment detected (confidence threshold: {confidence_threshold})")
        return None
    
    sentiments_list = [ sentiment for sentiment, _ in sentiments ]
    # Print all sentiments
    print(f"Sentiment Analysis Results for: {image_path.name}")
    print(f"- Detected sentiments above threshold ({confidence_threshold}):")
    for sentiment, score in sentiments:
        print(f"  - {sentiment}: {score:.3f}")
    print(f"sentiments_list: {sentiments_list}")
    return sentiments_list

def analyze_image_batch(photos_dir, output_file, confidence_threshold):
    """Analyze sentiment for all images in a directory"""
    photos_dir = Path(photos_dir)
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    
    # Initialize analyzer once for batch processing
    analyzer = CLIPSentimentAnalyzer()
    
    results = []
    total_files = len([f for f in photos_dir.iterdir() if f.suffix.lower() in image_extensions])
    logger.info(f"Found {total_files} images to analyze with confidence threshold: {confidence_threshold}")
    
    processed = 0
    uncertain_count = 0
    
    for image_file in photos_dir.iterdir():
        if image_file.suffix.lower() in image_extensions:
            processed += 1
            logger.info(f"Processing {processed}/{total_files}: {image_file.name}")
            
            sentiments = analyzer.analyze_sentiment(image_file, top_k=3, confidence_threshold=confidence_threshold)
            
            if not sentiments or sentiments[0][0] in ['uncertain', 'unknown']:
                logger.warning(f"  → No confident sentiment (threshold: {confidence_threshold})")
                uncertain_count += 1
                continue
            
            top_sentiment, confidence = sentiments[0]
            
            result = {
                'filename': image_file.name,
                'sentiment': top_sentiment,
                'confidence': confidence,
                'all_sentiments': sentiments
            }
            results.append(result)
            
            logger.info(f"  → {top_sentiment} ({confidence:.3f})")
    
    logger.info(f"Analysis complete: {len(results)} confident results, {uncertain_count} uncertain (below threshold)")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Image Sentiment Analysis Results\n")
        f.write("=" * 50 + "\n")
        f.write(f"Confidence Threshold: {confidence_threshold}\n")
        f.write(f"Total Images: {total_files}\n")
        f.write(f"Confident Results: {len(results)}\n")
        f.write(f"Uncertain Results: {uncertain_count}\n\n")
        
        for result in results:
            f.write(f"File: {result['filename']}\n")
            f.write(f"Primary Sentiment: {result['sentiment']} (confidence: {result['confidence']:.3f})\n")
            f.write("All sentiments above threshold:\n")
            for sentiment, score in result['all_sentiments']:
                f.write(f"  - {sentiment}: {score:.3f}\n")
            f.write("\n" + "-" * 30 + "\n\n")
    
    logger.info(f"Results saved to {output_file}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clip_sentiment.py <image_file_or_directory> [options]")
        print("Options:")
        print("  --open-ended              Use open-ended sentiment analysis")
        print("  --threshold <value>       Set confidence threshold (default: 0.25)")
        print("  --output <file>           Set output file for batch analysis")
        print("\nExamples:")
        print("  python clip_sentiment.py photo.jpg")
        print("  python clip_sentiment.py photo.jpg --open-ended --threshold 0.4")
        print("  python clip_sentiment.py assets/img/photos --threshold 0.5 --output results.txt")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_file = "sentiment_results.txt"
    confidence_threshold = 0.2
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--threshold":
            if i + 1 < len(sys.argv):
                confidence_threshold = float(sys.argv[i + 1])
                i += 1
            else:
                print("Error: --threshold requires a value")
                sys.exit(1)
        elif arg == "--output":
            if i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 1
            else:
                print("Error: --output requires a filename")
                sys.exit(1)
        i += 1
    
    if not os.path.exists(input_path):
        logger.error(f"Path {input_path} does not exist")
        sys.exit(1)
    
    input_path = Path(input_path)
    
    if input_path.is_file():
        # Single image analysis
        logger.info(f"Starting CLIP sentiment analysis on single image (threshold: {confidence_threshold})")
        ts = time.time()
        sentiments_list = analyze_single_image(input_path, confidence_threshold)
        if sentiments_list:
            logger.info(f"Analysis complete! (inference time: {time.time() - ts:.2f}s)")
    else:
        # Directory analysis
        logger.info(f"Starting CLIP sentiment analysis on {input_path} (threshold: {confidence_threshold})")
        results = analyze_image_batch(input_path, output_file, confidence_threshold)
        logger.info(f"Analysis complete! {len(results)} confident results found")