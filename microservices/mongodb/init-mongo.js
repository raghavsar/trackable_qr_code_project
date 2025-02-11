print('Starting MongoDB initialization script...');

try {
    // Wait a bit for MongoDB to be ready
    sleep(1000);
    
    print('Attempting to authenticate as root user...');
    db = db.getSiblingDB('admin');
    print('Root authentication successful');

    // Create the admin user if it doesn't exist
    if (!db.getUser("admin")) {
        db.createUser({
            user: "admin",
            pwd: "adminpassword",
            roles: [
                { role: "userAdminAnyDatabase", db: "admin" },
                { role: "readWriteAnyDatabase", db: "admin" },
                { role: "dbAdminAnyDatabase", db: "admin" }
            ]
        });
    }

    // Switch to the qr_code_db database
    print('Switching to qr_code_db database...');
    db = db.getSiblingDB('qr_code_db');
    print('Successfully switched to qr_code_db database');

    // Create collections
    print('Creating collections...');
    db.createCollection('users');
    db.createCollection('vcards');
    db.createCollection('qr_codes');
    db.createCollection('scan_events');

    // Create indexes
    print('Creating indexes...');
    
    // Users collection
    db.users.createIndex({ "email": 1 }, { unique: true });
    db.users.createIndex({ "created_at": 1 });

    // VCards collection
    db.vcards.createIndex({ "user_id": 1 });
    db.vcards.createIndex({ "created_at": 1 });

    // QR codes collection
    db.qr_codes.createIndex({ "user_id": 1 });
    db.qr_codes.createIndex({ "vcard_id": 1 });
    db.qr_codes.createIndex({ "created_at": 1 });

    // Scan events collection
    db.scan_events.createIndex({ "qr_code_id": 1 });
    db.scan_events.createIndex({ "vcard_id": 1 });
    db.scan_events.createIndex({ "user_id": 1 });
    db.scan_events.createIndex({ "timestamp": 1 });
    db.scan_events.createIndex({ "device_type": 1 });

    print('MongoDB initialization completed successfully');
} catch (error) {
    print('Error during initialization:');
    print(error);
} 