import fitz  # PyMuPDF
import google.generativeai as genai
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Configuração
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

def extract_text_smart(file_path):
    """Extrai texto de forma otimizada com prioridade para páginas-chave"""
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
        # Etapa 1: Extração rápida
        text, total_pages = extract_text_smart(file_path)
        
        # Etapa 2: Identificação do tipo
        doc_type = (
            "RG" if any(kw in text for kw in ["REGISTRO GERAL", "IDENTIDADE"]) else
            "HOLERITE" if any(kw in text for kw in ["HOLERITE", "CONTRA-CHEQUE"]) else
            "OUTRO"
        )
        
        # Etapa 3: Análise com IA (apenas para docs conhecidos)
        if doc_type != "OUTRO":
            analysis = analyze_with_gemini(text, doc_type)
        else:
            analysis = {"conteudo": text[:1500] + "..."}

        return {
            "status": "success",
            "type": doc_type,
            "data": analysis,
            "metadata": {
                "arquivo": os.path.basename(file_path),
                "paginas": total_pages,
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
        print(json.dumps(process_document(sys.argv[1]), indent=2))
    else:
        print(json.dumps({"status": "error", "message": "Nenhum arquivo fornecido"}))