import cv2
import pytesseract
import json
import sys
from datetime import datetime

def extract_text_from_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Não foi possível abrir a imagem.")
        text = pytesseract.image_to_string(img, lang='por')
        return {
            "status": "success",
            "type": "IMAGE",
            "data": {
                "texto": text.strip(),
                "dimensoes": f"{img.shape[1]}x{img.shape[0]}"
            },
            "metadata": {
                "processado_em": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(extract_text_from_image(sys.argv[1])))
    else:
        print(json.dumps({"status": "error", "message": "Nenhum arquivo fornecido"}))