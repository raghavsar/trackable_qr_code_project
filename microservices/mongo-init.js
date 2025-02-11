print('Starting MongoDB initialization script...');

try {
    // Wait a bit for MongoDB to be ready
    sleep(1000);
    
    print('Attempting to authenticate as root user...');
    db.auth('admin', 'adminpassword');
    print('Root authentication successful');

    print('Switching to qr_code_db database...');
    db = db.getSiblingDB('qr_code_db');
    print('Successfully switched to qr_code_db database');

    // Create database user if not exists
    try {
        print('Attempting to create database user...');
        db.createUser({
            user: 'admin',
            pwd: 'adminpassword',
            roles: [
                {
                    role: 'readWrite',
                    db: 'qr_code_db'
                }
            ]
        });
        print('Database user created successfully');
    } catch (error) {
        if (error.code === 51003) {
            print('User already exists, continuing...');
        } else {
            print('Error creating user: ' + error.message);
            throw error;
        }
    }

    // Create collections with explicit options
    const collections = ['users', 'vcards', 'qr_codes', 'scan_events'];
    collections.forEach(collectionName => {
        try {
            print(`Creating collection: ${collectionName}`);
            db.createCollection(collectionName, {
                validator: {
                    $jsonSchema: {
                        bsonType: "object",
                        required: ["created_at"]
                    }
                }
            });
            print(`Collection ${collectionName} created successfully`);
        } catch (error) {
            if (error.code === 48) {
                print(`Collection ${collectionName} already exists`);
            } else {
                print(`Error creating collection ${collectionName}: ${error.message}`);
                throw error;
            }
        }
    });

    // Create indexes with explicit options
    try {
        print('Creating indexes...');
        
        // Users collection indexes
        print('Creating users collection indexes...');
        db.users.createIndex({ "email": 1 }, { unique: true, background: true });
        db.users.createIndex({ "created_at": 1 }, { background: true });

        // VCards collection indexes
        print('Creating vcards collection indexes...');
        db.vcards.createIndex({ "user_id": 1 }, { background: true });
        db.vcards.createIndex({ "email": 1 }, { background: true });
        db.vcards.createIndex({ "created_at": 1 }, { background: true });

        // QR codes collection indexes
        print('Creating qr_codes collection indexes...');
        db.qr_codes.createIndex({ "user_id": 1 }, { background: true });
        db.qr_codes.createIndex({ "vcard_id": 1 }, { background: true });
        db.qr_codes.createIndex({ "created_at": 1 }, { background: true });

        // Scan events collection indexes
        print('Creating scan_events collection indexes...');
        db.scan_events.createIndex({ "qr_code_id": 1 }, { background: true });
        db.scan_events.createIndex({ "vcard_id": 1 }, { background: true });
        db.scan_events.createIndex({ "user_id": 1 }, { background: true });
        db.scan_events.createIndex({ "timestamp": 1 }, { background: true });
        db.scan_events.createIndex({ "device_type": 1 }, { background: true });
        db.scan_events.createIndex({ "location.country": 1 }, { background: true });

        // Compound indexes for analytics
        db.scan_events.createIndex({ "vcard_id": 1, "timestamp": -1 }, { background: true });
        db.scan_events.createIndex({ "user_id": 1, "timestamp": -1 }, { background: true });
        
        print('All indexes created successfully');
    } catch (error) {
        print('Error creating indexes: ' + error.message);
        throw error;
    }

    // Insert a test document to verify write access
    try {
        print('Inserting test document...');
        db.users.insertOne({
            email: "test@example.com",
            first_name: "Test",
            last_name: "User",
            created_at: new Date(),
            updated_at: new Date()
        });
        print('Test document inserted successfully');
    } catch (error) {
        print('Error inserting test document: ' + error.message);
        // Don't throw here, as this is just a test
    }

    print('MongoDB initialization completed successfully');
} catch (error) {
    print('Fatal error during initialization:');
    print('Error message: ' + error.message);
    print('Error code: ' + error.code);
    print('Stack trace: ' + error.stack);
    throw error;
} 