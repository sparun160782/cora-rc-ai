import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, FileText, Trash2, Database, X, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  deleteDocument,
  fetchDocuments,
  fetchTaxonomy,
  uploadDocument,
  type DocumentRecord,
  type TaxonomyCategory,
  type TaxonomyDomain,
  type TaxonomyFramework,
  type TaxonomyTopic,
} from '../services/api';

interface UploadFormState {
  framework_name: string;
  framework_description: string;
  framework_created_by: string;
  framework_version: string;
  domain_name: string;
  domain_description: string;
  category_name: string;
  category_description: string;
  document_name: string;
  jurisdiction: string;
  document_type: string;
  regulatory_body: string;
  applicable_entity: string;
  version_year: string;
  description: string;
  effective_date: string;
  section_reference: string;
  risk_level: string;
  compliance_type: string;
  entity_type: string;
  keywords: string;
  mapped_topics: string[];
}

const DEFAULT_FORM: UploadFormState = {
  framework_name: 'RBI Framework',
  framework_description: '',
  framework_created_by: 'User',
  framework_version: 'v1',
  domain_name: 'Compliance',
  domain_description: '',
  category_name: 'AML_KYC',
  category_description: '',
  document_name: '',
  jurisdiction: 'RBI',
  document_type: 'Master Direction',
  regulatory_body: 'RBI',
  applicable_entity: 'Banks / NBFC',
  version_year: '',
  description: '',
  effective_date: '',
  section_reference: '',
  risk_level: 'Medium',
  compliance_type: 'AML',
  entity_type: 'Bank',
  keywords: '',
  mapped_topics: [],
};

export const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [frameworks, setFrameworks] = useState<TaxonomyFramework[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [form, setForm] = useState<UploadFormState>(DEFAULT_FORM);
  const [error, setError] = useState<string | null>(null);

  const selectedFramework = useMemo(
    () => frameworks.find((framework) => framework.name === form.framework_name),
    [frameworks, form.framework_name],
  );
  const domains = selectedFramework?.domains ?? [];
  const selectedDomain = useMemo(
    () => domains.find((domain) => domain.name === form.domain_name),
    [domains, form.domain_name],
  );
  const categories = selectedDomain?.categories ?? [];
  const selectedCategory = useMemo(
    () => categories.find((category) => category.name === form.category_name),
    [categories, form.category_name],
  );
  const topics: TaxonomyTopic[] = selectedCategory?.topics ?? [];

  const loadPageData = async () => {
    setLoading(true);
    try {
      const [taxonomy, documentRows] = await Promise.all([fetchTaxonomy(), fetchDocuments()]);
      setFrameworks(taxonomy.frameworks);
      setDocuments(documentRows);

      const defaultFramework = taxonomy.frameworks[0];
      const defaultDomain = defaultFramework?.domains?.[0];
      const defaultCategory = defaultDomain?.categories?.[0];
      setForm((current) => ({
        ...current,
        framework_name: current.framework_name || defaultFramework?.name || '',
        framework_description: current.framework_description || defaultFramework?.description || '',
        framework_version: current.framework_version || defaultFramework?.version || 'v1',
        domain_name: current.domain_name || defaultDomain?.name || '',
        domain_description: current.domain_description || defaultDomain?.description || '',
        category_name: current.category_name || defaultCategory?.name || '',
        category_description: current.category_description || defaultCategory?.description || '',
      }));
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPageData();
  }, []);

  useEffect(() => {
    if (!selectedFramework) {
      return;
    }

    const firstDomain: TaxonomyDomain | undefined = selectedFramework.domains?.[0];
    setForm((current) => ({
      ...current,
      framework_description: selectedFramework.description ?? current.framework_description,
      framework_version: selectedFramework.version ?? current.framework_version,
      domain_name: selectedFramework.domains?.some((domain) => domain.name === current.domain_name)
        ? current.domain_name
        : firstDomain?.name ?? '',
    }));
  }, [selectedFramework]);

  useEffect(() => {
    if (!selectedDomain) {
      return;
    }

    const firstCategory: TaxonomyCategory | undefined = selectedDomain.categories?.[0];
    setForm((current) => ({
      ...current,
      domain_description: selectedDomain.description ?? current.domain_description,
      category_name: selectedDomain.categories?.some((category) => category.name === current.category_name)
        ? current.category_name
        : firstCategory?.name ?? '',
      mapped_topics: current.mapped_topics.filter((topic) =>
        (firstCategory?.topics ?? selectedCategory?.topics ?? []).some((item) => item.name === topic),
      ),
    }));
  }, [selectedDomain]);

  useEffect(() => {
    if (!selectedCategory) {
      return;
    }

    setForm((current) => ({
      ...current,
      category_description: selectedCategory.description ?? current.category_description,
      mapped_topics: current.mapped_topics.filter((topic) =>
        (selectedCategory.topics ?? []).some((item) => item.name === topic),
      ),
    }));
  }, [selectedCategory]);

  const updateForm = (key: keyof UploadFormState, value: string | string[]) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const toggleTopic = (topicName: string) => {
    setForm((current) => ({
      ...current,
      mapped_topics: current.mapped_topics.includes(topicName)
        ? current.mapped_topics.filter((topic) => topic !== topicName)
        : [...current.mapped_topics, topicName],
    }));
  };

  const resetForm = () => {
    setForm(DEFAULT_FORM);
    setSelectedFile(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!selectedFile) {
      setError('Select a document file before saving.');
      return;
    }

    if (!form.framework_name || !form.domain_name || !form.category_name || !form.document_name) {
      setError('Framework, domain, category, and document name are required.');
      return;
    }

    setIsUploading(true);
    try {
      await uploadDocument({
        ...form,
        file: selectedFile,
        keywords: form.keywords.split(',').map((keyword) => keyword.trim()).filter(Boolean),
      });
      await loadPageData();
      resetForm();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      await loadPageData();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Delete failed');
    }
  };

  return (
    <div className="flex-1 bg-slate-50 dark:bg-slate-900 min-h-screen overflow-y-auto">
      <div className="max-w-6xl mx-auto p-8">

        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Document Center</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Upload, classify, and automatically ingest regulatory source documents</p>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-blue-100 dark:border-slate-700 rounded-xl p-8 mb-8 shadow-sm relative">
          <button title="Reset form" aria-label="Reset form" onClick={resetForm} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors">
            <X size={20} />
          </button>

          <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
            <div className="space-y-6">
              <section className="grid gap-4 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">A. Framework</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Define the top-level regulatory framework.</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Framework Name
                    <select
                      value={form.framework_name}
                      onChange={(event) => updateForm('framework_name', event.target.value)}
                      className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5"
                    >
                      {frameworks.map((framework) => (
                        <option key={framework.name} value={framework.name}>{framework.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Version
                    <input
                      value={form.framework_version}
                      onChange={(event) => updateForm('framework_version', event.target.value)}
                      className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5"
                    />
                  </label>
                </div>
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  Description
                  <textarea
                    value={form.framework_description}
                    onChange={(event) => updateForm('framework_description', event.target.value)}
                    rows={2}
                    className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5"
                  />
                </label>
              </section>

              <section className="grid gap-4 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">B. Domain and Category</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Group documents under primary domains and sub-domains.</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Domain
                    <select
                      value={form.domain_name}
                      onChange={(event) => updateForm('domain_name', event.target.value)}
                      className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5"
                    >
                      {domains.map((domain) => (
                        <option key={domain.name} value={domain.name}>{domain.name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Category
                    <select
                      value={form.category_name}
                      onChange={(event) => updateForm('category_name', event.target.value)}
                      className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5"
                    >
                      {categories.map((category) => (
                        <option key={category.name} value={category.name}>{category.name}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </section>

              <section className="grid gap-4 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">C. Document</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Uploading now triggers chunking and embedding automatically.</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Document Name
                    <input value={form.document_name} onChange={(event) => updateForm('document_name', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Document Type
                    <input value={form.document_type} onChange={(event) => updateForm('document_type', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Regulatory Body
                    <input value={form.regulatory_body} onChange={(event) => updateForm('regulatory_body', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Applicable Entity
                    <input value={form.applicable_entity} onChange={(event) => updateForm('applicable_entity', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Version / Year
                    <input value={form.version_year} onChange={(event) => updateForm('version_year', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Jurisdiction
                    <input value={form.jurisdiction} onChange={(event) => updateForm('jurisdiction', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                </div>
                <label className="text-sm text-slate-600 dark:text-slate-300">
                  Upload File
                  <label className="mt-2 flex cursor-pointer items-center justify-center gap-3 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 px-4 py-8 text-sm text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
                    <UploadCloud size={20} />
                    <span>{selectedFile ? selectedFile.name : 'Choose PDF, DOCX, TXT, or Markdown file'}</span>
                    <input type="file" className="hidden" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
                  </label>
                </label>
              </section>
            </div>

            <div className="space-y-6">
              <section className="rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">D. Topics Mapping</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Attach reusable topics for retrieval, scoring, and auditability.</p>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {topics.length === 0 ? (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No preloaded topics for the selected category yet.</p>
                  ) : (
                    topics.map((topic) => (
                      <label key={topic.name} className="flex items-start gap-3 rounded-lg border border-slate-200 dark:border-slate-700 p-3 text-sm text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={form.mapped_topics.includes(topic.name)}
                          onChange={() => toggleTopic(topic.name)}
                          className="mt-1"
                        />
                        <div>
                          <div className="font-semibold">{topic.name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">{topic.description || topic.topic_type || 'Topic'}</div>
                        </div>
                      </label>
                    ))
                  )}
                </div>
                <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-400">
                      <tr>
                        <th className="px-4 py-3">Document</th>
                        <th className="px-4 py-3">Topics</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-slate-200 dark:border-slate-700">
                        <td className="px-4 py-3 text-slate-900 dark:text-white">{form.document_name || 'Current upload'}</td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{form.mapped_topics.join(', ') || 'No topics selected'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">E. Metadata</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Supports RAG retrieval, risk filtering, and search.</p>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Keywords
                    <input value={form.keywords} onChange={(event) => updateForm('keywords', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" placeholder="AML, KYC, Credit" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Risk Level
                    <select value={form.risk_level} onChange={(event) => updateForm('risk_level', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5">
                      <option>Low</option>
                      <option>Medium</option>
                      <option>High</option>
                    </select>
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Compliance Type
                    <input value={form.compliance_type} onChange={(event) => updateForm('compliance_type', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Entity Type
                    <input value={form.entity_type} onChange={(event) => updateForm('entity_type', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Effective Date
                    <input type="date" value={form.effective_date} onChange={(event) => updateForm('effective_date', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                  <label className="text-sm text-slate-600 dark:text-slate-300">
                    Section Reference
                    <input value={form.section_reference} onChange={(event) => updateForm('section_reference', event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                  </label>
                </div>
                <label className="mt-4 block text-sm text-slate-600 dark:text-slate-300">
                  Description
                  <textarea value={form.description} onChange={(event) => updateForm('description', event.target.value)} rows={4} className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-2.5" />
                </label>
              </section>
            </div>
          </div>

          {error ? (
            <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
              {error}
            </div>
          ) : null}

          <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-slate-100 dark:border-slate-700">
            <button onClick={resetForm} className="px-6 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-semibold rounded-lg hover:bg-slate-50 transition-colors">
              Cancel
            </button>
            <button onClick={() => void handleSave()} disabled={isUploading || loading} className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed">
              {isUploading ? 'Uploading and processing...' : 'Save document'}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4 mt-12">
          <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold text-lg">
            <Database size={20} className="text-blue-500" />
            Ingested Documents
          </div>
          <span className="text-sm text-slate-500">Showing {documents.length} files in knowledge base</span>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs font-bold text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-6 py-4">FILE NAME</th>
                  <th className="px-6 py-4">FRAMEWORK</th>
                  <th className="px-6 py-4">CLASSIFICATION</th>
                  <th className="px-6 py-4">STATUS</th>
                  <th className="px-6 py-4">TOPICS</th>
                  <th className="px-6 py-4">UPLOADED</th>
                  <th className="px-6 py-4 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">Loading documents...</td>
                  </tr>
                ) : documents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">No ingested documents yet.</td>
                  </tr>
                ) : documents.map((doc) => (
                  <tr key={doc.id} className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-200 flex items-center gap-3">
                      <div className="p-2 bg-blue-50 dark:bg-blue-900/30 text-blue-500 rounded-md">
                        <FileText size={18} />
                      </div>
                      {doc.title}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-800 dark:text-slate-200">{doc.framework_name || doc.jurisdiction}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">{doc.regulatory_body || doc.doc_type}</div>
                    </td>
                    <td className="px-6 py-4 text-xs">
                      <div className="text-slate-400">Domain: <span className="text-slate-600 dark:text-slate-300 font-medium">{doc.domain_name || 'N/A'}</span></div>
                      <div className="text-slate-400">Category: <span className="text-slate-600 dark:text-slate-300 font-medium">{doc.category_name || 'N/A'}</span></div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 text-xs font-medium">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-slate-500">
                      {doc.mapped_topics?.length ? doc.mapped_topics.join(', ') : 'No topics'}
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button title="Delete document" aria-label="Delete document" onClick={() => void handleDelete(doc.id)} className="text-slate-400 hover:text-red-600 transition-colors">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
};
