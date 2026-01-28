import * as React from 'react'
import { useCallback, useRef } from 'react'
import { Upload, FolderOpen, X, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface FileWithPath {
  file: File
  relativePath: string
}

interface FileUploadProps {
  onFilesSelected: (files: FileWithPath[]) => void
  selectedFiles: FileWithPath[]
  accept?: string
  disabled?: boolean
  uploadProgress?: number
  isUploading?: boolean
}

export function FileUpload({
  onFilesSelected,
  selectedFiles,
  accept,
  disabled = false,
  uploadProgress = 0,
  isUploading = false,
}: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = React.useState(false)

  const processFiles = useCallback(
    (fileList: FileList | null, isFolder = false) => {
      if (!fileList) return

      const filesWithPaths: FileWithPath[] = []
      for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i]
        // webkitRelativePath is available when using directory input
        const relativePath =
          isFolder && file.webkitRelativePath
            ? file.webkitRelativePath
            : file.name
        filesWithPaths.push({ file, relativePath })
      }
      onFilesSelected([...selectedFiles, ...filesWithPaths])
    },
    [onFilesSelected, selectedFiles]
  )

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files, false)
    // Reset input so same file can be selected again
    e.target.value = ''
  }

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files, true)
    e.target.value = ''
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      setIsDragOver(true)
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    if (disabled) return

    const items = e.dataTransfer.items
    const filesWithPaths: FileWithPath[] = []

    // Process dropped items
    const processEntry = (
      entry: FileSystemEntry,
      path: string
    ): Promise<void> => {
      return new Promise((resolve) => {
        if (entry.isFile) {
          ;(entry as FileSystemFileEntry).file((file) => {
            filesWithPaths.push({
              file,
              relativePath: path + file.name,
            })
            resolve()
          })
        } else if (entry.isDirectory) {
          const dirReader = (entry as FileSystemDirectoryEntry).createReader()
          dirReader.readEntries(async (entries) => {
            for (const subEntry of entries) {
              await processEntry(subEntry, path + entry.name + '/')
            }
            resolve()
          })
        } else {
          resolve()
        }
      })
    }

    const promises: Promise<void>[] = []
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry()
      if (entry) {
        promises.push(processEntry(entry, ''))
      }
    }

    Promise.all(promises).then(() => {
      if (filesWithPaths.length > 0) {
        onFilesSelected([...selectedFiles, ...filesWithPaths])
      }
    })
  }

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index)
    onFilesSelected(newFiles)
  }

  const clearAll = () => {
    onFilesSelected([])
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const totalSize = selectedFiles.reduce((acc, f) => acc + f.file.size, 0)

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center transition-colors',
          isDragOver
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground mb-4">
          Drag and drop files or folders here, or use the buttons below
        </p>

        <div className="flex gap-2 justify-center">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={accept}
            onChange={handleFileChange}
            className="hidden"
            disabled={disabled}
          />
          <input
            ref={folderInputRef}
            type="file"
            // @ts-expect-error webkitdirectory is not in the types
            webkitdirectory=""
            directory=""
            multiple
            onChange={handleFolderChange}
            className="hidden"
            disabled={disabled}
          />

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
          >
            <FileText className="mr-2 h-4 w-4" />
            Choose Files
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => folderInputRef.current?.click()}
            disabled={disabled || isUploading}
          >
            <FolderOpen className="mr-2 h-4 w-4" />
            Choose Folder
          </Button>
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium">Selected Files</p>
              <Badge variant="secondary">{selectedFiles.length}</Badge>
              <span className="text-xs text-muted-foreground">
                ({formatFileSize(totalSize)})
              </span>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearAll}
              disabled={disabled || isUploading}
            >
              Clear All
            </Button>
          </div>

          <div className="max-h-[150px] overflow-auto space-y-1 rounded-md border p-2">
            {selectedFiles.map((f, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50"
              >
                <span className="truncate flex-1 mr-2" title={f.relativePath}>
                  {f.relativePath}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(f.file.size)}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => removeFile(i)}
                    disabled={disabled || isUploading}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Uploading...</span>
            <span className="font-medium">{uploadProgress}%</span>
          </div>
          <Progress value={uploadProgress} className="h-2" />
        </div>
      )}
    </div>
  )
}
