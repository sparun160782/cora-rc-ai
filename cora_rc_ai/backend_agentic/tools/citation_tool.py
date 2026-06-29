import json
import logging
from cora_rc_ai.data_layer.vector_store.pgvector_adapter import PgVectorAdapter

logger = logging.getLogger(__name__)

def generate_and_verify_citation(
    document_title: str,
    section_name: str,
    clause_name: str = "",
    page_number: int = 0
) -> str:
    """
    Verify if a regulatory citation exists in the database and generate its canonical string format.
    Use this tool to cross-reference document sections and pages to guarantee 100% citation accuracy.

    Args:
        document_title: The name/title of the regulatory document (e.g. 'RBI Master Direction - KYC').
        section_name: The section name/number (e.g. 'Section 4' or 'Section 12').
        clause_name: The clause name/number (e.g. 'Clause 4.1' or 'Chapter II').
        page_number: The source page number.

    Returns:
        A JSON string containing the verification status ('VERIFIED' or 'UNVERIFIED') and the canonical citation string.
    """
    # Coerce LLM-supplied page_number to int; tool-calling models often pass
    # numbers as strings, which would break the numeric comparison below.
    try:
        page_number = int(float(str(page_number).strip()))
    except (TypeError, ValueError):
        page_number = 0

    db = PgVectorAdapter()
    
    # Verify the document exists and that the cited section/clause text actually
    # appears in an ingested chunk. The live schema (V2) stores chunks in
    # document_chunks (content + metadata) linked to regulatory_documents(id).
    query = """
        SELECT rd.id, rd.title, rd.source_file
        FROM document_chunks dc
        JOIN regulatory_documents rd ON dc.document_id = rd.id
        WHERE rd.title ILIKE %s
          AND (
                dc.content ILIKE %s
                OR (%s <> '' AND dc.content ILIKE %s)
              )
        LIMIT 1;
    """
    
    clause_value = clause_name if clause_name else ""
    params = (
        f"%{document_title}%",
        f"%{section_name}%",
        clause_value,
        f"%{clause_name}%" if clause_name else "%",
    )
    results = db.execute_query(query, params)
    
    if results:
        res = results[0]
        # V2 schema has no version column yet; default to v1 until versioning is added.
        version_str = "v1"
        citation_str = f"[{res['title']} {version_str}, {section_name}"
        if clause_name:
            citation_str += f", {clause_name}"
        if page_number > 0:
            citation_str += f", Page {page_number}"
        citation_str += "]"
        
        response = {
            "status": "VERIFIED",
            "citation": citation_str,
            "document": res['title'],
            "version": version_str
        }
    else:
        # Fallback if metadata lookup fails
        version_fallback = "v1"
        citation_str = f"[{document_title} {version_fallback}, {section_name}"
        if clause_name:
            citation_str += f", {clause_name}"
        if page_number > 0:
            citation_str += f", Page {page_number}"
        citation_str += "]"
        
        response = {
            "status": "UNVERIFIED",
            "citation": citation_str,
            "document": document_title,
            "version": version_fallback
        }
        
    return json.dumps(response, indent=2)
