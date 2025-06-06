import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
import io
import base64
import requests
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Configuração
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def pdf_to_images(pdf_path, dpi=300):
    """Converte páginas do PDF em imagens para OCR"""
    images = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(min(len(doc), 3)):  # Limita a 3 páginas para performance
                page = doc[page_num]
                pix = page.get_pixmap(dpi=dpi)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
        return images
    except Exception as e:
        raise Exception(f"Erro ao converter PDF para imagens: {str(e)}")

def ocr_with_gemini_vision(image, doc_type="DOCUMENTO"):
    """Realiza OCR usando Gemini Vision API"""
    try:
        # Converte imagem para base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Define prompt baseado no tipo de documento
        prompts = {
            "RG": """
            Extraia do RG na imagem os seguintes campos e retorne em formato JSON:
            - nome
            - numero_rg
            - numero_cpf
            - nome_pai
            - nome_mae
            - data_nascimento
            - natural_de
            - registro_civil
            - estado_civil (Se o campo Registro Civil indicar 'CN', coloque 'solteiro'; se indicar 'CC', coloque 'casado'; caso não haja CN ou CC, deixe em branco)
            
            Exemplo de resposta:
            {
              "nome": "NOME COMPLETO",
              "numero_rg": "00.000.000-0",
              "numero_cpf": "000.000.000-00",
              "nome_pai": "NOME DO PAI",
              "nome_mae": "NOME DA MÃE",
              "data_nascimento": "DD/MM/AAAA",
              "natural_de": "CIDADE/ESTADO",
              "registro_civil": "C.NASC ...",
              "estado_civil": "solteiro/casado"
            }
            """,
            "HOLERITE": """
            Extraia do holerite na imagem os seguintes campos e retorne em formato JSON:
            - nome_funcionario
            - empresa
            - cargo
            - periodo_referencia
            - salario_bruto
            - descontos_total
            - salario_liquido
            - data_pagamento
            
            Exemplo de resposta:
            {
              "nome_funcionario": "NOME DO FUNCIONÁRIO",
              "empresa": "NOME DA EMPRESA",
              "cargo": "CARGO/FUNÇÃO",
              "periodo_referencia": "MM/AAAA",
              "salario_bruto": "R$ 0.000,00",
              "descontos_total": "R$ 000,00",
              "salario_liquido": "R$ 0.000,00",
              "data_pagamento": "DD/MM/AAAA"
            }
            """,
            "DOCUMENTO": """
            Extraia todas as informações relevantes do documento na imagem e retorne em formato JSON.
            Identifique campos como nomes, números, datas, valores e organize de forma estruturada.
            """
        }
        
        prompt = prompts.get(doc_type, prompts["DOCUMENTO"])
        
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
                    return {"texto_extraido": text_response}
            except (KeyError, json.JSONDecodeError) as e:
                return {"erro": f"Erro ao processar resposta: {str(e)}", "resposta_bruta": data}
        else:
            return {"erro": f"Erro na API Gemini: {response.status_code}", "detalhes": response.text}
            
    except Exception as e:
        return {"erro": f"Erro no OCR com Gemini Vision: {str(e)}"}

def extract_text_smart(file_path):
    """Extrai texto de forma otimizada com fallback para OCR"""
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            
            # Estratégia para documentos grandes
            if total_pages > 10:
                # Páginas prioritárias: capa, assinaturas, últimas páginas
                priority_pages = {0, 1, total_pages-1, total_pages-2}
                text = "\n".join(
                    page.get_text() 
                    for i, page in enumerate(doc) 
                    if i in priority_pages or i % 5 == 0  # + cada 5 páginas
                )
            else:
                text = "\n".join(page.get_text() for page in doc)
            
            # Se o texto extraído for muito pequeno, pode ser um PDF de imagem
            if len(text.strip()) < 100:
                return None, total_pages  # Indica que precisa de OCR
                
            return text, total_pages
    except Exception as e:
        raise Exception(f"Falha na extração: {str(e)}")

def analyze_with_gemini(text, doc_type):
    """Envia para o Gemini com prompt otimizado"""
    try:
        prompt = f"""
        Analise este documento {doc_type} e retorne UM JSON com os campos relevantes.
        Dados prioritários: nomes, números de documento, datas e valores financeiros.
        Resumo máximo: 3 linhas por página.
        Texto para análise:
        {text[:8000]}  # Limite de tokens
        """
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        raise Exception(f"Erro no Gemini: {str(e)}")

def process_document(file_path):
    try:
        # Etapa 1: Tentativa de extração rápida de texto
        text, total_pages = extract_text_smart(file_path)
        
        # Etapa 2: Identificação do tipo de documento
        if text:
            doc_type = (
                "RG" if any(kw in text.upper() for kw in ["REGISTRO GERAL", "IDENTIDADE", "CARTEIRA DE IDENTIDADE"]) else
                "HOLERITE" if any(kw in text.upper() for kw in ["HOLERITE", "CONTRA-CHEQUE", "FOLHA DE PAGAMENTO"]) else
                "OUTRO"
            )
        else:
            # Se não conseguiu extrair texto, assume que é um documento de imagem
            doc_type = "DOCUMENTO"
        
        # Etapa 3: Análise com IA
        if text and doc_type != "OUTRO":
            # Usa análise de texto tradicional
            analysis = analyze_with_gemini(text, doc_type)
        else:
            # Usa OCR com Gemini Vision
            print(f"Usando OCR com Gemini Vision para: {file_path}")
            images = pdf_to_images(file_path)
            
            if images:
                # Processa a primeira página (ou todas se necessário)
                analysis = ocr_with_gemini_vision(images[0], doc_type)
                
                # Se há múltiplas páginas, pode processar outras também
                if len(images) > 1:
                    analysis["paginas_adicionais"] = []
                    for i, img in enumerate(images[1:], 2):
                        page_analysis = ocr_with_gemini_vision(img, doc_type)
                        analysis["paginas_adicionais"].append({
                            "pagina": i,
                            "dados": page_analysis
                        })
            else:
                analysis = {"erro": "Não foi possível processar o documento"}

        return {
            "status": "success",
            "type": doc_type,
            "data": analysis,
            "metadata": {
                "arquivo": os.path.basename(file_path),
                "paginas": total_pages,
                "metodo_processamento": "OCR_Gemini_Vision" if not text else "Extracao_Texto",
                "processado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "arquivo": os.path.basename(file_path)
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(process_document(sys.argv[1]), indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "message": "Nenhum arquivo fornecido"}))