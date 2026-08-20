'use client'

import { useMemo, useRef, useState } from 'react'
import { FileText, GitBranch, Hash, Upload } from 'lucide-react'
import {
  KNOWLEDGE_FOLDERS,
  uploadDocument,
  type KnowledgeFolder,
} from '@/lib/api'
import { ModalShell } from '@/components/overlays/ModalShell'

type UploadModalProps = {
  onClose: () => void
  onUploaded: () => void
}

const ACCEPT =
  '.pdf,.txt,.md,.markdown,.csv,.json,.html,.htm,.docx,.doc,.rtf,.log,.png,.jpg,.jpeg,.webp,.gif'

function defaultTitleFromFile(file: File) {
  return file.name.replace(/\.[^.]+$/i, '').trim() || 'Untitled'
}

export function UploadModal({ onClose, onUploaded }: UploadModalProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [folder, setFolder] = useState<KnowledgeFolder>('personal')
  const [displayName, setDisplayName] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const previewName = useMemo(() => {
    if (displayName.trim()) return displayName.trim()
    if (selectedFile) return defaultTitleFromFile(selectedFile)
    return ''
  }, [displayName, selectedFile])

  const handleFilePicked = (file: File | undefined) => {
    if (!file) return
    setSelectedFile(file)
    if (!displayName.trim()) {
      setDisplayName(defaultTitleFromFile(file))
    }
    setUploadMsg(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadMsg('Choose a document first.')
      return
    }

    setUploading(true)
    setUploadMsg(null)

    try {
      const res = await uploadDocument(selectedFile, {
        folder,
        source: previewName || defaultTitleFromFile(selectedFile),
      })

      if (res.error) {
        setUploadMsg(res.error)
        return
      }

      setUploadMsg(
        `Indexed ${res.source || res.filename} in ${res.folder || folder}: ${res.pages} pages, ${res.chunks} chunks.`,
      )
      onUploaded()
    } catch (err) {
      setUploadMsg(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <ModalShell
      eyebrow="EXPAND YOUR VAULT"
      title="Add knowledge"
      onClose={onClose}
    >
      <div className="upload-meta">
        <label className="upload-field">
          <span>Folder</span>
          <select
            value={folder}
            onChange={(e) => setFolder(e.target.value as KnowledgeFolder)}
            disabled={uploading}
          >
            {KNOWLEDGE_FOLDERS.map((item) => (
              <option key={item} value={item}>
                {item.charAt(0).toUpperCase() + item.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="upload-field">
          <span>Display name</span>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Resume - Shubham Pawar"
            disabled={uploading}
          />
        </label>
      </div>

      <div className="upload-zone">
        <Upload size={22} />
        <strong>
          {uploading
            ? 'Indexing document…'
            : selectedFile
              ? selectedFile.name
              : 'Drop a document or browse'}
        </strong>
        <span>
          {previewName
            ? `Will save as “${previewName}” in ${folder}`
            : 'PDF, DOCX, TXT, MD, CSV, JSON, HTML, images, and more'}
        </span>

        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => handleFilePicked(e.target.files?.[0])}
        />

        <div className="upload-actions">
          <button
            className="filter-btn"
            type="button"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {selectedFile ? 'Change file' : 'Browse files'}
          </button>
          <button
            className="primary-btn"
            type="button"
            disabled={uploading || !selectedFile}
            onClick={() => void handleUpload()}
          >
            {uploading ? 'Uploading…' : 'Upload & index'}
          </button>
        </div>

        {uploadMsg && <span>{uploadMsg}</span>}
      </div>

      <div className="source-options">
        <button type="button" disabled>
          <GitBranch size={17} />
          <strong>GitHub</strong>
          <small>Coming soon</small>
        </button>
        <button type="button" disabled>
          <Hash size={17} />
          <strong>YouTube</strong>
          <small>Coming soon</small>
        </button>
        <button type="button" disabled>
          <FileText size={17} />
          <strong>Website</strong>
          <small>Coming soon</small>
        </button>
      </div>
    </ModalShell>
  )
}
