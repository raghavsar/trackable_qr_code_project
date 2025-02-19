import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { qrService } from '@/services/api';
import type { VCardResponse } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Download, Mail, Phone, Building, Globe, MapPin } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function VCardRedirect() {
  const { id } = useParams();
  const [vcard, setVcard] = useState<VCardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVCard = async () => {
      try {
        if (!id) return;
        const data = await qrService.getVCard(id);
        setVcard(data);
        
        // Track page view
        const apiUrl = import.meta.env.VITE_API_URL;
        await fetch(`${apiUrl}/api/v1/analytics/scan`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            vcard_id: id,
            user_id: data.user_id,
            timestamp: new Date().toISOString(),
            device_info: {
              is_mobile: /Mobi|Android/i.test(navigator.userAgent),
              device: navigator.platform,
              os: navigator.platform,
              browser: navigator.userAgent
            },
            action_type: 'view',
            success: true,
            ip_address: null,
            headers: {
              'user-agent': navigator.userAgent
            }
          })
        });
      } catch (error) {
        console.error('Failed to fetch VCard:', error);
        toast.error('Failed to load contact information');
      } finally {
        setLoading(false);
      }
    };

    fetchVCard();
  }, [id]);

  const handleDownloadVCF = async () => {
    try {
      if (!vcard) return;
      
      // Get API URL from environment
      const apiUrl = import.meta.env.VITE_API_URL;
      
      // Track download
      await fetch(`${apiUrl}/api/v1/analytics/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          vcard_id: vcard._id,
          user_id: vcard.user_id,
          timestamp: new Date().toISOString(),
          device_info: {
            is_mobile: /Mobi|Android/i.test(navigator.userAgent),
            device: navigator.platform,
            os: navigator.platform,
            browser: navigator.userAgent
          },
          action_type: 'vcf_download',
          success: true,
          ip_address: null,
          headers: {
            'user-agent': navigator.userAgent
          }
        })
      });
      
      // Download VCF
      const response = await fetch(`${apiUrl}/vcards/${vcard._id}/download`, {
        headers: {
          'Accept': 'text/vcard'
        }
      });
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${vcard.first_name}_${vcard.last_name}.vcf`;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('Contact downloaded successfully');
    } catch (error) {
      console.error('Failed to download VCF:', error);
      toast.error('Failed to download contact');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="text-lg">Loading contact information...</p>
        </div>
      </div>
    );
  }

  if (!vcard) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-lg text-red-600">Contact information not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="max-w-3xl mx-auto">
        <CardHeader className="text-center">
          <img 
            src="/Phonon Logo.png" 
            alt="Phonon Logo" 
            className="h-12 mx-auto mb-4"
          />
          <CardTitle className="text-2xl font-bold">Digital Business Card</CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          {/* Profile Section */}
          <div className="flex flex-col items-center space-y-4">
            <Avatar className="w-32 h-32">
              <AvatarImage src={vcard.profile_picture} />
              <AvatarFallback className="text-2xl">
                {vcard.first_name?.[0]}{vcard.last_name?.[0]}
              </AvatarFallback>
            </Avatar>
            <div className="text-center">
              <h2 className="text-2xl font-bold">{`${vcard.first_name} ${vcard.last_name}`}</h2>
              {vcard.title && <p className="text-gray-600">{vcard.title}</p>}
              {vcard.company && <p className="text-gray-600">{vcard.company}</p>}
            </div>
          </div>

          {/* Contact Information */}
          <div className="space-y-4">
            {vcard.email && (
              <div className="flex items-center space-x-3">
                <Mail className="w-5 h-5 text-gray-500" />
                <a href={`mailto:${vcard.email}`} className="text-blue-600 hover:underline">
                  {vcard.email}
                </a>
              </div>
            )}
            
            {vcard.mobile_number && (
              <div className="flex items-center space-x-3">
                <Phone className="w-5 h-5 text-gray-500" />
                <a href={`tel:${vcard.mobile_number}`} className="text-blue-600 hover:underline">
                  {vcard.mobile_number}
                </a>
              </div>
            )}
            
            {vcard.work_number && (
              <div className="flex items-center space-x-3">
                <Building className="w-5 h-5 text-gray-500" />
                <a href={`tel:${vcard.work_number}`} className="text-blue-600 hover:underline">
                  {vcard.work_number}
                </a>
              </div>
            )}
            
            {vcard.website && (
              <div className="flex items-center space-x-3">
                <Globe className="w-5 h-5 text-gray-500" />
                <a href={vcard.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  {vcard.website}
                </a>
              </div>
            )}

            {vcard.address && (
              <div className="flex items-center space-x-3">
                <MapPin className="w-5 h-5 text-gray-500" />
                <address className="not-italic">
                  {[
                    vcard.address.street,
                    vcard.address.city,
                    vcard.address.state,
                    vcard.address.zip_code,
                    vcard.address.country
                  ].filter(Boolean).join(', ')}
                </address>
              </div>
            )}
          </div>

          {/* Notes */}
          {vcard.notes && (
            <div className="border-t pt-4">
              <p className="text-gray-700 whitespace-pre-wrap">{vcard.notes}</p>
            </div>
          )}

          {/* Download Button */}
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleDownloadVCF}
              className="bg-primary hover:bg-primary/90"
            >
              <Download className="w-4 h-4 mr-2" />
              Add to Contacts
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 