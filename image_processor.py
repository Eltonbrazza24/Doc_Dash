import cv2
import pytesseract
from PIL import Image
import io
import base64
import requests
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Configuração
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def ocr_with_gemini_vision(image_path):
    """Realiza OCR usando Gemini Vision API"""
    try:
        # Carrega e processa a imagem
        img = Image.open(image_path)
        
        # Converte para base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Prompt para extração de texto
        prompt = """
        Extraia todo o texto visível nesta imagem e retorne em formato JSON estruturado.
        Se conseguir identificar o tipo de documento (RG, CNH, Holerite, etc.), organize os dados nos campos apropriados.
        Caso contrário, retorne o texto extraído de forma organizada.
        
        Exemplo de resposta:
        {
          "tipo_documento": "RG/CNH/HOLERITE/OUTRO",
          "texto_extraido": "texto completo da imagem",
          "campos_identificados": {
            "campo1": "valor1",
            "campo2": "valor2"
          }
        }
        """
        
        # Requisição para Gemini Vision API
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": img_str
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            try:
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                # Tenta extrair JSON da resposta
                if "{" in text_response and "}" in text_response:
                    start = text_response.find("{")
                    end = text_response.rfind("}") + 1
                    json_str = text_response[start:end]
                    return json.loads(json_str)
                else:
                    return {"texto_extraido": text_response, "tipo_documento": "OUTRO"}
            except (KeyError, json.JSONDecodeError) as e:
                return {"erro": f"Erro ao processar resposta: {str(e)}", "resposta_bruta": data}
        else:
            return {"erro": f"Erro na API Gemini: {response.status_code}", "detalhes": response.text}
            
    except Exception as e:
        return {"erro": f"Erro no OCR com Gemini Vision: {str(e)}"}

def extract_text_from_image_tesseract(image_path):
    """Extração de texto usando Tesseract (fallback)"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Não foi possível abrir a imagem.")
        text = pytesseract.image_to_string(img, lang='por')
        return {
            "texto": text.strip(),
            "dimensoes": f"{img.shape[1]}x{img.shape[0]}",
            "metodo": "Tesseract"
        }
    except Exception as e:
        raise Exception(f"Erro no Tesseract: {str(e)}")

def extract_text_from_image(image_path):
    """Função principal para extração de texto de imagens"""
    try:
        # Primeiro tenta com Gemini Vision (mais preciso)
        if GEMINI_API_KEY:
            gemini_result = ocr_with_gemini_vision(image_path)
            
            if "erro" not in gemini_result:
                return {
                    "status": "success",
                    "type": "IMAGE",
                    "data": {
                        **gemini_result,
                        "metodo_processamento": "Gemini_Vision"
                    },
                    "metadata": {
                        "arquivo": os.path.basename(image_path),
                        "processado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                }
        
        # Fallback para Tesseract se Gemini falhar ou não estiver configurado
        tesseract_result = extract_text_from_image_tesseract(image_path)
        
        return {
            "status": "success",
            "type": "IMAGE",
            "data": tesseract_result,
            "metadata": {
                "arquivo": os.path.basename(image_path),
                "processado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "arquivo": os.path.basename(image_path)
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(extract_text_from_image(sys.argv[1]), indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "message": "Nenhum arquivo fornecido"}))