export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export interface TaxonomyTopic {
  id?: string;
  name: string;
  topic_type?: string;
  description?: string;
  is_mandatory?: boolean;
}

export interface TaxonomyCategory {
  id?: string;
  name: string;
  description?: string;
  topics?: TaxonomyTopic[];
}

export interface TaxonomyDomain {
  id?: string;
  name: string;
  description?: string;
  categories?: TaxonomyCategory[];
}

export interface TaxonomyFramework {
  id?: string;
  name: string;
  description?: string;
  created_by?: string;
  version?: string;
  domains?: TaxonomyDomain[];
}

export interface PersonaOption {
  id: string;
  name: string;
  action?: string;
  needs?: string[];
}

export interface TaxonomyResponse {
  frameworks: TaxonomyFramework[];
  domains?: Array<Record<string, unknown>>;
  categories?: Array<Record<string, unknown>>;
  topics?: TaxonomyTopic[];
  personas?: PersonaOption[];
}

export interface DocumentRecord {
  id: string;
  title: string;
  doc_type: string;
  jurisdiction: string;
  status: string;
  created_at: string;
  framework_name?: string;
  domain_name?: string;
  category_name?: string;
  mapped_topics?: string[];
  regulatory_body?: string;
  applicable_entity?: string;
  version_year?: string;
  file_size_bytes?: number;
  effective_date?: string;
  chunk_count?: number;
}

export interface ChatSessionSummary {
  session_id: string;
  user_id: string;
  persona?: string;
  title?: string;
  started_at?: string;
  updated_at: string;
  last_message_preview?: string;
}

export interface ChatMessageRecord {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  citations?: unknown[];
  timestamp: string;
}

export interface ChatSessionDetail {
  session: ChatSessionSummary;
  messages: ChatMessageRecord[];
}

export interface UploadDocumentPayload {
  file: File;
  framework_name: string;
  framework_description?: string;
  framework_created_by?: string;
  framework_version?: string;
  domain_name: string;
  domain_description?: string;
  category_name: string;
  category_description?: string;
  document_name: string;
  jurisdiction: string;
  document_type: string;
  regulatory_body?: string;
  applicable_entity?: string;
  version_year?: string;
  description?: string;
  effective_date?: string;
  section_reference?: string;
  risk_level?: string;
  compliance_type?: string;
  entity_type?: string;
  keywords?: string[];
  mapped_topics?: string[];
  uploaded_by?: string;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || 'Request failed');
  }

  return response.json() as Promise<T>;
}

export async function fetchTaxonomy(): Promise<TaxonomyResponse> {
  const response = await fetch(`${API_BASE_URL}/regulations/taxonomy`);
  return parseJsonResponse<TaxonomyResponse>(response);
}

export async function fetchDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/regulations/documents`);
  const payload = await parseJsonResponse<{ documents: DocumentRecord[] }>(response);
  return payload.documents;
}

export async function uploadDocument(payload: UploadDocumentPayload): Promise<void> {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('framework_name', payload.framework_name);
  formData.append('framework_description', payload.framework_description ?? '');
  formData.append('framework_created_by', payload.framework_created_by ?? 'system');
  formData.append('framework_version', payload.framework_version ?? '');
  formData.append('domain_name', payload.domain_name);
  formData.append('domain_description', payload.domain_description ?? '');
  formData.append('category_name', payload.category_name);
  formData.append('category_description', payload.category_description ?? '');
  formData.append('document_name', payload.document_name);
  formData.append('jurisdiction', payload.jurisdiction);
  formData.append('document_type', payload.document_type);
  formData.append('regulatory_body', payload.regulatory_body ?? '');
  formData.append('applicable_entity', payload.applicable_entity ?? '');
  formData.append('version_year', payload.version_year ?? '');
  formData.append('description', payload.description ?? '');
  formData.append('effective_date', payload.effective_date ?? '');
  formData.append('section_reference', payload.section_reference ?? '');
  formData.append('risk_level', payload.risk_level ?? '');
  formData.append('compliance_type', payload.compliance_type ?? '');
  formData.append('entity_type', payload.entity_type ?? '');
  formData.append('keywords', (payload.keywords ?? []).join(','));
  formData.append('mapped_topics', JSON.stringify(payload.mapped_topics ?? []));
  formData.append('uploaded_by', payload.uploaded_by ?? 'default_user');

  const response = await fetch(`${API_BASE_URL}/regulations/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  await parseJsonResponse(response);
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/regulations/documents/${documentId}`, {
    method: 'DELETE',
  });

  await parseJsonResponse(response);
}

export async function fetchChatSessions(userId = 'default_user'): Promise<ChatSessionSummary[]> {
  const response = await fetch(`${API_BASE_URL}/chats/sessions?user_id=${encodeURIComponent(userId)}`);
  const payload = await parseJsonResponse<{ sessions: ChatSessionSummary[] }>(response);
  return payload.sessions;
}

export async function fetchChatSession(sessionId: string): Promise<ChatSessionDetail> {
  const response = await fetch(`${API_BASE_URL}/chats/sessions/${encodeURIComponent(sessionId)}`);
  return parseJsonResponse<ChatSessionDetail>(response);
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chats/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
  await parseJsonResponse(response);
}

export interface BookmarkRecord {
  bookmark_id: string;
  user_id: string;
  session_id: string;
  transaction_payload?: any;
  assessment: {
    application: string;
    message_id: string;
    content: string;
    title: string;
  };
  created_at: string;
}

export async function fetchBookmarks(userId = 'default_user'): Promise<BookmarkRecord[]> {
  const response = await fetch(`${API_BASE_URL}/chats/bookmarks?user_id=${encodeURIComponent(userId)}`);
  const payload = await parseJsonResponse<{ bookmarks: BookmarkRecord[] }>(response);
  return payload.bookmarks;
}

export async function createBookmark(
  sessionId: string,
  application: string,
  messageId: string,
  content: string,
  userId = 'default_user'
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chats/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      application,
      message_id: messageId,
      content,
    }),
  });
  await parseJsonResponse(response);
}

export async function deleteBookmark(bookmarkId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chats/bookmarks/${encodeURIComponent(bookmarkId)}`, {
    method: 'DELETE',
  });
  await parseJsonResponse(response);
}

export async function submitFeedback(
  sessionId: string,
  responseId: string,
  rating: 'LIKE' | 'DISLIKE',
  comments?: string,
  userId = 'default_user'
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chats/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      response_id: responseId,
      rating,
      comments: comments || null,
    }),
  });
  await parseJsonResponse(response);
}

export async function fetchApplications(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/chats/applications`);
  const payload = await parseJsonResponse<{ applications: string[] }>(response);
  return payload.applications;
}