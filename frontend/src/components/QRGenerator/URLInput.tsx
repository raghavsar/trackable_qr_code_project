"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardContent } from "@/components/ui/card"
import { QRCodeSVG } from 'qrcode.react'

interface Props {
  onGenerate: (url: string) => Promise<void>;
}

export default function URLInput({ onGenerate }: Props) {
  const [url, setUrl] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await onGenerate(url)
    } catch (error) {
      console.error('Failed to generate QR code:', error)
    }
  }

  return (
    <div className="space-y-8">
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="url">URL</Label>
            <Input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              required
            />
          </div>
          <Button type="submit" className="w-full">
            Generate QR Code
          </Button>
        </form>
      </CardContent>

      {url && (
        <div className="flex justify-center p-6 bg-white rounded-lg">
          <QRCodeSVG 
            value={url} 
            size={200}
            level="H"
            includeMargin={true}
          />
        </div>
      )}
    </div>
  )
} 