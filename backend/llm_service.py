import json
import requests
import time
import re
from search_service import search_academic_papers

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_ollama(prompt: str, model: str, system_prompt: str = "") -> str:
    """Helper function to call the local Ollama LLM."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1
        }
    }
    try:
        # Reasoning models take a massive amount of time; setting timeout to None disables the limit
        response = requests.post(OLLAMA_URL, json=payload, timeout=None)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        raise RuntimeError(f"Ollama connection error (make sure ollama is running on localhost:11434 with {model} pulled): {e}")

def extract_json_block(text: str, expect_list: bool = False) -> str:
    """Extracts JSON from response, skipping thinking tokens and markdown wrappers."""
    # Strip known thinking markers
    if "...done thinking." in text:
        text = text.split("...done thinking.")[-1]
    elif "</think>" in text:
        text = text.split("</think>")[-1]
        
    text = text.strip()
    
    # Check for markdown json extraction
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Standard bracket extraction as fallback
    try:
        start_char = '[' if expect_list else '{'
        end_char = ']' if expect_list else '}'
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
    except Exception:
        pass
    return text

def process_text_and_cite(text: str, model: str, strictness: int = 2) -> dict:
    """The main RAG pipeline utilizing the Identify -> Search -> Verify -> Inject flow."""
    # 1. Split text into logical sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {"annotated_text": text, "bibtex": ""}

    # Format the sentences for the LLM
    numbered_sentences = ""
    for i, s in enumerate(sentences):
        numbered_sentences += f"{i}: {s}\n"

    # 2. PHASE 1: IDENTIFY Concepts using LLM
    system_prompt = """You are an expert academic researcher. First, identify the central overarching academic field or topic of the whole text. Then, given the numbered list of sentences, determine which sentences would benefit from an academic citation. 
For those that do, provide a highly standardized search query (maximum 4 to 6 words). You MUST manually include the central overarching topic within EVERY search query you generate so that the search results remain strictly locked onto the correct context.

Example Output:
{
  "0": "standard GARCH limitations economic models",
  "6": "correlation breakdown financial time series crises"
}
"""
    prompt = f"Numbered Sentences:\n{numbered_sentences}\n\nOutput JSON ONLY:"
    
    response = call_ollama(prompt, model, system_prompt)
    
    try:
        cleanup = extract_json_block(response, expect_list=False)
        mapping = json.loads(cleanup)
        if not isinstance(mapping, dict):
            mapping = {}
    except Exception:
        mapping = {}

    # 3. PHASE 2: BROAD SEARCH
    candidates = {} # map idx -> list of papers
    all_retrieved_papers = {} 
    
    for idx_str, query in dict(list(mapping.items())[:8]).items():
        try:
            idx = int(idx_str)
            if 0 <= idx < len(sentences) and query and isinstance(query, str):
                papers = search_academic_papers(query, limit=3) # get up to 3
                if papers:
                    candidates[idx] = papers
                    for p in papers:
                        all_retrieved_papers[p['cite_key']] = p
                time.sleep(1.5) # rate limit prevention
        except ValueError:
            continue
            
    if not candidates:
        return {"annotated_text": " ".join(sentences), "bibtex": "No citations found."}

    # 4. PHASE 3: VERIFY Relevance using LLM
    validation_prompt_text = "Review the following sentences and their candidate academic papers.\n\n"
    for idx, papers_list in candidates.items():
        validation_prompt_text += f"*** SENTENCE {idx}: \"{sentences[idx]}\"\n"
        validation_prompt_text += "CANDIDATES:\n"
        for p in papers_list:
             validation_prompt_text += f"- [{p['cite_key']}]: {p['title']}\n  Abstract Snippet: {str(p.get('abstract', 'No abstract available'))[:300]}\n"
        validation_prompt_text += "\n"

    if strictness == 1:
        strictness_instructions = "You must act as an extremely strict and brutal academic reviewer. ONLY select a paper if it perfectly, explicitly, and directly proves the central mathematical or factual claim of the sentence. Do not accept any paper that only tangentially relates to the topic. It is better to have no citation than a weak one. Map to explicitly `null` aggressively if none are a perfect fit."
    elif strictness == 3:
        strictness_instructions = "You are desperate for citations. The user needs ANY citation on the board. Be extremely lenient. Select any paper even if it is only broadly related or stretches relevancy to the overarching field. Only map to explicitly `null` if all candidates are fundamentally broken or completely unrelated to the topic."
    else:
        # Balanced
        strictness_instructions = "Be lenient: It is better to provide a broadly related topical citation than no citation at all. Select a paper as long as it generally deals with the core concepts mentioned in the sentence. Map to explicitly `null` ONLY if absolutely all candidates are fundamentally irrelevant."

    validation_sys_prompt = f"""You are an expert academic peer-reviewer. For each sentence provided, evaluate the candidate papers and select the single BEST paper to cite for that sentence's topic.
{strictness_instructions} Output ONLY a JSON dictionary mapping the sentence index (as a string) to the winning paper's exact `cite_key`. DO NOT output anything else.

Example Output:
{{
  "0": "smith2023",
  "1": null,
  "2": "jones2020"
}}"""
    validation_prompt = f"{validation_prompt_text}\nOutput JSON dict ONLY:"

    validation_response = call_ollama(validation_prompt, model, validation_sys_prompt)
    try:
        cleanup_val = extract_json_block(validation_response, expect_list=False)
        approved_mapping = json.loads(cleanup_val)
        if not isinstance(approved_mapping, dict):
            approved_mapping = {}
    except Exception as e:
        print(f"Failed to parse validation JSON: {e}\nResponse: {validation_response}")
        approved_mapping = {}

    cited_papers = {}
    
    # 5. PHASE 4: NATIVE INJECT
    for idx_str, cite_key in approved_mapping.items():
        try:
            idx = int(idx_str)
            if cite_key is None:
                continue
            if 0 <= idx < len(sentences) and cite_key and isinstance(cite_key, str):
                if cite_key in all_retrieved_papers:
                    if sentences[idx][-1] in ".!?":
                        # Insert citation before the punctuation mark
                        sentences[idx] = sentences[idx][:-1] + f" \\cite{{{cite_key}}}" + sentences[idx][-1]
                    else:
                        sentences[idx] = sentences[idx] + f" \\cite{{{cite_key}}}"
                        
                    cited_papers[cite_key] = all_retrieved_papers[cite_key]
        except ValueError:
            continue
            
    annotated_text = " ".join(sentences)

    bibtex_str = ""
    for p in cited_papers.values():
        authors = " and ".join(p['authors']) if p['authors'] else "Unknown"
        journal = p.get('venue', 'Academic Reference')
        bibtex_str += f"""@article{{{p['cite_key']},
  title={{{p['title']}}},
  author={{{authors}}},
  journal={{{journal}}},
  year={{{p['year']}}},
  url={{{p['url']}}}
}}

"""
    return {
        "annotated_text": annotated_text,
        "bibtex": bibtex_str.strip() or "No citations found / all citations judged irrelevant by reviewer AI."
    }
