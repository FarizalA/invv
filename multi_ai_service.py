import os
import json
import base64
import requests

def extract_with_gemini(file_bytes: bytes, mime_type: str, api_key: str, model_name: str = "gemini-2.5-flash") -> dict:
    from gemini_service import extract_invoice_data
    return extract_invoice_data(file_bytes, mime_type, api_key, model_name)

def extract_with_openai_compatible(file_bytes: bytes, mime_type: str, api_key: str, base_url: str, model_name: str) -> dict:
    """
    Mendukung OpenAI (GPT-4o), OpenRouter, Groq, NVIDIA NIM, DeepSeek, Together dsb.
    """
    b64_img = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_img}"

    system_prompt = (
        "Kamu adalah sistem OCR AI ekstraktor nota & bukti transfer keuangan. "
        "Kembalikan HANYA JSON valid tanpa markdown fence. Format JSON:\n"
        "{\n"
        '  "invoice_number": "Nomor invoice / referensi / masked phone",\n'
        '  "date": "YYYY-MM-DD",\n'
        '  "customer_name": "Nama pembeli / pengirim transfer",\n'
        '  "customer_initials": "Inisial nama",\n'
        '  "description": "Deskripsi transaksi",\n'
        '  "category": "Kategori (Jasa Layanan/Penjualan/Transfer/Lainnya)",\n'
        '  "bank_name": "Nama bank (BCA/Mandiri/BRI/DANA/dsb)",\n'
        '  "subtotal": 0,\n'
        '  "tax_amount": 0,\n'
        '  "discount_amount": 0,\n'
        '  "total_amount": 0,\n'
        '  "status": "Lunas",\n'
        '  "notes": ""\n'
        "}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Ekstrak transaksi dari gambar/dokumen ini ke JSON:"},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "temperature": 0.1
    }

    endpoint = base_url.rstrip("/") + "/chat/completions"
    res = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise Exception(f"Provider Error ({res.status_code}): {res.text}")

    data = res.json()
    text = data["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1).strip()
    parsed = json.loads(text)
    parsed["_provider_used"] = model_name
    return parsed

def extract_with_claude(file_bytes: bytes, mime_type: str, api_key: str, model_name: str = "claude-3-5-sonnet-20241022") -> dict:
    b64_content = base64.b64encode(file_bytes).decode("utf-8")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    content_item = {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type if mime_type.startswith("image/") else "image/jpeg",
            "data": b64_content
        }
    }

    payload = {
        "model": model_name,
        "max_tokens": 1024,
        "system": "Ekstrak nota/bukti transfer ke JSON murni (format: invoice_number, date, customer_name, customer_initials, description, category, bank_name, total_amount, status).",
        "messages": [
            {
                "role": "user",
                "content": [
                    content_item,
                    {"type": "text", "text": "Ekstrak transaksi ke JSON murni."}
                ]
            }
        ]
    }

    res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise Exception(f"Claude Error ({res.status_code}): {res.text}")
    text = res.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1).strip()
    parsed = json.loads(text)
    parsed["_provider_used"] = model_name
    return parsed

def universal_extract(file_bytes: bytes, mime_type: str, provider: str, api_key: str, model: str = None) -> dict:
    """Router ekstraksi multi-provider BYOK"""
    provider = (provider or "gemini").lower()

    if provider == "gemini":
        return extract_with_gemini(file_bytes, mime_type, api_key, model or "gemini-2.5-flash")

    elif provider == "openai":
        return extract_with_openai_compatible(
            file_bytes, mime_type, api_key,
            base_url="https://api.openai.com/v1",
            model_name=model or "gpt-4o-mini"
        )

    elif provider == "claude":
        return extract_with_claude(file_bytes, mime_type, api_key, model or "claude-3-5-sonnet-20241022")

    elif provider == "nvidia":
        # NVIDIA NIM API (OpenAI Compatible)
        # Model Vision Multimodal di NVIDIA NIM:
        # meta/llama-3.2-11b-vision-instruct atau meta/llama-3.2-90b-vision-instruct
        return extract_with_openai_compatible(
            file_bytes, mime_type, api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            model_name=model or "meta/llama-3.2-11b-vision-instruct"
        )

    elif provider == "openrouter":
        return extract_with_openai_compatible(
            file_bytes, mime_type, api_key,
            base_url="https://openrouter.ai/api/v1",
            model_name=model or "google/gemini-2.5-flash"
        )

    elif provider == "groq":
        return extract_with_openai_compatible(
            file_bytes, mime_type, api_key,
            base_url="https://api.groq.com/openai/v1",
            model_name=model or "llama-3.2-11b-vision-preview"
        )

    else:
        # Default fallback ke Gemini
        return extract_with_gemini(file_bytes, mime_type, api_key, model or "gemini-2.5-flash")


def test_ai_connection(provider: str, api_key: str) -> dict:
    """Menguji kevalidan API key untuk provider yang dipilih"""
    provider = provider.lower()
    
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "Hello, respond with OK"}]}]
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi Google Gemini berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"Gemini Error ({resp.status_code}): {resp.text[:200]}"}

    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi OpenAI berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"OpenAI Error ({resp.status_code}): {resp.text[:200]}"}

    elif provider == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 5,
            "messages": [{"role": "user", "content": "ping"}]
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi Anthropic Claude berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"Claude Error ({resp.status_code}): {resp.text[:200]}"}

    elif provider == "nvidia":
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "nvidia/nemotron-3-ultra-550b-a55b",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi NVIDIA NIM berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"NVIDIA Error ({resp.status_code}): {resp.text[:200]}"}

    elif provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi Groq berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"Groq Error ({resp.status_code}): {resp.text[:200]}"}

    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "message": "Koneksi OpenRouter berhasil! API Key valid."}
        else:
            return {"success": False, "message": f"OpenRouter Error ({resp.status_code}): {resp.text[:200]}"}

    return {"success": False, "message": f"Provider '{provider}' tidak dikenal."}
