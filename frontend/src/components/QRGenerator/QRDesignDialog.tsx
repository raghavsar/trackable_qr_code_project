"use client"

import * as React from 'react'
import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { qrService } from '@/services/api'
import type { QRDesignOptions, QRTemplate } from '@/types/api'
import { toast } from 'react-hot-toast'
import { Upload, Trash2, Info } from 'lucide-react'
import { useDebounce } from '@/hooks/useDebounce'
import { axiosInstance } from '@/services/axios'

interface Props {
  isOpen: boolean
  onClose: () => void
  onApply: (design: QRDesignOptions, templateId?: string) => void
  initialDesign?: QRDesignOptions
  vcardId: string
}

const defaultDesign: QRDesignOptions = {
  foreground_color: '#000000',
  background_color: '#FFFFFF',
  pattern_style: 'square',
  eye_style: 'square',
  error_correction: 'M',
  box_size: 10,
  border: 4,
  logo_size: 0.2,
  logo_background: false,
  logo_round: false,
}

const patternStyles: Array<{
  id: QRDesignOptions['pattern_style']
  label: string
  image: string
}> = [
  { id: 'square', label: 'Square', image: '/patterns/square.svg' },
  { id: 'rounded', label: 'Rounded', image: '/patterns/rounded.svg' },
  { id: 'dots', label: 'Dots', image: '/patterns/dots.svg' },
  { id: 'circular', label: 'Circular', image: '/patterns/circular.svg' },
  { id: 'diamond', label: 'Diamond', image: '/patterns/diamond.svg' },
  { id: 'special', label: 'Special', image: '/patterns/special.svg' },
] as const

const eyeStyles: Array<{
  id: QRDesignOptions['eye_style']
  label: string
  image: string
}> = [
  { id: 'square', label: 'Square', image: '/eyes/square.svg' },
  { id: 'rounded', label: 'Rounded', image: '/eyes/rounded.svg' },
  { id: 'circle', label: 'Circle', image: '/eyes/circle.svg' },
  { id: 'flower', label: 'Flower', image: '/eyes/flower.svg' },
] as const

const errorCorrectionLevels = [
  { value: 'L', label: 'Low (7%)', description: 'Best for clean environments' },
  { value: 'M', label: 'Medium (15%)', description: 'Balanced protection' },
  { value: 'Q', label: 'Quartile (25%)', description: 'Better error correction' },
  { value: 'H', label: 'High (30%)', description: 'Best for poor conditions' },
]

const COLOR_PRESETS = {
  pattern: [
    '#000000', '#1E88E5', '#43A047', '#5E35B1', '#E53935',
    '#FB8C00', '#546E7A', '#8E24AA', '#00ACC1'
  ],
  background: [
    '#FFFFFF', '#E3F2FD', '#E8F5E9', '#EDE7F6', '#FFEBEE',
    '#FFF3E0', '#ECEFF1', '#F3E5F5', '#E0F7FA'
  ]
}

export default function QRDesignDialog({ isOpen, onClose, onApply, initialDesign, vcardId }: Props) {
  const [activeTab, setActiveTab] = useState('custom')
  const [templates, setTemplates] = useState<QRTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [design, setDesign] = useState<QRDesignOptions>(initialDesign || defaultDesign)
  const [isLoading, setIsLoading] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const debouncedDesign = useDebounce(design, 300)

  useEffect(() => {
    if (initialDesign) {
      setDesign(initialDesign)
    }
    loadTemplates()
  }, [initialDesign])

  useEffect(() => {
    const generatePreview = async () => {
      try {
        const response = await axiosInstance.post('/qrcodes/preview', {
          vcard_id: vcardId,
          design: debouncedDesign
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        })
        if (response.data && response.data.preview_url) {
          setPreviewUrl(response.data.preview_url)
        } else {
          console.error('Invalid preview response:', response.data)
        }
      } catch (error) {
        console.error('Failed to generate preview:', error)
        setPreviewUrl('')
      }
    }

    if (vcardId) {
      generatePreview()
    }
  }, [debouncedDesign, vcardId])

  const loadTemplates = async () => {
    try {
      setIsLoading(true)
      const templates = await qrService.listTemplates()
      setTemplates(templates)
    } catch (error) {
      console.error('Failed to load templates:', error)
      toast.error('Failed to load templates')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDesignChange = (field: keyof QRDesignOptions, value: any) => {
    setDesign(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleLogoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (file.size > 1024 * 1024) {
        toast.error('Logo size should be less than 1MB')
        return
      }

      if (!file.type.startsWith('image/')) {
        toast.error('Please upload an image file')
        return
      }

      try {
        setIsUploading(true)
        // Here you would typically upload the file to your storage service
        // For now, we'll use a local URL
        const url = URL.createObjectURL(file)
        handleDesignChange('logo_url', url)
        toast.success('Logo uploaded successfully')
      } catch (error) {
        console.error('Failed to upload logo:', error)
        toast.error('Failed to upload logo')
      } finally {
        setIsUploading(false)
      }
    }
  }

  const handleDeleteLogo = () => {
    setLogoFile(null)
    handleDesignChange('logo_url', undefined)
    toast.success('Logo removed')
  }

  const handleTemplateSelect = async (templateId: string) => {
    try {
      setIsLoading(true)
      setSelectedTemplate(templateId)
      const template = await qrService.getTemplate(templateId)
      setDesign(template.design)
      toast.success('Template applied')
    } catch (error) {
      console.error('Failed to load template:', error)
      toast.error('Failed to load template')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveTemplate = async () => {
    if (!templateName) {
      toast.error('Please enter a template name')
      return
    }

    try {
      setIsLoading(true)
      await qrService.createTemplate({
        name: templateName,
        description: templateDescription,
        design,
        category: 'vcard',
        is_public: isPublic
      })
      toast.success('Template saved successfully')
      loadTemplates()
      setTemplateName('')
      setTemplateDescription('')
      setIsPublic(false)
    } catch (error) {
      console.error('Failed to save template:', error)
      toast.error('Failed to save template')
    } finally {
      setIsLoading(false)
    }
  }

  const handleApply = () => {
    onApply(design, selectedTemplate || undefined)
    onClose()
    toast.success('Design applied successfully')
  }

  const handleColorChange = (type: 'foreground_color' | 'background_color', color: string) => {
    setDesign(prev => ({
      ...prev,
      [type]: color
    }))
  }

  const handlePatternChange = (pattern: QRDesignOptions['pattern_style']) => {
    setDesign(prev => ({
      ...prev,
      pattern_style: pattern
    }))
  }

  const handleEyeStyleChange = (style: QRDesignOptions['eye_style']) => {
    setDesign(prev => ({
      ...prev,
      eye_style: style
    }))
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="px-6 py-4 flex-shrink-0">
          <DialogTitle>Customize QR Code Design</DialogTitle>
          <DialogDescription>
            Customize the appearance of your QR code or choose from existing templates
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="w-full grid grid-cols-2 gap-4 px-6 flex-shrink-0">
            <TabsTrigger value="custom">Custom Design</TabsTrigger>
            <TabsTrigger value="templates">Templates</TabsTrigger>
          </TabsList>

          <TabsContent value="custom" className="flex-1 overflow-y-auto px-6 pb-6">
            {/* Logo Section */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Logo</h3>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => document.getElementById('logo-upload')?.click()}
                    disabled={isUploading}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {isUploading ? 'Uploading...' : 'Upload Logo'}
                  </Button>
                  {design.logo_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDeleteLogo}
                      disabled={isUploading}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Remove
                    </Button>
                  )}
                </div>
              </div>

              <input
                id="logo-upload"
                type="file"
                className="hidden"
                accept="image/png,image/jpeg"
                onChange={handleLogoChange}
              />

              <div className="flex flex-col space-y-2">
                <p className="text-sm text-muted-foreground">
                  <Info className="h-4 w-4 inline-block mr-1" />
                  Upload a square or circular PNG/JPEG image (max 1MB)
                </p>
                
                {design.logo_url && (
                  <div className="relative w-20 h-20 border rounded-lg overflow-hidden">
                    <img
                      src={design.logo_url}
                      alt="Logo preview"
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}

                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={design.logo_background}
                      onChange={(e) => handleDesignChange('logo_background', e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    White background
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={design.logo_round}
                      onChange={(e) => handleDesignChange('logo_round', e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    Round shape
                  </label>
                </div>
              </div>
            </section>

            {/* Colors Section */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Colors</h3>
                <div className="flex items-center text-sm text-muted-foreground">
                  <Info className="h-4 w-4 mr-1" />
                  Low-contrast QR codes may not scan well
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Pattern Color</Label>
                  <div className="flex gap-3">
                    <div className="relative flex-shrink-0 w-10 h-10 rounded-md overflow-hidden">
                      <Input
                        type="color"
                        value={design.foreground_color}
                        onChange={(e) => handleColorChange('foreground_color', e.target.value)}
                        className="absolute inset-0 w-full h-full border-0 p-0"
                      />
                    </div>
                    <Input
                      type="text"
                      value={design.foreground_color.toUpperCase()}
                      onChange={(e) => handleColorChange('foreground_color', e.target.value)}
                      className="flex-1 font-mono uppercase"
                      maxLength={7}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Background Color</Label>
                  <div className="flex gap-3">
                    <div className="relative flex-shrink-0 w-10 h-10 rounded-md overflow-hidden">
                      <Input
                        type="color"
                        value={design.background_color}
                        onChange={(e) => handleColorChange('background_color', e.target.value)}
                        className="absolute inset-0 w-full h-full border-0 p-0"
                      />
                    </div>
                    <Input
                      type="text"
                      value={design.background_color.toUpperCase()}
                      onChange={(e) => handleColorChange('background_color', e.target.value)}
                      className="flex-1 font-mono uppercase"
                      maxLength={7}
                    />
                  </div>
                </div>
              </div>
            </section>

            {/* Pattern Section */}
            <section className="space-y-4">
              <h3 className="text-lg font-medium">Pattern Style</h3>
              <div className="grid grid-cols-6 gap-3">
                {patternStyles.map((style) => (
                  <button
                    key={style.id}
                    className={`group relative aspect-square rounded-lg border-2 transition-all ${
                      design.pattern_style === style.id
                        ? 'border-primary shadow-sm'
                        : 'border-transparent hover:border-primary/50'
                    }`}
                    onClick={() => handlePatternChange(style.id)}
                  >
                    <img
                      src={style.image}
                      alt={style.label}
                      className="w-full h-full object-cover rounded-md"
                    />
                    <div className="absolute inset-x-0 bottom-0 p-1 text-xs text-center bg-black/50 text-white rounded-b-md">
                      {style.label}
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Eye Style Section */}
            <section className="space-y-4">
              <h3 className="text-lg font-medium">Eye Style</h3>
              <div className="grid grid-cols-4 gap-4">
                {eyeStyles.map((style) => (
                  <button
                    key={style.id}
                    className={`group relative aspect-square rounded-lg border-2 transition-all ${
                      design.eye_style === style.id
                        ? 'border-primary shadow-sm'
                        : 'border-transparent hover:border-primary/50'
                    }`}
                    onClick={() => handleEyeStyleChange(style.id)}
                  >
                    <img
                      src={style.image}
                      alt={style.label}
                      className="w-full h-full object-cover rounded-md"
                    />
                    <div className="absolute inset-x-0 bottom-0 p-1 text-xs text-center bg-black/50 text-white rounded-b-md">
                      {style.label}
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Error Correction Section */}
            <section className="space-y-4">
              <h3 className="text-lg font-medium">Error Correction</h3>
              <div className="grid grid-cols-4 gap-4">
                {errorCorrectionLevels.map((level) => (
                  <button
                    key={level.value}
                    className={`p-4 text-left rounded-lg border-2 transition-all ${
                      design.error_correction === level.value
                        ? 'border-primary bg-primary/5'
                        : 'border-transparent hover:border-primary/50'
                    }`}
                    onClick={() => handleDesignChange('error_correction', level.value)}
                  >
                    <div className="font-medium">{level.label}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {level.description}
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* Save as Template Section */}
            <section className="space-y-4 pt-4 border-t">
              <h3 className="text-lg font-medium">Save as Template</h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="template_name">Template Name</Label>
                  <Input
                    id="template_name"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    placeholder="Enter a name for your template"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="template_description">Description</Label>
                  <Input
                    id="template_description"
                    value={templateDescription}
                    onChange={(e) => setTemplateDescription(e.target.value)}
                    placeholder="Add a description (optional)"
                  />
                </div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isPublic}
                    onChange={(e) => setIsPublic(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Make this template available to everyone
                </label>
                <Button
                  variant="secondary"
                  onClick={handleSaveTemplate}
                  disabled={!templateName || isLoading}
                  className="w-full"
                >
                  {isLoading ? 'Saving...' : 'Save Template'}
                </Button>
              </div>
            </section>

            {/* Preview Section */}
            <div className="flex flex-col gap-4">
              <div className="bg-white p-8 rounded-lg shadow-lg">
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt="QR Code Preview"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full aspect-square bg-gray-100 animate-pulse rounded" />
                )}
              </div>
              <Button 
                variant="outline"
                onClick={() => window.open(previewUrl, '_blank')}
                disabled={!previewUrl}
              >
                Test scannability
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="templates" className="flex-1 overflow-y-auto px-6 pb-6">
            {isLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="text-center text-muted-foreground">Loading templates...</div>
              </div>
            ) : templates.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-muted-foreground">No templates available</div>
                <Button
                  variant="link"
                  onClick={() => setActiveTab('custom')}
                  className="mt-2"
                >
                  Create your first template
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    className={`p-4 text-left rounded-lg border-2 transition-all ${
                      selectedTemplate === template.id
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 hover:border-primary/50'
                    }`}
                    onClick={() => handleTemplateSelect(template.id!)}
                  >
                    <h3 className="font-medium">{template.name}</h3>
                    {template.description && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {template.description}
                      </p>
                    )}
                    <div className="mt-2 text-xs text-muted-foreground">
                      {template.is_public ? 'Public template' : 'Private template'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <div className="flex justify-end gap-3 px-6 py-4 border-t bg-background">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleApply}>
            Apply Design
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
} 