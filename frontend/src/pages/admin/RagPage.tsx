import { useEffect, useState, useRef } from 'react';
import { Upload, Database, FileText, Trash2 } from 'lucide-react';
import { getCollections, createCollection, deleteCollection, ingestFiles, getDocuments } from '../../api/admin';
import type { DocumentInfo } from '../../types';

export function RagPage() {
  const [collections, setCollections] = useState<{ name: string; doc_count: number }[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [newCollName, setNewCollName] = useState('');
  const [selectedColl, setSelectedColl] = useState('');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    try {
      const colls = await getCollections();
      setCollections(colls);
      const docs = await getDocuments(selectedColl || undefined);
      setDocuments(docs);
    } catch {}
  };

  useEffect(() => { refresh(); }, [selectedColl]);

  const handleCreateCollection = async () => {
    if (!newCollName) return;
    await createCollection(newCollName);
    setNewCollName('');
    refresh();
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files?.length || !selectedColl) return;
    setUploading(true);
    setMessage('');
    try {
      const result = await ingestFiles(selectedColl, Array.from(files));
      setMessage(`${result.message}`);
      setTimeout(refresh, 2000);
    } catch {
      setMessage('Upload failed');
    }
    setUploading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">RAG / Documents</h1>

      {message && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-primary-50 dark:bg-primary-950 text-primary-600 text-sm">
          {message}
        </div>
      )}

      {/* Collections */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Collections</h2>
        <div className="flex gap-3 mb-4">
          <input
            value={newCollName}
            onChange={(e) => setNewCollName(e.target.value)}
            placeholder="New collection name"
            className="input-field flex-1"
          />
          <button onClick={handleCreateCollection} disabled={!newCollName} className="btn-primary">
            Create
          </button>
        </div>
        <div className="space-y-2">
          {collections.map((coll) => (
            <div
              key={coll.name}
              className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors ${selectedColl === coll.name ? 'bg-white/60 dark:bg-white/10 border border-white/50 dark:border-white/15' : 'hover:bg-white/40 dark:hover:bg-white/5'}`}
              onClick={() => setSelectedColl(coll.name)}
            >
              <div className="flex items-center gap-2">
                <Database size={16} className="text-surface-400" />
                <span className="font-medium">{coll.name}</span>
                <span className="text-sm text-surface-500">({coll.doc_count} docs)</span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); deleteCollection(coll.name).then(refresh); }}
                className="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-colors"
              >
                <Trash2 size={14} className="text-red-500" />
              </button>
            </div>
          ))}
          {collections.length === 0 && <p className="text-surface-500 text-sm">No collections yet.</p>}
        </div>
      </div>

      {/* File Upload */}
      {selectedColl && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Upload Documents to "{selectedColl}"</h2>
          <div
            className="border-2 border-dashed border-white/50 dark:border-white/15 rounded-2xl p-8 text-center cursor-pointer hover:border-primary-500 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={32} className="mx-auto mb-3 text-surface-400" />
            <p className="text-surface-600 dark:text-surface-400">
              {uploading ? 'Uploading...' : 'Click to upload files (PDF, DOCX, TXT, CSV, HTML, images, etc.)'}
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
          </div>
        </div>
      )}

      {/* Documents */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">Documents</h2>
        <div className="space-y-2">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-3 bg-white/40 dark:bg-white/5 border border-white/40 dark:border-white/10 rounded-xl">
              <div className="flex items-center gap-3">
                <FileText size={18} className="text-surface-400" />
                <div>
                  <p className="font-medium text-sm">{doc.filename}</p>
                  <p className="text-xs text-surface-500">
                    {doc.chunkCount} chunks | {doc.status}
                  </p>
                </div>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${doc.status === 'complete' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : doc.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'}`}>
                {doc.status}
              </span>
            </div>
          ))}
          {documents.length === 0 && <p className="text-surface-500 text-sm">No documents ingested yet.</p>}
        </div>
      </div>
    </div>
  );
}
