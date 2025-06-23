from ultralytics import YOLO
import sys
from pathlib import Path

def detect_object(input_path, model_size, image_size=640, show_image=False):
    if model_size not in ['n', 's', 'm', 'l', 'x']:
        raise ValueError("Invalid model size. Choose from: 'n', 's', 'm', 'l', 'x'.")
    if not input_path:
        raise ValueError("Input path cannot be empty.")
    
    # Convert Path object to string if necessary
    input_path_str = str(input_path)
    
    # Check file extension
    if input_path_str.split('.')[-1].lower() not in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
        return f"Skip processing, unsupported file format. {input_path_str}"
    
    # Load model based on size
    model_files = {
        'n': 'yolo11n.pt',
        's': 'yolo11s.pt',
        'm': 'yolo11m.pt',
        'l': 'yolo11l.pt',
        'x': 'yolo11x.pt'
    }
    
    model = YOLO(model_files[model_size])
    results = model(input_path_str, imgsz=image_size)
    
    if show_image:
        results[0].show()
    
    detection_strings = []
    objects = []
    for result in results:
        for box in result.boxes:
            # Get class name, confidence, and bounding box coordinates
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            
            detection_str = {'object':class_name, 'confidence':confidence}
            detection_strings.append(detection_str)
            objects.append(class_name)
    
    print(f"detection result: {detection_strings}")
    if detection_strings:
        return objects
    else:
        return None

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python yolo_ultralytics.py <input_path> <model_size> [show_image]")
        print("Model sizes: 'n', 's', 'm', 'l', 'x'")
        print("show_image: 'true' or 'false' (optional, default: false)")
        sys.exit(1)
    
    input_path = sys.argv[1]
    model_size = sys.argv[2]
    show_image = len(sys.argv) == 4 and sys.argv[3].lower() == 'true'
    
    result = detect_object(input_path, model_size, show_image=show_image)
    print(result)