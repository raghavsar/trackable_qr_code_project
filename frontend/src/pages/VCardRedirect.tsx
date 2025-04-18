import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { qrService } from '@/services/api';
import type { VCardResponse } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Download, Mail, Phone, Building, Globe, Home, Briefcase } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { trackVCardPageLoad, trackContactAdd, trackVcfDownload } from '@/utils/analytics';

export default function VCardRedirect() {
  const { id } = useParams<{ id: string }>();
  const [vcard, setVcard] = useState<VCardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    const fetchVCard = async () => {
      try {
        if (!id) return;
        const data = await qrService.getVCard(id);
        setVcard(data);

        // Only track events if the page is visible
        if (document.visibilityState === 'visible') {
          // Check if we're in the /r/ route or direct navigation, which indicates a QR scan
          const isQRScan = window.location.pathname.startsWith('/r/') && document.referrer === '';

          // Use our new unified tracking function
          await trackVCardPageLoad(id, data.user_id, isQRScan);
        } else {
          console.log('📊 Skipping analytics - page not visible');
        }
      } catch (error) {
        console.error('Failed to fetch VCard:', error);
        toast.error('Failed to load contact information');
      } finally {
        setLoading(false);
      }
    };

    fetchVCard();

    // Set up visibility change listener
    const handleVisibilityChange = () => {
      // Do not track anything on visibility change to prevent background tab issues
      console.log(`Page visibility changed to: ${document.visibilityState}`);
    };

    // Add visibility change listener
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Clean up
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [id]);

  // Compute formatted address from address object
  const getFormattedAddress = (address: VCardResponse['address']) => {
    if (!address) return '';

    const parts = [];
    if (address.street) parts.push(address.street);
    if (address.city) parts.push(address.city);
    if (address.state) parts.push(address.state);
    if (address.zip_code) parts.push(address.zip_code);
    if (address.country) parts.push(address.country);

    return parts.join(', ');
  };

  // Phonon HQ address and Google Maps URL
  const phononHQMapsUrl = "https://maps.app.goo.gl/99bjahgR1SJdWXbb7";
  const phononHQAddress = "106, Blue Diamond Complex, Fatehgunj, Vadodara 390002, Gujarat, India";

  // Function to handle adding contact directly
  const handleAddContact = async () => {
    if (isAdding) return; // Prevent multiple clicks
    setIsAdding(true);
    try {
      if (!vcard || !vcard._id || !vcard.user_id) {
        toast.error('Invalid VCard data');
        return;
      }

      // Track contact add using our new utility function
      const success = await trackContactAdd(vcard._id, vcard.user_id);

      if (success) {
        toast.success('Contact added successfully!');

        // Trigger VCF download after tracking is complete
        await handleDownloadVCF();
      } else {
        toast.error('Failed to add contact.');
      }
    } catch (error) {
      console.error('Error adding contact:', error);
      toast.error('Failed to add contact');
    } finally {
      setIsAdding(false); // Reset the state after the request
    }
  };

  // Function to handle VCF download
  const handleDownloadVCF = async () => {
    try {
      if (!vcard) return;

      // Track download using our new utility function
      await trackVcfDownload(vcard._id, vcard.user_id);

      // Get API URL from environment
      const apiUrl = import.meta.env.VITE_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured');
      }

      // Construct the URL correctly to avoid duplicate 'api' in the path
      // Use the redirect service's VCF download endpoint which doesn't require authentication
      const downloadUrl = `${apiUrl}/r/${vcard._id}?format=vcf`;
      console.log('Downloading VCF from URL:', downloadUrl);

      // Download VCF
      const response = await fetch(downloadUrl, {
        headers: {
          'Accept': 'text/vcard'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to download contact');
      }

      // Get filename from Content-Disposition header or create a default one
      const contentDisposition = response.headers.get('content-disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `${vcard.first_name}_${vcard.last_name}.vcf`;

      // Create blob with proper MIME type
      const blob = new Blob([await response.text()], { type: 'text/vcard' });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
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

            {/* Address */}
            {vcard.address && Object.values(vcard.address).some(value => value) ? (
              <div className="flex items-start space-x-3">
                <Home className="w-6 h-6 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-sm font-medium text-gray-500 block">Address</span>
                  <span className="text-gray-700">
                    {getFormattedAddress(vcard.address)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-start space-x-3">
                <Briefcase className="w-6 h-6 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="text-sm font-medium text-gray-500 block">Address</span>
                  <a
                    href={phononHQMapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline leading-relaxed"
                  >
                    {phononHQAddress}
                  </a>
                </div>
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

          {/* REMOVE THIS DIV BLOCK
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleAddContact}
              className="bg-primary hover:bg-primary/90"
              disabled={isAdding}
            >
              Add Contact
            </Button>
          </div>
          END REMOVE */}
        </CardContent>
      </Card>
    </div>
  );
}