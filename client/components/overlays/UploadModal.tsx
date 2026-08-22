'use client'

import { useMemo, useRef, useState } from 'react'
import { FileText, GitBranch, Hash, Upload, X } from 'lucide-react'
import {
  KNOWLEDGE_FOLDERS,
  uploadDocuments,
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

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`
}

function mergeFiles(existing: File[], incoming: File[]) {
  const seen = new Set(existing.map(fileKey))
  const merged = [...existing]
  for (const file of incoming) {
    const key = fileKey(file)
    if (seen.has(key)) continue
    seen.add(key)
    merged.push(file)
  }
  return merged
}

export function UploadModal({ onClose, onUploaded }: UploadModalProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<string | null>(null)
  const [folder, setFolder] = useState<KnowledgeFolder>('personal')
  const [displayName, setDisplayName] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const singleFile = selectedFiles.length === 1 ? selectedFiles[0] : null

  const previewName = useMemo(() => {
    if (singleFile && displayName.trim()) return displayName.trim()
    if (singleFile) return defaultTitleFromFile(singleFile)
    return ''
  }, [displayName, singleFile])

  const handleFilesPicked = (fileList: FileList | null | undefined) => {
    if (!fileList?.length) return

    const incoming = Array.from(fileList)
    setSelectedFiles((current) => mergeFiles(current, incoming))

    if (incoming.length === 1 && !displayName.trim()) {
      setDisplayName(defaultTitleFromFile(incoming[0]))
    }

    setUploadMsg(null)
    setUploadProgress(null)

    if (fileRef.current) {
      fileRef.current.value = ''
    }
  }

  const removeFile = (file: File) => {
    setSelectedFiles((current) =>
      current.filter((item) => fileKey(item) !== fileKey(file)),
    )
    setUploadMsg(null)
    setUploadProgress(null)
  }

  const clearFiles = () => {
    setSelectedFiles([])
    setDisplayName('')
    setUploadMsg(null)
    setUploadProgress(null)
    if (fileRef.current) {
      fileRef.current.value = ''
    }
  }

  const handleUpload = async () => {
    if (!selectedFiles.length) {
      setUploadMsg('Choose one or more documents first.')
      return
    }

    setUploading(true)
    setUploadMsg(null)
    setUploadProgress(null)

    try {
      const results = await uploadDocuments(selectedFiles, {
        folder,
        sourceForFile: (file) => {
          if (selectedFiles.length === 1) {
            return previewName || defaultTitleFromFile(file)
          }
          return defaultTitleFromFile(file)
        },
        onProgress: (completed, total, fileName) => {
          if (fileName) {
            setUploadProgress(`Indexing ${completed + 1} of ${total}: ${fileName}`)
          }
        },
      })

      const succeeded = results.filter((item) => item.ok)
      const failed = results.filter((item) => !item.ok)

      if (succeeded.length) {
        onUploaded()
      }

      if (failed.length === 0) {
        if (succeeded.length === 1) {
          const res = succeeded[0].response
          setUploadMsg(
            `Indexed ${res?.source || res?.filename || succeeded[0].fileName} in ${res?.folder || folder}: ${res?.pages ?? 0} pages, ${res?.chunks ?? 0} chunks.`,
          )
        } else {
          setUploadMsg(
            `Indexed ${succeeded.length} documents in ${folder}.`,
          )
        }
        if (succeeded.length === selectedFiles.length) {
          clearFiles()
        } else {
          setSelectedFiles(
            selectedFiles.filter((file) =>
              failed.some((item) => item.fileName === file.name),
            ),
          )
        }
        return
      }

      const failureLines = failed
        .slice(0, 3)
        .map((item) => `${item.fileName}: ${item.error || 'Upload failed'}`)
        .join(' · ')

      if (succeeded.length) {
        setUploadMsg(
          `Indexed ${succeeded.length} of ${selectedFiles.length}. Failed: ${failureLines}${failed.length > 3 ? '…' : ''}`,
        )
        setSelectedFiles(
          selectedFiles.filter((file) =>
            failed.some((item) => item.fileName === file.name),
          ),
        )
        return
      }

      setUploadMsg(
        failed.length === 1
          ? failed[0].error || 'Upload failed'
          : `All uploads failed. ${failureLines}${failed.length > 3 ? '…' : ''}`,
      )
    } catch (err) {
      setUploadMsg(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(null)
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

        {singleFile ? (
          <label className="upload-field">
            <span>Display name</span>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Resume - Shubham Pawar"
              disabled={uploading}
            />
          </label>
        ) : (
          <div className="upload-field">
            <span>Batch</span>
            <p className="upload-batch-note">
              {selectedFiles.length
                ? `${selectedFiles.length} files — each uses its filename`
                : 'Select multiple files at once'}
            </p>
          </div>
        )}
      </div>

      <div className="upload-zone">
        <Upload size={22} />
        <strong>
          {uploading
            ? uploadProgress || 'Indexing documents…'
            : selectedFiles.length
              ? `${selectedFiles.length} document${selectedFiles.length === 1 ? '' : 's'} selected`
              : 'Drop documents or browse'}
        </strong>
        <span>
          {previewName
            ? `Will save as “${previewName}” in ${folder}`
            : selectedFiles.length
              ? `All files will be indexed in ${folder}`
              : 'PDF, DOCX, TXT, MD, CSV, JSON, HTML, images, and more'}
        </span>

        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => handleFilesPicked(e.target.files)}
        />

        {selectedFiles.length > 0 && (
          <ul className="upload-file-list">
            {selectedFiles.map((file) => (
              <li key={fileKey(file)}>
                <span>{file.name}</span>
                <button
                  type="button"
                  className="icon-btn"
                  aria-label={`Remove ${file.name}`}
                  disabled={uploading}
                  onClick={() => removeFile(file)}
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="upload-actions">
          <button
            className="filter-btn"
            type="button"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {selectedFiles.length ? 'Add more files' : 'Browse files'}
          </button>
          {selectedFiles.length > 0 && (
            <button
              className="filter-btn"
              type="button"
              disabled={uploading}
              onClick={clearFiles}
            >
              Clear all
            </button>
          )}
          <button
            className="primary-btn"
            type="button"
            disabled={uploading || !selectedFiles.length}
            onClick={() => void handleUpload()}
          >
            {uploading
              ? 'Uploading…'
              : selectedFiles.length > 1
                ? `Upload & index (${selectedFiles.length})`
                : 'Upload & index'}
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
