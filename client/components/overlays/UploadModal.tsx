'use client'

import { useRef, useState } from 'react'
import { FileText, GitBranch, Hash, Upload } from 'lucide-react'
import { uploadPdf } from '@/lib/api'
import { ModalShell } from '@/components/overlays/ModalShell'

type UploadModalProps = {
  onClose: () => void
  onUploaded: () => void
}

export function UploadModal({ onClose, onUploaded }: UploadModalProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)

  const handleUpload = async (file: File | undefined) => {
    if (!file) return

    setUploading(true)
    setUploadMsg(null)

    try {
      const res = await uploadPdf(file)

      if (res.error) {
        setUploadMsg(res.error)
        return
      }

      setUploadMsg(
        `Indexed ${res.filename}: ${res.pages} pages, ${res.chunks} chunks.`,
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
      <div className="upload-zone">
        <Upload size={22} />
        <strong>{uploading ? 'Indexing PDF…' : 'Drop a PDF or browse'}</strong>
        <span>Uses POST /upload-pdf</span>

        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          onChange={(e) => void handleUpload(e.target.files?.[0])}
        />

        <button
          className="primary-btn"
          type="button"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? 'Uploading…' : 'Browse PDF'}
        </button>

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
