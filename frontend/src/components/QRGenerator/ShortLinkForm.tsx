"use client"

import * as React from 'react'
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { CardContent } from "../ui/card"
import { QRCodeSVG } from 'qrcode.react'

interface FormData {
  originalUrl: string
  customAlias?: string
}

export default function ShortLinkForm() {
  const [formData, setFormData] = React.useState<FormData>({
    originalUrl: "",
    customAlias: ""
  })
  const [shortUrl, setShortUrl] = React.useState<string>("")

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  return (
    <div className="space-y-8">
      <CardContent className="p-6">
        <form className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="originalUrl">Original URL</Label>
            <Input
              id="originalUrl"
              name="originalUrl"
              type="url"
              value={formData.originalUrl}
              onChange={handleInputChange}
              placeholder="https://example.com/your-long-url"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="customAlias">Custom Alias (Optional)</Label>
            <Input
              id="customAlias"
              name="customAlias"
              value={formData.customAlias}
              onChange={handleInputChange}
              placeholder="custom-alias"
            />
          </div>

          <Button type="submit" className="w-full bg-black hover:bg-black/90">
            Generate Short Link & QR Code
          </Button>
        </form>
      </CardContent>

      {shortUrl && (
        <div className="space-y-6">
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm font-medium">Short URL:</p>
            <p className="text-primary">{shortUrl}</p>
          </div>
          <div className="flex justify-center p-6 bg-white rounded-lg">
            <QRCodeSVG 
              value={shortUrl} 
              size={200}
              level="H"
              includeMargin={true}
            />
          </div>
        </div>
      )}
    </div>
  )
} 