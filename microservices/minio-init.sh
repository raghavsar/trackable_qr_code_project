#!/bin/sh

# Wait for MinIO to be ready
sleep 5

# Add the MinIO server as an alias
mc alias set myminio http://minio:9000 minioadmin minioadmin

# Create the bucket if it doesn't exist
mc mb --ignore-existing myminio/qrcodes

# Set the bucket policy to public (download)
mc anonymous set download myminio/qrcodes

# Create the service account for qr-service
mc admin user add myminio qr_service_user qr_service_password_123

# Set policy for the service account
mc admin policy attach myminio readwrite --user qr_service_user

# Create a policy for the qr_service_user
cat > /tmp/qr-service-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::qrcodes/*",
                "arn:aws:s3:::qrcodes"
            ]
        }
    ]
}
EOF

echo "Created policy file"

# Create and assign the policy using new commands
mc admin policy create myminio qr-service-policy /tmp/qr-service-policy.json
echo "Created policy: qr-service-policy"

mc admin policy attach myminio qr-service-policy --user qr_service_user
echo "Attached policy to user"

# Set bucket policy for public read access
cat > /tmp/bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::qrcodes/*"]
        }
    ]
}
EOF

echo "Created bucket policy file"
mc anonymous set-json /tmp/bucket-policy.json myminio/qrcodes
echo "Set bucket policy for public access"

# List configuration to verify
echo "\nVerifying configuration:"
echo "1. Listing buckets:"
mc ls myminio/

echo "\n2. Listing users:"
mc admin user list myminio

echo "\n3. Listing policies:"
mc admin policy list myminio

echo "\nInitialization complete!" 