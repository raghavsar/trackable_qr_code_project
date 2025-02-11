"use client"

import * as React from 'react'
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { CardContent } from "../ui/card"
import { Textarea } from "../ui/textarea"
import { QRCodeSVG } from 'qrcode.react'

interface FormData {
  title: string
  url: string
  description: string
}

export default function LandingPageForm() {
  const [formData, setFormData] = React.useState<FormData>({
    title: "",
    url: "",
    description: ""
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  return (
    <div className="space-y-8">
      <CardContent className="p-6">
        <form className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="title">Landing Page Title</Label>
            <Input
              id="title"
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              placeholder="Enter your landing page title"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="url">Landing Page URL</Label>
            <Input
              id="url"
              name="url"
              type="url"
              value={formData.url}
              onChange={handleInputChange}
              placeholder="https://example.com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="Enter a description for your landing page"
              rows={4}
            />
          </div>

          <Button type="submit" className="w-full bg-black hover:bg-black/90">
            Generate QR Code
          </Button>
        </form>
      </CardContent>

      {formData.url && (
        <div className="flex justify-center p-6 bg-white rounded-lg">
          <QRCodeSVG 
            value={formData.url} 
            size={200}
            level="H"
            includeMargin={true}
          />
        </div>
      )}
    </div>
  )
} 