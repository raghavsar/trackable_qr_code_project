print('Starting database verification...');

try {
    // Connect to admin database
    db = db.getSiblingDB('admin');
    
    // Authenticate
    db.auth('admin', 'adminpassword');
    
    // List all databases
    let dbs = db.adminCommand('listDatabases');
    print('\nExisting databases:');
    dbs.databases.forEach(db => {
        print(`- ${db.name} (size: ${db.sizeOnDisk})`);
    });
    
    // Check qr_code_db specifically
    let qrDb = db.getSiblingDB('qr_code_db');
    print('\nCollections in qr_code_db:');
    qrDb.getCollectionNames().forEach(collection => {
        let count = qrDb[collection].countDocuments();
        print(`- ${collection} (documents: ${count})`);
    });
    
} catch (error) {
    print('Error during verification:');
    print(error);
} 